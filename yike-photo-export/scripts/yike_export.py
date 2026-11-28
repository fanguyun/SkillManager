#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一刻相册原图批量导出工具 (photo.baidu.com)

子命令
  check      检查 Cookie 是否有效，统计云端项目数量
  list       导出清单 (JSONL + CSV)，不下载文件
  albums     列出相册及各自项目数
  download   批量下载原图/原视频（断点续传 + MD5 校验 + 去重）
  verify     校验已下载文件的 MD5 是否仍与云端一致

认证
  本工具不接触账号密码，只复用你已登录浏览器的 Cookie。三选一：
    --browser chrome            从本机浏览器自动读取（需 pip install browser_cookie3）
    --cookie-file cookies.txt   Netscape 格式 / "k=v; k2=v2" 文本 / JSON
    --cookie-json '{"BDUSS":"..."}'

示例
  python yike_export.py check    --browser chrome
  python yike_export.py list     --browser chrome --out ~/Pictures/yike
  python yike_export.py download --browser chrome --out ~/Pictures/yike --jobs 4
  python yike_export.py download --cookie-file cookies.txt --out ./yike --layout year-month

退出码
  0 成功   1 部分失败   2 认证失败   3 参数/环境错误
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

try:
    import requests
except ImportError:  # pragma: no cover
    sys.exit("缺少依赖，请先安装：pip install requests")

# 可被环境变量覆盖，便于指向镜像或本地 mock（测试用）
BASE = os.environ.get("YIKE_BASE_URL", "https://photo.baidu.com").rstrip("/")

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

AUTH_ERRNO = -6          # 未登录 / Cookie 失效
RATE_LIMIT_ERRNOS = (50005,)   # 操作过于频繁，可退避重试
STATE_FILE = ".yike-state.json"
INVENTORY_JSONL = "yike-inventory.jsonl"
INVENTORY_CSV = "yike-inventory.csv"
REPORT_FILE = "yike-export-report.json"


def safe_url(url: str) -> str:
    """去掉查询串再用于日志/报告。

    dlink 是带签名的临时直链，接口 URL 的查询串里带 bdstoken。
    这些都不该被写进 report.json 或被打印出来——报告常被随手分享或提交。
    """
    base, sep, _ = url.partition("?")
    return base + ("?<已脱敏>" if sep else "")


def safe_error(exc: object) -> str:
    """把异常转成可安全写入报告/日志的文本。

    requests 的异常消息里会带完整 URL（含 dlink 签名和 bdstoken），
    直接落盘会把凭据写进 yike-export-report.json。这里统一裁掉查询串。
    """
    text = str(exc)
    return re.sub(r"(https?://[^\s?]+)\?[^\s\"']*", r"\1?<已脱敏>", text)


def file_md5(path: str, chunk: int = 1 << 20) -> str:
    """计算本地文件 MD5。用于确认磁盘上的文件确实是我们要的那一份。"""
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def truthy_flag(value: Any) -> bool:
    """宽松解析接口的 has_more 之类标志位。

    服务端可能返回 1 / "1" / true / "true" / 2。早期实现只认 (1,"1",True)，
    遇到 "true" 或 2 就当成"没有下一页"，导致静默少下载。
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "none", "null")
    return bool(value)


def positive_int(text: str) -> int:
    try:
        n = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"需要正整数，收到 {text!r}")
    if n < 1:
        raise argparse.ArgumentTypeError(f"需要正整数（≥1），收到 {n}")
    return n


# --------------------------------------------------------------------------
# 异常
# --------------------------------------------------------------------------
class AuthError(RuntimeError):
    """Cookie 失效或未登录。"""


class ApiError(RuntimeError):
    """接口返回了非 0 的 errno，或响应不是 JSON。"""


class RateLimited(ApiError):
    """服务端限流（errno=50005「操作过于频繁」）。

    这是**可恢复**的：等一会儿再试即可，不该被当成永久失败写进状态文件。
    早期版本把它当普通错误，导致并发稍高就成片失败。
    """


# --------------------------------------------------------------------------
# Cookie 读取
# --------------------------------------------------------------------------
def _parse_netscape(text: str) -> Dict[str, str]:
    """Netscape cookies.txt：domain, flag, path, secure, expiry, name, value"""
    jar: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            parts = line.split()
        if len(parts) >= 7:
            jar[parts[5]] = parts[6]
    return jar


def _parse_header_string(text: str) -> Dict[str, str]:
    """"BAIDUID=xxx; STOKEN=yyy" 形式"""
    jar: Dict[str, str] = {}
    for chunk in text.replace("\n", ";").split(";"):
        if "=" not in chunk:
            continue
        k, _, v = chunk.partition("=")
        k, v = k.strip(), v.strip()
        if k:
            jar[k] = v
    return jar


def _from_browser(name: str) -> Dict[str, str]:
    try:
        import browser_cookie3  # type: ignore
    except ImportError:
        sys.exit(
            "未安装 browser_cookie3。请执行：pip install browser_cookie3\n"
            "或改用 --cookie-file / --cookie-json 手动提供 Cookie。"
        )
    fn = getattr(browser_cookie3, name, None)
    if fn is None:
        sys.exit(f"browser_cookie3 不支持浏览器：{name}")
    jar: Dict[str, str] = {}
    # 同时抓 .baidu.com 与 photo.baidu.com 两个域
    for domain in ("baidu.com", None):
        try:
            cj = fn(domain_name=domain) if domain else fn()
        except Exception:
            continue
        for c in cj:
            if "baidu" in (c.domain or ""):
                jar[c.name] = c.value
    return jar


def load_cookies(args: argparse.Namespace) -> Dict[str, str]:
    if args.cookie_json:
        data = json.loads(args.cookie_json)
        return {str(k): str(v) for k, v in data.items()}

    if args.cookie_file:
        text = open(args.cookie_file, "r", encoding="utf-8", errors="ignore").read()
        stripped = text.lstrip()
        if stripped.startswith("{"):
            data = json.loads(text)
            return {str(k): str(v) for k, v in data.items()}
        jar = _parse_netscape(text)
        return jar or _parse_header_string(text)

    if args.browser:
        return _from_browser(args.browser)

    sys.exit("需要认证信息：请提供 --browser / --cookie-file / --cookie-json 之一（详见 --help）。")


def check_cookie_health(jar: Dict[str, str]) -> List[str]:
    """返回关键 Cookie 缺失的提示列表。"""
    missing = []
    if not any(k.startswith("BDUSS") for k in jar):
        missing.append("BDUSS / BDUSS_BFESS（登录态核心字段）")
    if not any(k.startswith("STOKEN") for k in jar):
        missing.append("STOKEN")
    return missing


# --------------------------------------------------------------------------
# 客户端
# --------------------------------------------------------------------------
@dataclass
class Item:
    fsid: str
    path: str
    md5: str = ""
    size: int = 0
    ctime: int = 0
    mtime: int = 0
    dlink: str = ""

    @property
    def filename(self) -> str:
        return self.path.rsplit("/", 1)[-1] or f"{self.fsid}.bin"

    @property
    def timestamp(self) -> int:
        return self.mtime or self.ctime or 0


def _norm_item(raw: Dict[str, Any]) -> Optional[Item]:
    fsid = raw.get("fsid") or raw.get("fs_id")
    if fsid is None:
        return None
    try:
        size = int(raw.get("size") or 0)
    except (TypeError, ValueError):
        size = 0
    def _ts(key: str) -> int:
        try:
            return int(raw.get(key) or 0)
        except (TypeError, ValueError):
            return 0
    return Item(
        fsid=str(fsid),
        path=str(raw.get("path") or raw.get("server_filename") or ""),
        md5=str(raw.get("md5") or raw.get("server_md5") or ""),
        size=size,
        ctime=_ts("ctime"),
        mtime=_ts("mtime"),
        dlink=str(raw.get("dlink") or ""),
    )


class YikeClient:
    def __init__(
        self,
        cookies: Dict[str, str],
        proxies: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        retries: int = 3,
        sleep: float = 0.0,
    ) -> None:
        self.s = requests.Session()
        self.s.cookies.update(cookies)
        self.s.headers.update(
            {
                "User-Agent": UA,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{BASE}/photo/web/home",
            }
        )
        self.proxies = proxies or {}
        self.timeout = timeout
        self.retries = max(1, retries)
        self.sleep = sleep
        self._bdstoken: Optional[str] = None
        # 分页异常（服务端声称还有下一页却给不出可用游标）会记录在此，
        # 由调用方在结束时明确告知用户，避免"静默少下载一批"这种最危险的失败。
        self.warnings: List[str] = []

    # ---- 底层请求 ----------------------------------------------------
    def _request(self, method: str, url: str, **kw) -> requests.Response:
        kw.setdefault("timeout", self.timeout)
        if self.proxies:
            kw.setdefault("proxies", self.proxies)
        last: Optional[Exception] = None
        for attempt in range(self.retries):
            try:
                if self.sleep:
                    time.sleep(self.sleep)
                resp = self.s.request(method, url, **kw)
                if resp.status_code >= 500 or resp.status_code == 429:
                    raise requests.HTTPError(f"HTTP {resp.status_code}")
                return resp
            except Exception as exc:  # 网络类异常统一重试
                last = exc
                if attempt < self.retries - 1:
                    time.sleep(min(2 ** attempt + random.random(), 20))
        raise ApiError(f"请求失败（已重试 {self.retries} 次）：{safe_url(url)} -> {last}")

    def _json(self, resp: requests.Response) -> Dict[str, Any]:
        try:
            data = resp.json()
        except ValueError:
            snippet = resp.text[:200].replace("\n", " ")
            raise ApiError(f"响应不是 JSON（HTTP {resp.status_code}）：{snippet}")
        # 接口非官方，返回数组/字符串/null 都是可能的（改版、风控页、包裹层）。
        # 调用方一律按 dict 取字段，这里必须先挡住，否则是裸 AttributeError。
        if not isinstance(data, dict):
            kind = type(data).__name__
            preview = json.dumps(data, ensure_ascii=False)[:200]
            raise ApiError(
                f"接口返回的不是 JSON 对象（{kind}）：{preview}。"
                f"接口可能已改版，请核对 references/api-notes.md。"
            )
        if "errno" not in data:
            # 形状不符也当错误处理，避免调用方 KeyError/静默拿到空结果
            preview = json.dumps(data, ensure_ascii=False)[:200]
            raise ApiError(f"接口响应缺少 errno 字段，可能已改版：{preview}")
        if data["errno"] == 0:
            return data
        if data["errno"] == AUTH_ERRNO:
            raise AuthError(
                "Cookie 已失效或未登录（errno=-6）。请重新在浏览器登录一刻相册后重试。"
            )
        if data["errno"] in RATE_LIMIT_ERRNOS:
            raise RateLimited(
                f"操作过于频繁（errno={data['errno']}），服务端限流"
            )
        raise ApiError(
            f"接口报错 errno={data['errno']}："
            f"{json.dumps(data, ensure_ascii=False)[:300]}"
        )

    def _params(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        p = dict(extra or {})
        token = self.bdstoken()
        if token:
            p["bdstoken"] = token
        return {k: v for k, v in p.items() if v is not None}

    # ---- bdstoken ----------------------------------------------------
    def bdstoken(self) -> Optional[str]:
        """从首页 HTML 中提取 bdstoken；失败则返回 None（多数接口仍可用）。"""
        if self._bdstoken is not None:
            return self._bdstoken or None
        self._bdstoken = ""
        try:
            resp = self._request("GET", f"{BASE}/photo/web/home")
            text = resp.text
            patterns = [
                r'"bdstoken"\s*:\s*"([^"]+)"',
                r"'bdstoken'\s*:\s*'([^']+)'",
                r'bdstoken["\']?\s*[:=]\s*["\']([A-Za-z0-9]{8,})["\']',
            ]
            for pat in patterns:
                m = re.search(pat, text)
                if m:
                    self._bdstoken = m.group(1)
                    break
        except Exception:
            pass
        return self._bdstoken or None

    # ---- 列表 --------------------------------------------------------
    def list_page(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        """云端全部项目（照片+视频）的一页。"""
        resp = self._request(
            "GET",
            f"{BASE}/youai/file/v1/list",
            params=self._params({"cursor": cursor, "need_filter_hidden": 0}),
        )
        data = self._json(resp)
        raw_list = data.get("list") or []
        items = [i for i in (_norm_item(r) for r in raw_list) if i]
        return {
            "items": items,
            "has_more": truthy_flag(data.get("has_more")),
            "cursor": data.get("cursor"),
        }

    def _next_cursor(self, page: Dict[str, Any], seen: Set[str], label: str) -> Optional[str]:
        """校验分页游标。返回 None 表示确实没有下一页。

        服务端有时会 has_more=1 却给出空游标或重复游标。此时**不能**当作
        "已到末页"静默结束——那会悄悄少下载一批文件。这里记录警告并中止翻页。
        """
        nxt = page.get("cursor")
        if nxt is None or str(nxt).strip() == "":
            self.warnings.append(
                f"{label}：服务端返回 has_more=1 但游标为空，分页提前结束，"
                f"可能漏掉后续项目。请重跑；若持续出现，请核对接口是否变更。"
            )
            return None
        nxt = str(nxt)
        if nxt in seen:
            self.warnings.append(
                f"{label}：分页游标重复（{nxt}），已中止翻页以避免死循环，可能漏掉后续项目。"
            )
            return None
        return nxt

    def iter_items(self, limit: int = 0) -> Iterator[Item]:
        cursor: Optional[str] = None
        seen: Set[str] = set()
        count = 0
        while True:
            page = self.list_page(cursor)
            for item in page["items"]:
                yield item
                count += 1
                if limit and count >= limit:
                    return
            if not page["has_more"]:
                return
            nxt = self._next_cursor(page, seen, "文件列表")
            if nxt is None:
                return
            seen.add(nxt)
            cursor = nxt

    # ---- 相册 --------------------------------------------------------
    def list_albums(self) -> List[Dict[str, Any]]:
        albums: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        seen: Set[str] = set()
        while True:
            resp = self._request(
                "GET",
                f"{BASE}/youai/album/v1/list",
                params=self._params(
                    {
                        "clienttype": 70,
                        "limit": 30,
                        "need_amount": 1,
                        "need_member": 1,
                        "field": "mtime",
                        "cursor": cursor,
                    }
                ),
            )
            data = self._json(resp)
            for raw in data.get("list") or []:
                albums.append(
                    {
                        "album_id": str(raw.get("album_id")),
                        "title": str(raw.get("title") or ""),
                        "amount": raw.get("amount"),
                        "mtime": raw.get("mtime"),
                    }
                )
            if not truthy_flag(data.get("has_more")):
                return albums
            nxt = self._next_cursor(data, seen, "相册列表")
            if nxt is None:
                return albums
            seen.add(nxt)
            cursor = nxt

    def iter_album_items(self, album_id: str, limit: int = 0) -> Iterator[Item]:
        cursor: Optional[str] = None
        seen: Set[str] = set()
        count = 0
        while True:
            resp = self._request(
                "POST",
                f"{BASE}/youai/album/v1/listfile",
                params=self._params(),
                data={"cursor": cursor, "album_id": album_id},
            )
            data = self._json(resp)
            for raw in data.get("list") or []:
                item = _norm_item(raw)
                if item:
                    yield item
                    count += 1
                    if limit and count >= limit:
                        return
            if not truthy_flag(data.get("has_more")):
                return
            nxt = self._next_cursor(data, seen, "相册文件列表")
            if nxt is None:
                return
            seen.add(nxt)
            cursor = nxt

    # ---- 下载 --------------------------------------------------------
    def get_dlink(self, item: Item) -> str:
        if item.dlink:
            return item.dlink
        resp = self._request(
            "GET",
            f"{BASE}/youai/file/v2/download",
            params=self._params({"clienttype": 70, "fsid": item.fsid}),
        )
        data = self._json(resp)
        dlink = data.get("dlink")
        if not dlink:
            raise ApiError(f"接口未返回 dlink（fsid={item.fsid}）")
        return str(dlink)

    def refresh_dlink(self, item: Item) -> str:
        """丢弃列表自带的 dlink，重新向接口要一条。

        列表里的 dlink 可能已过期（带签名，有时效）。若一直重试同一个死链，
        该文件会永久失败，所以重试前必须换一条新链。
        """
        item.dlink = ""
        return self.get_dlink(item)

    def stream_download(self, item: Item, dest: str, chunk: int = 1 << 16) -> Tuple[int, str]:
        """流式下载到 dest，返回 (字节数, md5)。

        失败时清理 .part 临时文件；成功时用 os.replace 原子落盘，
        保证进程被强杀也不会留下半成品冒充完整文件。
        """
        url = self.get_dlink(item)
        md5 = hashlib.md5()
        total = 0
        part = dest + ".part"
        try:
            resp = self._request("GET", url, stream=True)
            if resp.status_code != 200:
                raise ApiError(f"下载失败 HTTP {resp.status_code}（fsid={item.fsid}）")
            with open(part, "wb") as fh:
                for block in resp.iter_content(chunk):
                    if not block:
                        continue
                    fh.write(block)
                    md5.update(block)
                    total += len(block)
            os.replace(part, dest)  # 原子落盘
            return total, md5.hexdigest()
        except BaseException:
            # 网络错误、校验失败、Ctrl-C 都要清理，避免 .part 长期占空间
            try:
                if os.path.exists(part):
                    os.remove(part)
            except OSError:
                pass
            raise


# --------------------------------------------------------------------------
# 文件名 / 归档
# --------------------------------------------------------------------------
_ILLEGAL = re.compile(r'[\\/:*?"<>|\x00-\x1f\x7f]')


def sanitize(name: str) -> str:
    name = _ILLEGAL.sub("_", name).strip().strip(". ")
    if not name:
        name = "unnamed"
    if len(name) > 180:
        stem, ext = os.path.splitext(name)
        name = stem[:170] + ext
    return name


def relpath_for(item: Item, layout: str) -> str:
    name = sanitize(item.filename)
    if layout == "flat":
        return name
    ts = item.timestamp
    now = time.time()
    if ts < 946684800 or ts > now + 86400:  # 早于 2000 年或未来时间 → 归入 unknown
        sub = "unknown"
    elif layout == "year":
        sub = time.strftime("%Y", time.localtime(ts))
    else:  # year-month
        sub = time.strftime("%Y/%m", time.localtime(ts))
    return os.path.join(sub, name)


class NameAllocator:
    """按目录分配不冲突的文件名（线程安全）。

    必须同时避开两类占用：

    1. 本轮已分配/已认领的名字（内存集合）
    2. **磁盘上已经存在的文件**——那是上一轮下载的原图。云端返回顺序一变，
       同名的新文件就可能被算到旧文件的名字上；只看内存集合会直接覆盖它。

    `reserve()` 用于把"已认领的既有文件"提前登记，确保后续分配不会碰它。
    """

    def __init__(self) -> None:
        self._used: Dict[str, Set[str]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(directory: str) -> str:
        return os.path.normcase(os.path.abspath(directory))

    def reserve(self, path: str) -> None:
        """登记一个既有文件路径为已占用，后续分配不得使用。"""
        directory, name = os.path.split(path)
        with self._lock:
            self._used.setdefault(self._key(directory), set()).add(name.lower())

    def is_reserved(self, path: str) -> bool:
        directory, name = os.path.split(path)
        with self._lock:
            return name.lower() in self._used.get(self._key(directory), set())

    def allocate(self, directory: str, filename: str) -> str:
        key = self._key(directory)
        with self._lock:
            used = self._used.setdefault(key, set())
            candidate = filename
            stem, ext = os.path.splitext(filename)
            i = 1
            while candidate.lower() in used or os.path.exists(
                os.path.join(directory, candidate)
            ):
                candidate = f"{stem} ({i}){ext}"
                i += 1
            used.add(candidate.lower())
            return candidate


# --------------------------------------------------------------------------
# 状态文件（断点续传）
# --------------------------------------------------------------------------
class State:
    def __init__(self, path: str) -> None:
        self.path = path
        self.lock = threading.Lock()
        self.data: Dict[str, Any] = {"version": 1, "items": {}}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                if isinstance(loaded, dict) and "items" in loaded:
                    self.data = loaded
            except Exception:
                pass  # 状态损坏则从零开始，已存在的文件仍会被 size 检查兜住

    def get(self, fsid: str) -> Optional[Dict[str, Any]]:
        return self.data["items"].get(fsid)

    def mark(self, fsid: str, **fields: Any) -> None:
        with self.lock:
            rec = self.data["items"].setdefault(fsid, {})
            rec.update(fields)
            rec["ts"] = int(time.time())

    def flush(self) -> None:
        with self.lock:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, ensure_ascii=False)
            os.replace(tmp, self.path)


# --------------------------------------------------------------------------
# 进度显示
# --------------------------------------------------------------------------
class Progress:
    def __init__(self, total: int) -> None:
        self.total = total
        self.done = 0
        self.ok = 0
        self.failed = 0
        self.skipped = 0
        self.dup = 0
        self.bytes = 0
        self.start = time.time()
        self.lock = threading.Lock()

    def update(self, status: str, nbytes: int = 0) -> None:
        with self.lock:
            self.done += 1
            self.bytes += nbytes
            if status == "ok":
                self.ok += 1
            elif status == "failed":
                self.failed += 1
            elif status == "skipped":
                self.skipped += 1
            elif status == "dup":
                self.dup += 1
            if self.done % 20 == 0 or self.done == self.total:
                self.render()

    def render(self) -> None:
        elapsed = max(time.time() - self.start, 1e-6)
        rate = self.bytes / elapsed / 1e6
        if self.total:
            pct = self.done * 100.0 / self.total
            eta = (elapsed / self.done) * (self.total - self.done) if self.done else 0
            head = f"{self.done}/{self.total} ({pct:5.1f}%)"
            tail = f"ETA {int(eta // 60)}m{int(eta % 60):02d}s"
        else:
            head, tail = f"{self.done}", ""
        sys.stderr.write(
            f"\r  {head}  新 {self.ok}  跳过 {self.skipped}  重复 {self.dup}  "
            f"失败 {self.failed}  {rate:.1f} MB/s  {tail}      "
        )
        sys.stderr.flush()

    def finish(self) -> None:
        sys.stderr.write("\n")
        sys.stderr.flush()


# --------------------------------------------------------------------------
# 子命令
# --------------------------------------------------------------------------
def build_client(args: argparse.Namespace) -> YikeClient:
    jar = load_cookies(args)
    if not jar:
        sys.exit("未能解析出任何 Cookie。")
    missing = check_cookie_health(jar)
    if missing:
        print(f"⚠ Cookie 缺少关键字段：{', '.join(missing)}", file=sys.stderr)
        print("  若 check 报未登录，请在浏览器中重新登录一刻相册后重试。", file=sys.stderr)
    return YikeClient(
        jar,
        timeout=args.timeout,
        retries=args.retries,
        sleep=args.sleep,
    )


def report_warnings(client: YikeClient) -> None:
    """把分页等异常显式告诉用户——静默少下载是最危险的失败模式。"""
    if not client.warnings:
        return
    print("\n⚠️ 需要注意：", file=sys.stderr)
    for w in dict.fromkeys(client.warnings):  # 去重但保持顺序
        print(f"  · {w}", file=sys.stderr)


def cmd_check(args: argparse.Namespace) -> int:
    client = build_client(args)
    print("检查登录态…")
    token = client.bdstoken()
    print(f"  bdstoken: {token or '（未取到，多数接口仍可正常使用）'}")

    first = client.list_page()
    print(f"  首页返回 {len(first['items'])} 项，has_more={first['has_more']}")
    if not first["items"] and not first["has_more"]:
        print("  ⚠ 账号内没有检测到任何项目。")
        return 0

    print("统计全部项目（只读列表，不下载）…")
    total = 0
    photos = videos = 0
    size = 0
    for item in client.iter_items():
        total += 1
        size += item.size
        if re.search(r"\.(mp4|mov|avi|mkv|wmv|flv|m4v|3gp|webm)$", item.filename, re.I):
            videos += 1
        else:
            photos += 1
        if total % 500 == 0:
            sys.stderr.write(f"\r  已统计 {total} 项…")
            sys.stderr.flush()
    sys.stderr.write("\r" + " " * 40 + "\r")

    print("\n✅ Cookie 有效，可以开始下载。")
    if client.warnings:
        # 分页被截断时，这个总数只是下限，必须说清楚，不能让它看起来像完整统计。
        print(f"  ⚠️ 项目总数：至少 {total}（分页异常导致未能统计完整，见下方警告）")
    else:
        print(f"  项目总数：{total}  （照片 {photos} / 视频 {videos}）")
    print(f"  云端合计：{size / 1024 / 1024 / 1024:.2f} GB")
    print(f"\n下一步：python {os.path.basename(sys.argv[0])} download "
          f"--out <目标目录> --jobs 4  （认证参数同上）")
    report_warnings(client)
    return 1 if client.warnings else 0


def cmd_list(args: argparse.Namespace) -> int:
    client = build_client(args)
    os.makedirs(args.out, exist_ok=True)
    jsonl = os.path.join(args.out, INVENTORY_JSONL)
    csv_path = os.path.join(args.out, INVENTORY_CSV)

    count = 0
    total = 0
    with open(jsonl, "w", encoding="utf-8") as jf, open(
        csv_path, "w", encoding="utf-8-sig", newline=""
    ) as cf:
        writer = csv.writer(cf)
        writer.writerow(["fsid", "filename", "path", "size", "md5", "ctime", "mtime"])
        for item in client.iter_items(limit=args.limit):
            jf.write(json.dumps(item.__dict__, ensure_ascii=False) + "\n")
            writer.writerow(
                [item.fsid, item.filename, item.path, item.size, item.md5, item.ctime, item.mtime]
            )
            count += 1
            total += item.size
            if count % 500 == 0:
                sys.stderr.write(f"\r  已导出 {count} 项…")
                sys.stderr.flush()
    sys.stderr.write("\r" + " " * 40 + "\r")

    print(f"✅ 清单已写入：\n  {jsonl}\n  {csv_path}")
    if client.warnings:
        print(f"  ⚠️ 导出 {count} 项（分页异常，清单可能不完整）")
    else:
        print(f"  {count} 项，合计 {total / 1024 / 1024 / 1024:.2f} GB")
    report_warnings(client)
    return 1 if client.warnings else 0


def cmd_albums(args: argparse.Namespace) -> int:
    client = build_client(args)
    albums = client.list_albums()
    if not albums:
        print("没有找到任何相册。")
        return 0
    print(f"共 {len(albums)} 个相册：\n")
    print(f"{'相册名':<28} {'数量':>6}  相册 ID")
    print("-" * 64)
    for a in albums:
        title = (a["title"] or "(未命名)")[:26]
        print(f"{title:<28} {str(a['amount'] or '?'):>6}  {a['album_id']}")
    print("\n用 --album <ID> 只导出某个相册。")
    report_warnings(client)
    return 1 if client.warnings else 0


def cmd_download(args: argparse.Namespace) -> int:
    client = build_client(args)
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)

    state = State(os.path.join(out, STATE_FILE))
    alloc = NameAllocator()

    print("正在获取云端清单…")
    if args.album:
        source: Iterator[Item] = client.iter_album_items(args.album, limit=args.limit)
        scope = f"相册 {args.album}"
    else:
        source = client.iter_items(limit=args.limit)
        scope = "全部项目"
    items = list(source)
    print(f"  {scope}：{len(items)} 项")
    if not items:
        # 账号有几千张却因接口改版返回空列表时，报"完成"会造成"备份好了"的假象。
        print(
            "⚠️ 云端清单为空，未下载任何文件。\n"
            "  如果账号里确实有照片，说明接口可能已改版或返回了非预期结构，\n"
            "  请先跑 check 子命令核对，不要把它当作「没有照片」或「备份完成」。",
            file=sys.stderr,
        )
        return 1
    if client.warnings:
        # 分页被截断意味着"没下载到"的那些文件根本不在本次清单里，
        # 若不明确告知，用户会以为备份已完成——这是本工具最危险的失败模式。
        print(f"  ⚠️ 清单可能不完整（分页异常），本次只处理已获取的 {len(items)} 项。")
        report_warnings(client)
        if not args.allow_partial:
            print(
                "\n已中止，未开始下载：清单不完整时下载会给出「备份已完成」的错误印象。\n"
                "  请先重跑一次；确认接口确实异常仍要处理已有清单，加 --allow-partial。",
                file=sys.stderr,
            )
            return 1

    # ---- 路径规划 ----------------------------------------------------------
    # 关键：每个 fsid 的目标路径必须先看状态记录里的 rec["file"]，不能重新分配。
    # 云端返回顺序会变（新增照片插队、改 --limit、切 --album），若每轮都重新
    # 按顺序分配名字，同名文件就会被算到别的 fsid 上，把上一轮的原图覆盖掉。
    def verify_local(path: str, item: Item) -> bool:
        """确认磁盘上这个文件确实就是云端这一份（字节级）。

        必须有云端 md5 才敢判定一致——只比 size 是不够的：两台相机拍出的
        同名照片经常同为 4096 字节，但那不是同一张图。宁可重下，不可错认。
        """
        if not item.md5 or not os.path.exists(path):
            return False
        if item.size and os.path.getsize(path) != item.size:
            return False
        try:
            return file_md5(path).lower() == item.md5.lower()
        except OSError:
            return False

    def cleanup_parts() -> None:
        """删除中断时残留的 .part 临时文件（只在本输出目录内，非递归风险可控）。"""
        for root, _dirs, fnames in os.walk(out):
            for fname in fnames:
                if fname.endswith(".part"):
                    try:
                        os.remove(os.path.join(root, fname))
                    except OSError:
                        pass

    def norm(path: str) -> str:
        return os.path.normcase(os.path.abspath(path))

    # 状态记录里已认领、且文件仍在磁盘的路径 → fsid
    claimed: Dict[str, str] = {}
    for fsid, rec in state.data["items"].items():
        if rec.get("status") == "ok" and rec.get("file") and os.path.exists(rec["file"]):
            claimed.setdefault(norm(rec["file"]), fsid)
    for path in claimed:
        alloc.reserve(path)   # 这些名字后续分配一律绕开

    # (item, dest, src)：src 为 None 表示 dest 已是正确内容（跳过下载）；
    # src 非 None 表示 dest 尚不存在，需从 src 复制/硬链接（旧状态错绑的修复）
    reuse: List[Tuple[Item, str, Optional[str]]] = []
    to_fetch: List[Tuple[Item, str]] = []
    shadowed: List[str] = []

    for item in items:
        rec = state.get(item.fsid)
        prev = rec.get("file") if rec and rec.get("status") == "ok" else None

        # 1) 该 fsid 上次已下好且内容仍然正确 → 沿用原路径，不重新分配
        if prev and verify_local(prev, item):
            key = norm(prev)
            owner = claimed.get(key)
            if owner in (None, item.fsid):
                claimed[key] = item.fsid
                alloc.reserve(prev)
                reuse.append((item, prev, None))
                continue
            # 路径已被另一个 fsid 占用，而两边内容校验都通过 → 旧版状态遗留的
            # 错绑。给当前 fsid 换个新名字，内容从既有文件复制过来。
            directory = os.path.dirname(prev)
            dest = os.path.join(directory, alloc.allocate(directory, os.path.basename(prev)))
            claimed[norm(dest)] = item.fsid
            reuse.append((item, dest, prev))
            continue

        rel = relpath_for(item, args.layout)
        directory = os.path.join(out, os.path.dirname(rel))
        natural = os.path.join(directory, os.path.basename(rel))

        # 2) 自然名未被认领且磁盘上已是正确内容（状态丢失但文件还在）→ 认领
        if norm(natural) not in claimed and os.path.exists(natural) and verify_local(natural, item):
            claimed[norm(natural)] = item.fsid
            alloc.reserve(natural)
            state.mark(item.fsid, status="ok", file=natural,
                       md5=item.md5, size=item.size)
            reuse.append((item, natural, None))
            continue

        # 2b) 自然名被一个内容不同的既有文件占着。绝不覆盖用户已有的文件
        #     （可能是别处放来的同名照片），但要说清楚，否则用户会以为下载漏了。
        if norm(natural) not in claimed and os.path.exists(natural):
            shadowed.append(natural)

        # 3) 其余一律分配一个全新名字去下载。
        #    绝不覆盖磁盘上任何既有文件——哪怕 size 相同（见 verify_local 注释）。
        dest = os.path.join(directory, alloc.allocate(directory, os.path.basename(rel)))
        claimed[norm(dest)] = item.fsid
        to_fetch.append((item, dest))

    if shadowed:
        print(f"  ⚠ {len(shadowed)} 个目标文件名已被内容不同的既有文件占用，"
              f"新文件将另存为带序号的名字：", file=sys.stderr)
        for path in shadowed[:5]:
            print(f"      {path}", file=sys.stderr)
        if len(shadowed) > 5:
            print(f"      … 其余 {len(shadowed) - 5} 个省略", file=sys.stderr)

    skipped = len(reuse)
    todo: List[Tuple[Item, str]] = []
    dup_planned: List[Tuple[Item, str, str]] = []  # (item, dest, 来源文件)
    md5_seen: Dict[str, str] = {}                  # 云端 md5 -> 可信的本地文件

    # 先登记"已在磁盘且校验通过"的文件，它们是最可靠的去重源
    for item, dest, src in reuse:
        if src is None and item.md5:
            md5_seen.setdefault(item.md5, dest)
    # 需要修复性复制的项，排在下载之前处理，保证顺序在后的引用能看到文件
    for item, dest, src in reuse:
        if src is not None:
            dup_planned.append((item, dest, src))
    for item, dest in to_fetch:
        if args.dedup != "download" and item.md5 and item.md5 in md5_seen:
            dup_planned.append((item, dest, md5_seen[item.md5]))
            continue
        todo.append((item, dest))
        if item.md5:
            md5_seen.setdefault(item.md5, dest)

    if skipped:
        print(f"  已完成 {skipped} 项（断点续传跳过）")
    if args.dry_run:
        print(f"\n[dry-run] 待下载 {len(todo)} 项，重复 {len(dup_planned)} 项，跳过 {skipped} 项")
        for item, dest in todo[:20]:
            print(f"  {item.filename}  ({item.size/1024/1024:.1f} MB) -> {dest}")
        if len(todo) > 20:
            print(f"  … 其余 {len(todo) - 20} 项省略")
        return 0

    prog = Progress(len(todo) + len(dup_planned))
    prog.skipped = skipped
    failures: List[Dict[str, Any]] = []

    def handle_duplicate(item: Item, dest: str, src: str) -> str:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        # 源文件必须存在**且内容确实是云端这一份**。只检查存在会把损坏的或
        # 来路不明的文件硬链接成 N 份，还把云端 md5 盖上去冒充"已验证"。
        if not os.path.exists(src):
            reason = f"去重源文件不存在（{src}），可能其下载失败；重跑本命令即可重试"
            failures.append({"fsid": item.fsid, "file": dest, "error": reason})
            state.mark(item.fsid, status="failed", file=dest, error=reason)
            return "failed"
        if item.md5:
            try:
                actual = file_md5(src)
            except OSError as exc:
                reason = f"无法读取去重源文件：{safe_error(exc)}"
                failures.append({"fsid": item.fsid, "file": dest, "error": reason})
                state.mark(item.fsid, status="failed", file=dest, error=reason)
                return "failed"
            if actual.lower() != item.md5.lower():
                # 源文件内容不对 → 退化为真实下载，绝不能把错误内容复制出去
                reason = (f"去重源文件内容与云端不符（期望 {item.md5} / 实际 {actual}），"
                          f"已改为独立下载")
                print(f"  ⚠ {reason}", file=sys.stderr)
                failures.append({"fsid": item.fsid, "file": dest, "error": reason})
                return handle_download(item, dest)
        if args.dedup == "link":
            try:
                os.link(src, dest)
                state.mark(item.fsid, status="ok", file=dest, md5=item.md5,
                           size=item.size, dedup="link", source=src)
                return "dup"
            except OSError:
                pass  # 跨文件系统等 → 退回复制
        try:
            shutil.copy2(src, dest)
            # 复制后复验一次，确保落盘的就是校验过的那份内容
            if item.md5 and file_md5(dest).lower() != item.md5.lower():
                raise ApiError("复制后校验失败")
            state.mark(item.fsid, status="ok", file=dest, md5=item.md5,
                       size=item.size, dedup="copy", source=src)
            return "dup"
        except Exception as exc:
            failures.append({"fsid": item.fsid, "file": dest,
                             "error": f"去重复制失败: {safe_error(exc)}"})
            state.mark(item.fsid, status="failed", file=dest, error=safe_error(exc))
            return "failed"

    def handle_download(item: Item, dest: str) -> str:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        last_err = ""
        attempt = 0
        rate_limit_streak = 0
        while attempt < args.file_retries:
            try:
                nbytes, digest = client.stream_download(item, dest)
                if item.md5 and digest.lower() != item.md5.lower():
                    last_err = f"MD5 不匹配（云端 {item.md5} / 本地 {digest}）"
                    try:
                        os.remove(dest)
                    except OSError:
                        pass
                    attempt += 1
                    if attempt < args.file_retries:
                        time.sleep(2 ** attempt)
                        continue
                    raise ApiError(last_err)
                if item.size and nbytes != item.size:
                    last_err = f"大小不符（云端 {item.size} / 本地 {nbytes}）"
                    attempt += 1
                    if attempt < args.file_retries:
                        continue
                    raise ApiError(last_err)
                if item.timestamp:
                    os.utime(dest, (item.timestamp, item.timestamp))
                state.mark(item.fsid, status="ok", file=dest, md5=item.md5, size=nbytes)
                return "ok"
            except AuthError:
                raise
            except RateLimited:
                # 限流是可恢复的：指数退避等待，且**不消耗**本文件的重试预算，
                # 否则并发一高就成片变 failed。连续限流太久则放弃本文件，
                # 让它进 failed 由下一轮重跑处理，避免单个文件卡死整个队列。
                rate_limit_streak += 1
                if rate_limit_streak > 8:
                    last_err = "持续被限流，留待下次重跑"
                    break
                backoff = min(3 * (2 ** (rate_limit_streak - 1)) + random.uniform(0, 2), 90)
                sys.stderr.write(f"\r  限流，等待 {backoff:.0f}s 后重试…{' ' * 20}")
                sys.stderr.flush()
                time.sleep(backoff)
                continue
            except Exception as exc:
                last_err = safe_error(exc)
                attempt += 1
                if attempt < args.file_retries:
                    # 换一条新的 dlink 再试：列表自带的那条可能已过期，
                    # 死链重试多少次都是同一个结果。
                    try:
                        client.refresh_dlink(item)
                    except Exception:
                        pass
                    time.sleep(min(2 ** attempt + random.random(), 15))
        failures.append({"fsid": item.fsid, "file": dest, "error": last_err})
        state.mark(item.fsid, status="failed", file=dest, error=last_err)
        return "failed"

    # 去重必须在真实下载之后：硬链接/复制需要一个已经落盘的源文件。
    saved = 0
    pool = ThreadPoolExecutor(max_workers=max(1, args.jobs))
    try:
        futures = {pool.submit(handle_download, it, d): it for it, d in todo}
        for fut in as_completed(futures):
            item = futures[fut]
            try:
                status = fut.result()
            except AuthError:
                for f in futures:
                    f.cancel()
                prog.finish()
                state.flush()
                print("\n❌ Cookie 已失效，已保存进度。重新登录后重跑同一命令即可续传。",
                      file=sys.stderr)
                return 2
            prog.update(status, item.size if status == "ok" else 0)
            saved += 1
            if saved % 25 == 0:
                state.flush()
    except KeyboardInterrupt:
        # 关键：ThreadPoolExecutor 的线程在解释器退出时会被 join（atexit 钩子），
        # 而它们正阻塞在 socket read 上，最长要等 --timeout 才返回。所以即使这里
        # return，进程仍会挂住几十秒，用户以为卡死就会 kill -9。
        # 处理办法：先保存进度、清理 .part，然后立即硬退出。
        pool.shutdown(wait=False, cancel_futures=True)
        prog.finish()
        state.flush()
        cleanup_parts()
        print("\n⏸ 已中断，进度已保存。重跑同一命令会从断点继续。", file=sys.stderr)
        sys.stderr.flush()
        os._exit(1)
    finally:
        pool.shutdown(wait=False)

    # 源文件此刻已全部就位，再处理重复项
    for item, dest, src in dup_planned:
        status = handle_duplicate(item, dest, src)
        prog.update(status, item.size if status == "dup" else 0)

    prog.finish()
    state.flush()

    report = {
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "output_dir": out,
        "total": len(items),
        "downloaded": prog.ok,
        "deduplicated": prog.dup,
        "skipped": prog.skipped,
        "failed": prog.failed,
        "bytes_downloaded": prog.bytes,
        "failures": failures,
    }
    with open(os.path.join(out, REPORT_FILE), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    print(f"\n{'✅' if not failures else '⚠️'} 完成：新下载 {prog.ok}，去重 {prog.dup}，"
          f"跳过 {prog.skipped}，失败 {prog.failed}")
    print(f"  本次下载 {prog.bytes / 1024 / 1024 / 1024:.2f} GB，输出目录：{out}")
    if client.warnings:
        print("\n⚠️ 本次运行的清单可能不完整，不能视为已完成全量备份：", file=sys.stderr)
        report_warnings(client)
    if failures:
        print(f"  失败明细：{os.path.join(out, REPORT_FILE)}")
        print("  直接重跑同一命令即可只重试失败项。")
    return 0 if not failures else 1


def cmd_verify(args: argparse.Namespace) -> int:
    """对已下载文件重新计算 MD5，与云端记录比对。"""
    out = os.path.abspath(args.out)
    state = State(os.path.join(out, STATE_FILE))
    records = state.data["items"]
    if not records:
        print("没有找到状态文件，请先执行 download。")
        return 3

    checked = bad = missing = unverifiable = failed_rec = 0
    bad_list: List[Tuple[str, str]] = []
    for fsid, rec in records.items():
        if rec.get("status") != "ok":
            failed_rec += 1
            continue
        path = rec.get("file")
        if not path or not os.path.exists(path):
            missing += 1
            continue
        expected = rec.get("md5") or ""
        if not expected:
            # 云端没给 md5 → 无法比对。必须单独计数，不能算进"已校验"，
            # 否则会宣称"完全一致"而实际一个字节都没验过。
            unverifiable += 1
            continue
        try:
            actual = file_md5(path)
        except OSError:
            missing += 1
            continue
        checked += 1
        if actual.lower() != expected.lower():
            bad += 1
            bad_list.append((path, expected))
        if checked % 200 == 0:
            sys.stderr.write(f"\r  已校验 {checked} 个文件…")
            sys.stderr.flush()
    sys.stderr.write("\r" + " " * 40 + "\r")

    ok = checked - bad
    print(f"校验结果：{ok} 个通过 MD5 比对（共 {checked} 个可校验文件）")
    if missing:
        print(f"  ⚠ {missing} 个文件在磁盘上不存在（可能被移动或删除）")
    if unverifiable:
        print(f"  ⚠ {unverifiable} 个文件没有云端 MD5 记录，无法校验")
    if failed_rec:
        print(f"  ⚠ {failed_rec} 条记录状态为失败，未纳入校验")
    if bad:
        print(f"  ❌ {bad} 个文件 MD5 与云端不一致：")
        for path, expected in bad_list[:20]:
            print(f"     {path}")
    elif checked:
        print("  以上文件与云端 MD5 完全一致，即为字节级原图。")

    if not checked:
        print("  ❌ 没有任何文件真正通过校验，不能视为已备份。", file=sys.stderr)
        return 1
    # 有缺失或无法校验的文件时，不能给"一切正常"的退出码
    return 0 if (not bad and not missing and not unverifiable) else 1


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def add_auth_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("认证（三选一）")
    g.add_argument("--browser", choices=["chrome", "chromium", "edge", "firefox",
                                         "brave", "opera", "safari", "vivaldi"],
                   help="从本机浏览器读取 Cookie（需 pip install browser_cookie3）")
    g.add_argument("--cookie-file", help="Cookie 文件：Netscape 格式 / k=v; 文本 / JSON")
    g.add_argument("--cookie-json", help="直接传入 Cookie 的 JSON 字符串")


def add_net_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("网络")
    g.add_argument("--timeout", type=int, default=30, help="单次请求超时秒数（默认 30）")
    g.add_argument("--retries", type=int, default=3, help="接口请求重试次数（默认 3）")
    g.add_argument("--sleep", type=float, default=0.0, help="每次请求前的间隔秒数（默认 0）")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="yike_export",
        description="一刻相册原图批量导出工具（断点续传 + MD5 校验 + 去重）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("check", help="检查 Cookie 有效性并统计云端项目")
    add_auth_args(p)
    add_net_args(p)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("list", help="导出清单（JSONL + CSV），不下载")
    add_auth_args(p)
    add_net_args(p)
    p.add_argument("--out", default="./yike", help="输出目录（默认 ./yike）")
    p.add_argument("--limit", type=int, default=0, help="最多处理多少项（0=全部）")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("albums", help="列出相册")
    add_auth_args(p)
    add_net_args(p)
    p.set_defaults(func=cmd_albums)

    p = sub.add_parser("download", help="批量下载原图/原视频")
    add_auth_args(p)
    add_net_args(p)
    p.add_argument("--out", required=True, help="输出目录（建议独立空目录）")
    p.add_argument("--jobs", type=positive_int, default=4,
                   help="并发数（默认 4，过高易触发风控）")
    p.add_argument("--limit", type=int, default=0, help="最多处理多少项（0=全部，可先试 20）")
    p.add_argument("--album", help="只导出指定相册 ID（见 albums 子命令）")
    p.add_argument("--layout", choices=["flat", "year", "year-month"], default="flat",
                   help="归档方式：flat 平铺 / year 按年 / year-month 按年月（默认 flat）")
    p.add_argument("--dedup", choices=["link", "copy", "download"], default="link",
                   help="相同 MD5 的重复项处理：link 硬链接 / copy 复制 / download 照常下载")
    p.add_argument("--file-retries", type=int, default=2, help="单文件下载失败重试次数（默认 2）")
    p.add_argument("--dry-run", action="store_true", help="只显示将要下载什么，不实际下载")
    p.add_argument("--allow-partial", action="store_true",
                   help="分页异常导致清单可能不完整时，仍然继续下载已获取的部分")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("verify", help="校验已下载文件的 MD5 是否与云端一致")
    p.add_argument("--out", required=True, help="download 时使用的输出目录")
    p.set_defaults(func=cmd_verify)

    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except AuthError as exc:
        print(f"\n❌ 认证失败：{exc}", file=sys.stderr)
        return 2
    except ApiError as exc:
        print(f"\n❌ 接口错误：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已取消。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

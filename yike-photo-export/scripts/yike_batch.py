#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一刻相册批量下载器（走 batchdownload 接口，绕开单文件接口的账号级限流）。

为什么需要它：
    `file/v2/download`（单文件取直链）会被百度按账号限流（errno 50005），
    一旦触发可持续数小时。而 `file/v1/batchdownload`（打包成 zip）不受同样限制。
    实测该接口返回的 zip 内文件与原图 **MD5 完全一致**，是字节级原图。

策略：
    - 每次打包 N 个文件（默认 30），下载 zip，解压到目标目录。
    - 每个文件解压后立即校验云端 md5，不符则记录失败。
    - 已有状态文件（.yike-state.json）中标记 ok 且内容正确的文件直接跳过。
    - 全部成功写入同一状态文件，可与 yike_export.py 互操作。

用法：
    python3 yike_batch.py --cookie-file /tmp/yike-cookie.txt --out ~/Pictures/yike
    python3 yike_batch.py --cookie-file ... --out ... --batch-size 30 --layout year-month
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import random
import re
import sys
import time
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    sys.exit("缺少依赖：pip install requests")

BASE = os.environ.get("YIKE_BASE_URL", "https://photo.baidu.com").rstrip("/")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
STATE_FILE = ".yike-state.json"
REPORT_FILE = "yike-batch-report.json"
RATE_LIMIT_ERRNOS = (50005,)
AUTH_ERRNO = -6


# --------------------------------------------------------------------------
# 异常
# --------------------------------------------------------------------------
class AuthError(RuntimeError):
    pass


class RateLimited(RuntimeError):
    pass


class ApiError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# 工具函数
# --------------------------------------------------------------------------
def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def file_md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def safe_error(exc: object) -> str:
    text = str(exc)
    return re.sub(r"(https?://[^\s?]+)\?[^\s\"']*", r"\1?<已脱敏>", text)


_ILLEGAL = re.compile(r'[\\/:*?"<>|\x00-\x1f\x7f]')


def sanitize(name: str) -> str:
    name = _ILLEGAL.sub("_", name).strip().strip(". ")
    return name or "unnamed"


def load_cookies(path: str) -> Dict[str, str]:
    text = open(path, "r", encoding="utf-8", errors="ignore").read()
    jar: Dict[str, str] = {}
    if text.lstrip().startswith("{"):
        return {str(k): str(v) for k, v in json.loads(text).items()}
    for chunk in text.replace("\n", ";").split(";"):
        if "=" in chunk:
            k, _, v = chunk.partition("=")
            if k.strip():
                jar[k.strip()] = v.strip()
    return jar


def rc4_variant(j: str, r: str) -> str:
    """复现接口下发的 sign2 算法（RC4 变体），用于计算 batchdownload 的 sign。"""
    a: List[int] = []
    p: List[int] = []
    v = len(j)
    if v == 0:
        raise ValueError("sign3 为空，无法计算 sign")
    for q in range(256):
        a.append(ord(j[q % v]))
        p.append(q)
    u = 0
    for q in range(256):
        u = (u + p[q] + a[q]) % 256
        p[q], p[u] = p[u], p[q]
    i = u = 0
    out: List[str] = []
    for q in range(len(r)):
        i = (i + 1) % 256
        u = (u + p[i]) % 256
        p[i], p[u] = p[u], p[i]
        k = p[(p[i] + p[u]) % 256]
        out.append(chr(ord(r[q]) ^ k))
    return "".join(out)


# --------------------------------------------------------------------------
# 状态
# --------------------------------------------------------------------------
class State:
    def __init__(self, path: str) -> None:
        self.path = path
        self.data: Dict[str, Any] = {"version": 1, "items": {}}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                if isinstance(loaded, dict) and "items" in loaded:
                    self.data = loaded
            except Exception:
                pass

    def get(self, fsid: str) -> Optional[Dict[str, Any]]:
        return self.data["items"].get(fsid)

    def mark(self, fsid: str, **fields: Any) -> None:
        rec = self.data["items"].setdefault(fsid, {})
        rec.update(fields)
        rec["ts"] = int(time.time())

    def flush(self) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False)
        os.replace(tmp, self.path)

    def counts(self) -> Tuple[int, int]:
        ok = sum(1 for v in self.data["items"].values() if v.get("status") == "ok")
        bad = sum(1 for v in self.data["items"].values() if v.get("status") == "failed")
        return ok, bad


# --------------------------------------------------------------------------
# 客户端
# --------------------------------------------------------------------------
class BatchClient:
    def __init__(self, cookies: Dict[str, str], timeout: int = 60) -> None:
        self.s = requests.Session()
        self.s.cookies.update(cookies)
        self.s.headers.update({
            "User-Agent": UA,
            "Referer": f"{BASE}/photo/web/home",
            "Accept": "application/json, text/plain, */*",
        })
        self.timeout = timeout
        self._bdstoken: Optional[str] = None

    def _check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise ApiError(f"响应不是 JSON 对象：{str(data)[:150]}")
        errno = data.get("errno")
        if errno == 0:
            return data
        if errno == AUTH_ERRNO:
            raise AuthError("Cookie 已失效，请重新登录一刻相册后重试")
        if errno in RATE_LIMIT_ERRNOS:
            raise RateLimited(f"限流 errno={errno}")
        raise ApiError(f"接口错误 errno={errno}：{json.dumps(data, ensure_ascii=False)[:200]}")

    def bdstoken(self) -> Optional[str]:
        if self._bdstoken is not None:
            return self._bdstoken or None
        self._bdstoken = ""
        try:
            r = self.s.get(f"{BASE}/photo/web/home", timeout=self.timeout)
            m = re.search(r'"bdstoken"\s*:\s*"([^"]+)"', r.text) or \
                re.search(r"'bdstoken'\s*:\s*'([^']+)'", r.text)
            if m:
                self._bdstoken = m.group(1)
        except Exception:
            pass
        return self._bdstoken or None

    def _params(self, extra: Dict[str, Any]) -> Dict[str, Any]:
        p = dict(extra)
        t = self.bdstoken()
        if t:
            p["bdstoken"] = t
        return p

    def list_page(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        r = self.s.get(f"{BASE}/youai/file/v1/list",
                       params=self._params({"clienttype": 70, "need_filter_hidden": 0,
                                            "cursor": cursor}),
                       timeout=self.timeout)
        data = self._check(r.json())
        return {
            "items": data.get("list") or [],
            "has_more": data.get("has_more") in (1, "1", True),
            "cursor": data.get("cursor"),
        }

    def iter_all(self, limit: int = 0):
        cursor = None
        seen = set()
        n = 0
        while True:
            page = self.list_page(cursor)
            for it in page["items"]:
                yield it
                n += 1
                if limit and n >= limit:
                    return
            if not page["has_more"]:
                return
            nxt = page["cursor"]
            if not nxt or str(nxt) in seen:
                return
            seen.add(str(nxt))
            cursor = nxt

    def get_sign(self) -> Tuple[str, Any]:
        r = self.s.get(f"{BASE}/youai/file/v1/batchdownloadvariable",
                       params=self._params({
                           "fields": '["sign1","sign2","sign3","timestamp"]',
                           "clienttype": 70,
                       }), timeout=self.timeout)
        d = self._check(r.json())
        raw = rc4_variant(d["sign3"], d["sign1"])
        sign = base64.encodebytes(raw.encode("latin1")).decode()
        return sign, d["timestamp"]

    def batch_zip(self, fsids: List[str], zipname: str) -> bytes:
        """取一批文件的 zip 内容。"""
        last: Optional[Exception] = None
        for attempt in range(5):
            try:
                sign, ts = self.get_sign()
                r = self.s.get(
                    f"{BASE}/youai/file/v1/batchdownload",
                    params=self._params({
                        "clienttype": 70,
                        "fsid_list": "[{}]".format(",".join(fsids)),
                        "zipname": zipname,
                        "sign": sign,
                        "timestamp": ts,
                    }),
                    timeout=self.timeout,
                )
                d = self._check(r.json())
                dlink = d.get("dlink")
                if not dlink:
                    raise ApiError("接口未返回 dlink")
                z = self.s.get(dlink, timeout=600,
                               headers={"User-Agent": UA, "Referer": f"{BASE}/"})
                if z.status_code != 200:
                    raise ApiError(f"zip 下载失败 HTTP {z.status_code}")
                if not z.content.startswith(b"PK"):
                    raise ApiError(f"返回内容不是 zip：{z.content[:80]}")
                return z.content
            except RateLimited:
                wait = min(30 * (2 ** attempt) + random.uniform(0, 10), 600)
                log(f"    限流，等待 {wait:.0f}s")
                time.sleep(wait)
                last = RateLimited("持续限流")
            except AuthError:
                raise
            except Exception as exc:
                last = exc
                time.sleep(min(5 * (2 ** attempt), 120))
        raise ApiError(f"批量下载失败：{safe_error(last)}")


# --------------------------------------------------------------------------
# 归档路径
# --------------------------------------------------------------------------
def relpath_for(item: Dict[str, Any], layout: str) -> str:
    path = str(item.get("path") or "")
    name = sanitize(path.rsplit("/", 1)[-1] or f"{item.get('fsid')}.bin")
    if layout == "flat":
        return name
    ts = int(item.get("mtime") or item.get("ctime") or 0)
    if ts < 946684800 or ts > time.time() + 86400:
        sub = "unknown"
    elif layout == "year":
        sub = time.strftime("%Y", time.localtime(ts))
    else:
        sub = time.strftime("%Y/%m", time.localtime(ts))
    return os.path.join(sub, name)


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="一刻相册批量下载（绕开单文件限流）")
    ap.add_argument("--cookie-file", required=True, help="Cookie 文件")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--batch-size", type=int, default=30, help="每批打包多少文件（默认 30）")
    ap.add_argument("--limit", type=int, default=0, help="最多处理多少项（0=全部）")
    ap.add_argument("--layout", choices=["flat", "year", "year-month"], default="year-month")
    ap.add_argument("--sleep", type=float, default=1.0, help="每批之间的间隔秒数")
    args = ap.parse_args()

    out = os.path.abspath(os.path.expanduser(args.out))
    os.makedirs(out, exist_ok=True)
    state = State(os.path.join(out, STATE_FILE))
    client = BatchClient(load_cookies(os.path.expanduser(args.cookie_file)))

    log("获取云端清单…")
    all_items: List[Dict[str, Any]] = []
    for it in client.iter_all(limit=args.limit):
        all_items.append(it)
        if len(all_items) % 500 == 0:
            sys.stderr.write(f"\r  已获取 {len(all_items)} 项…")
            sys.stderr.flush()
    sys.stderr.write("\r" + " " * 40 + "\r")
    log(f"云端共 {len(all_items)} 项")

    # 过滤：已完成的跳过（必须 md5 一致）
    todo: List[Dict[str, Any]] = []
    skipped = 0
    for it in all_items:
        fsid = str(it.get("fsid") or it.get("fs_id"))
        rec = state.get(fsid)
        if rec and rec.get("status") == "ok":
            fp = rec.get("file")
            md5 = str(it.get("md5") or "")
            if fp and os.path.exists(fp) and md5:
                try:
                    if file_md5_bytes(open(fp, "rb").read()) == md5.lower():
                        skipped += 1
                        continue
                except OSError:
                    pass
        todo.append(it)

    log(f"跳过已完成 {skipped} 项，待下载 {len(todo)} 项")

    if not todo:
        log("🎉 没有待下载的文件")
        return 0

    # 分配目标路径
    claimed: Dict[str, str] = {}
    for fsid, rec in state.data["items"].items():
        if rec.get("status") == "ok" and rec.get("file"):
            claimed[os.path.normcase(os.path.abspath(rec["file"]))] = fsid

    planned: List[Tuple[Dict[str, Any], str]] = []
    for it in todo:
        fsid = str(it.get("fsid") or it.get("fs_id"))
        rel = relpath_for(it, args.layout)
        directory = os.path.join(out, os.path.dirname(rel))
        base = os.path.basename(rel)
        stem, ext = os.path.splitext(base)
        dest = os.path.join(directory, base)
        i = 1
        while (os.path.normcase(os.path.abspath(dest)) in claimed
               or (os.path.exists(dest) and os.path.normcase(os.path.abspath(dest)) not in claimed)):
            dest = os.path.join(directory, f"{stem} ({i}){ext}")
            i += 1
        claimed[os.path.normcase(os.path.abspath(dest))] = fsid
        planned.append((it, dest))

    # 分批下载
    total = len(planned)
    done_ok = 0
    done_fail = 0
    failures: List[Dict[str, Any]] = []
    t0 = time.time()

    for start in range(0, total, args.batch_size):
        chunk = planned[start:start + args.batch_size]
        fsids = [str(it.get("fsid") or it.get("fs_id")) for it, _ in chunk]
        zipname = f"opengym-{start}-{len(chunk)}.zip"
        log(f"批次 {start // args.batch_size + 1}/{(total + args.batch_size - 1) // args.batch_size}：{len(chunk)} 个文件")

        try:
            blob = client.batch_zip(fsids, zipname)
        except AuthError:
            log("❌ Cookie 失效，已保存进度")
            state.flush()
            return 2
        except Exception as exc:
            log(f"  批次失败：{safe_error(exc)}")
            for it, dest in chunk:
                fsid = str(it.get("fsid") or it.get("fs_id"))
                state.mark(fsid, status="failed", error=safe_error(exc))
                failures.append({"fsid": fsid, "error": safe_error(exc)})
                done_fail += 1
            state.flush()
            continue

        # 解压并按 md5 匹配到目标文件
        try:
            zf = zipfile.ZipFile(io.BytesIO(blob))
        except Exception as exc:
            log(f"  zip 解析失败：{exc}")
            for it, dest in chunk:
                fsid = str(it.get("fsid") or it.get("fs_id"))
                state.mark(fsid, status="failed", error="zip 解析失败")
                failures.append({"fsid": fsid, "error": "zip 解析失败"})
                done_fail += 1
            state.flush()
            continue

        # 建立 md5 -> 内容 的映射（zip 内文件名可能与 path 不同）
        by_md5: Dict[str, bytes] = {}
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            data = zf.read(name)
            by_md5[file_md5_bytes(data)] = data

        for it, dest in chunk:
            fsid = str(it.get("fsid") or it.get("fs_id"))
            want = str(it.get("md5") or "").lower()
            data = by_md5.get(want)
            if data is None:
                # 尝试按文件名匹配
                fname = os.path.basename(str(it.get("path") or ""))
                hit = None
                for name in zf.namelist():
                    if os.path.basename(name) == fname:
                        cand = zf.read(name)
                        if not want or file_md5_bytes(cand) == want:
                            hit = cand
                            break
                data = hit
            if data is None:
                state.mark(fsid, status="failed", error="zip 中未找到对应文件")
                failures.append({"fsid": fsid, "error": "zip 中未找到对应文件"})
                done_fail += 1
                continue
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                tmp = dest + ".part"
                with open(tmp, "wb") as fh:
                    fh.write(data)
                os.replace(tmp, dest)
                ts = int(it.get("mtime") or it.get("ctime") or 0)
                if ts:
                    os.utime(dest, (ts, ts))
                state.mark(fsid, status="ok", file=dest, md5=want, size=len(data))
                done_ok += 1
            except Exception as exc:
                state.mark(fsid, status="failed", file=dest, error=safe_error(exc))
                failures.append({"fsid": fsid, "error": safe_error(exc)})
                done_fail += 1

        state.flush()
        elapsed = time.time() - t0
        rate = (done_ok + done_fail) / max(elapsed, 1e-6)
        remain = total - done_ok - done_fail
        eta = remain / rate / 60 if rate > 0 else 0
        log(f"  进度 {done_ok + done_fail}/{total}  成功 {done_ok} 失败 {done_fail}  "
            f"ETA {eta:.0f} 分钟")

        if start + args.batch_size < total and args.sleep:
            time.sleep(args.sleep)

    state.flush()
    report = {
        "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": total,
        "ok": done_ok,
        "failed": done_fail,
        "skipped": skipped,
        "failures": failures[:200],
    }
    with open(os.path.join(out, REPORT_FILE), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    log(f"\n{'✅' if done_fail == 0 else '⚠️'} 完成：成功 {done_ok}，失败 {done_fail}，跳过 {skipped}")
    if failures:
        log(f"  失败明细：{os.path.join(out, REPORT_FILE)}")
    return 0 if done_fail == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("已中断，进度已保存")
        sys.exit(1)

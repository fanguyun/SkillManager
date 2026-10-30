#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yike_export.py 的离线端到端测试。

用一个本地 mock 服务器模拟 photo.baidu.com 的四个接口，
验证：认证失败识别、分页游标、MD5 校验、断点续传、去重、归档布局、错误重试。

用法：python3 test_yike_export.py
退出码 0 = 全部通过
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "yike_export.py")

# ---- 测试数据 -------------------------------------------------------------
def _blob(seed: str, size: int) -> bytes:
    out = bytearray()
    i = 0
    while len(out) < size:
        out += hashlib.sha256(f"{seed}:{i}".encode()).digest()
        i += 1
    return bytes(out[:size])


PHOTOS = [
    # (fsid, filename, bytes, mtime)  — 故意让两项内容相同以测试去重
    ("1001", "IMG_0001.jpg", _blob("a", 4096), 1700000000),   # 2023-11
    ("1002", "IMG_0002.jpg", _blob("b", 8192), 1700100000),   # 2023-11
    ("1003", "dup-of-0001.jpg", _blob("a", 4096), 1710000000),  # 2024-03 内容同 1001
    ("1004", "VID_0001.mp4", _blob("c", 16384), 1600000000),  # 2020-09
    ("1005", "IMG_bad.jpg", _blob("d", 2048), 0),             # 时间戳缺失 → unknown
]

# 让 1005 的云端 md5 故意写错，用于验证 MD5 校验能发现问题
CORRUPT_MD5_FOR = "1005"

REQUESTS_SEEN: dict = {}
FAIL_ONCE = {"count": 0}   # 让下载首次失败一次，验证重试
# 由测试用例在进程内切换；不能用环境变量，因为 mock 服务器跑在测试主进程里，
# 读不到被测子进程的 env。
BAD_CURSOR = {"on": False}
# 泄漏检测：把带签名的 dlink 与 bdstoken 塞进响应，验证工具不会把它们写进报告
LEAK = {"on": False}
LEAK_SIG = "SUPERSECRETSIGNATURE12345"
LEAK_TOKEN = "SECRETBDSTOKEN999"
# S-1 回归：跨运行改变云端返回顺序 + 同名同尺寸文件
SHIFT = {"on": False}
# 两台相机拍出同名、且恰好同为 4096 字节的两张不同照片
SHIFT_A = ("7001", "IMG_0001.jpg", _blob("shiftA", 4096), 1700000000)
SHIFT_B = ("7002", "IMG_0001.jpg", _blob("shiftB", 4096), 1700000001)
SHIFT_X = ("7003", "IMG_0001.jpg", _blob("shiftX", 9000), 1700000002)
# S-4 回归：返回非 dict 的 JSON
NON_DICT = {"on": False}
# M-1 回归：has_more 的各种真值形态
HAS_MORE = {"value": None}
# M-2 回归：接口返回空清单
EMPTY = {"on": False}


def item_payload(rec, corrupt=False):
    fsid, name, data, mtime = rec
    real_md5 = hashlib.md5(data).hexdigest()
    md5 = ("0" * 32) if corrupt else real_md5
    return {
        "fsid": int(fsid),
        "path": f"/youa/web/{name}",
        "md5": md5,
        "size": len(data),
        "ctime": mtime,
        "mtime": mtime,
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # 静音
        pass

    def _send(self, code, body: bytes, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj):
        self._send(200, json.dumps(obj).encode())

    # ------------------------------------------------------------------
    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        path = u.path

        # 首页：提供 bdstoken
        if path == "/photo/web/home":
            REQUESTS_SEEN["home"] = REQUESTS_SEEN.get("home", 0) + 1
            html = b"<script>var templateData={'bdstoken':'testtoken123'};</script>"
            self._send(200, html, "text/html")
            return

        # 无 cookie → errno -6
        if "BDUSS" not in (self.headers.get("Cookie") or ""):
            self._json({"errno": -6, "request_id": 1})
            return

        # 列表接口：每页 2 项，游标分页
        if path == "/youai/file/v1/list":
            cursor = (q.get("cursor") or [None])[0]

            # S-4 回归：返回 JSON 数组 / 字符串 / null，而不是对象
            if NON_DICT["on"]:
                self._send(200, b'[{"fsid":1,"path":"/x.jpg"}]')
                return

            # M-2 回归：账号看起来是空的
            if EMPTY["on"]:
                self._json({"errno": 0, "list": [], "has_more": 0, "cursor": "0"})
                return

            # S-1 回归：跨运行改变顺序 —— 第二轮把新增的 X 插到最前
            if SHIFT["on"]:
                items = [SHIFT_X, SHIFT_A, SHIFT_B] if SHIFT["round"] == 2 \
                    else [SHIFT_A, SHIFT_B]
                if cursor:
                    items = []
                self._json({
                    "errno": 0,
                    "list": [item_payload(r) for r in items],
                    "has_more": 0,
                    "cursor": "0",
                })
                return

            # 异常模式：首屏就声称 has_more=1 却不给可用游标（真实服务端出现过）
            if BAD_CURSOR["on"] and not cursor:
                self._json({
                    "errno": 0,
                    "list": [item_payload(PHOTOS[0])],
                    "has_more": 1,
                    "cursor": "",
                })
                return
            start = int(cursor) if cursor else 0
            page = PHOTOS[start:start + 2]
            nxt = start + 2
            has_more = 1 if nxt < len(PHOTOS) else 0
            # M-1 回归：只在首页注入 has_more 的其它真值形态。
            # 若工具不把它当"还有下一页"，就会在第一页后静默停下，
            # 只导出 2 项而不是 5 项 —— 用清单条数即可判定。
            if HAS_MORE["value"] is not None and not cursor:
                has_more = HAS_MORE["value"]
            self._json({
                "errno": 0,
                "list": [item_payload(r, corrupt=(r[0] == CORRUPT_MD5_FOR)) for r in page],
                "has_more": has_more,
                "cursor": str(nxt),
            })
            return

        # 相册列表
        if path == "/youai/album/v1/list":
            self._json({
                "errno": 0,
                "list": [{"album_id": "9001", "title": "测试相册", "amount": 2, "mtime": 1710000000}],
                "has_more": 0,
                "cursor": "0",
            })
            return

        # 相册内文件
        if path == "/youai/album/v1/listfile":
            self._json({
                "errno": 0,
                "list": [item_payload(PHOTOS[0]), item_payload(PHOTOS[1])],
                "has_more": 0,
                "cursor": "0",
            })
            return

        # 取 dlink
        if path == "/youai/file/v2/download":
            fsid = (q.get("fsid") or [""])[0]
            if LEAK["on"]:
                # 带签名直链 + bdstoken，模拟真实响应
                self._json({
                    "errno": 0,
                    "dlink": f"http://127.0.0.1:{PORT}/dl/{fsid}"
                             f"?sign={LEAK_SIG}&bdstoken={LEAK_TOKEN}",
                })
                return
            self._json({"errno": 0, "dlink": f"http://127.0.0.1:{PORT}/dl/{fsid}"})
            return

        # 实际文件内容
        if path.startswith("/dl/"):
            fsid = path.rsplit("/", 1)[-1]
            if LEAK["on"]:
                # 泄漏测试需要走失败路径，才能让错误信息进入报告
                self._send(500, b"boom", "text/plain")
                return
            # 首次请求 1002 时故意返回 500，验证重试
            if fsid == "1002" and FAIL_ONCE["count"] == 0:
                FAIL_ONCE["count"] += 1
                self._send(500, b"boom", "text/plain")
                return
            for r in PHOTOS + [SHIFT_A, SHIFT_B, SHIFT_X]:
                if r[0] == fsid:
                    self._send(200, r[2], "application/octet-stream")
                    return
            self._send(404, b"nope", "text/plain")
            return

        self._json({"errno": -9, "msg": f"unknown {path}"})

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/youai/album/v1/listfile":
            self._json({
                "errno": 0,
                "list": [item_payload(PHOTOS[0]), item_payload(PHOTOS[1])],
                "has_more": 0,
                "cursor": "0",
            })
            return
        self._json({"errno": -9})


PORT = 0


def start_server():
    global PORT
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    srv.daemon_threads = True
    PORT = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


# ---- 测试框架 -------------------------------------------------------------
PASS, FAIL = [], []


def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print(f"  ✅ {name}")
    else:
        FAIL.append((name, detail))
        print(f"  ❌ {name}  {detail}")


def run(args, expect_code=None, env_extra=None):
    env = dict(os.environ)
    env["YIKE_BASE_URL"] = f"http://127.0.0.1:{PORT}"
    env.update(env_extra or {})
    p = subprocess.run(
        [sys.executable, SCRIPT] + args,
        capture_output=True, text=True, env=env, timeout=180,
    )
    if expect_code is not None:
        check(
            f"退出码 = {expect_code}（实际 {p.returncode}）",
            p.returncode == expect_code,
            f"\nSTDOUT:\n{p.stdout[-1500:]}\nSTDERR:\n{p.stderr[-1500:]}",
        )
    return p


def main():
    srv = start_server()
    print(f"mock 服务器: http://127.0.0.1:{PORT}\n")
    tmp = tempfile.mkdtemp(prefix="yike-test-")
    good_cookie = "BDUSS=abc; STOKEN=def"
    bad_cookie = "OTHER=1"

    try:
        print("【1】认证失败应被识别（errno=-6 → 退出码 2）")
        p = run(["check", "--cookie-json", json.dumps({"OTHER": "1"})], expect_code=2)
        check("提示 Cookie 失效", "Cookie 已失效" in (p.stdout + p.stderr))

        print("\n【2】check 应统计出全部项目")
        p = run(["check", "--cookie-json", '{"BDUSS":"abc","STOKEN":"def"}'], expect_code=0)
        check("统计到 5 项", "项目总数：5" in p.stdout, p.stdout)
        check("识别 1 个视频", "视频 1" in p.stdout, p.stdout)
        check("取到 bdstoken", "testtoken123" in p.stdout, p.stdout)

        print("\n【3】list 应输出 JSONL + CSV 清单")
        out_list = os.path.join(tmp, "list")
        p = run(["list", "--cookie-json", '{"BDUSS":"abc"}', "--out", out_list], expect_code=0)
        jl = os.path.join(out_list, "yike-inventory.jsonl")
        cv = os.path.join(out_list, "yike-inventory.csv")
        check("JSONL 存在", os.path.exists(jl))
        check("CSV 存在", os.path.exists(cv))
        if os.path.exists(jl):
            lines = [l for l in open(jl, encoding="utf-8") if l.strip()]
            check("JSONL 有 5 行", len(lines) == 5, f"实际 {len(lines)}")
            check("JSONL 含 md5 字段", '"md5"' in lines[0], lines[0][:200])

        print("\n【4】albums 应列出相册")
        p = run(["albums", "--cookie-json", '{"BDUSS":"abc"}'], expect_code=0)
        check("列出测试相册", "测试相册" in p.stdout and "9001" in p.stdout, p.stdout)

        print("\n【5】dry-run 不应写入任何文件")
        out_dry = os.path.join(tmp, "dry")
        p = run(["download", "--cookie-json", '{"BDUSS":"abc"}', "--out", out_dry,
                 "--dry-run"], expect_code=0)
        check("dry-run 报告待下载数", "待下载" in p.stdout, p.stdout)
        files = [f for f in os.listdir(out_dry)] if os.path.exists(out_dry) else []
        check("dry-run 未下载文件", not any(f.endswith((".jpg", ".mp4")) for f in files), str(files))

        print("\n【6】download 全量下载 + 断点续传 + 去重")
        out = os.path.join(tmp, "dl")
        p = run(["download", "--cookie-json", '{"BDUSS":"abc"}', "--out", out,
                 "--jobs", "3", "--file-retries", "3"], expect_code=1)  # 1005 故意 MD5 错 → 1
        check("报告含失败项", "失败 1" in p.stdout, p.stdout)
        check("重试后 1002 成功", "新下载 3" in p.stdout, p.stdout)
        check("去重生效（1003 复用 1001）", "去重 1" in p.stdout, p.stdout)

        got = {}
        for root, _, fnames in os.walk(out):
            for fn in fnames:
                fp = os.path.join(root, fn)
                got[fn] = os.path.getsize(fp)
        check("IMG_0001.jpg 已下载", "IMG_0001.jpg" in got, str(sorted(got)))
        check("IMG_0002.jpg 已下载（重试成功）", "IMG_0002.jpg" in got)
        check("VID_0001.mp4 已下载", "VID_0001.mp4" in got)
        check("损坏项 IMG_bad.jpg 未留下残file",
              "IMG_bad.jpg" not in got, str(sorted(got)))

        if "IMG_0001.jpg" in got and "dup-of-0001.jpg" in got:
            h1 = hashlib.md5(open(os.path.join(out, "IMG_0001.jpg"), "rb").read()).hexdigest()
            h2 = hashlib.md5(open(os.path.join(out, "dup-of-0001.jpg"), "rb").read()).hexdigest()
            check("去重后内容一致", h1 == h2)
            st1, st2 = os.stat(os.path.join(out, "IMG_0001.jpg")), os.stat(os.path.join(out, "dup-of-0001.jpg"))
            check("硬链接生效（inode 相同）", st1.st_ino == st2.st_ino,
                  f"{st1.st_ino} vs {st2.st_ino}")

        # 时间戳应被还原
        if "IMG_0001.jpg" in got:
            mt = os.stat(os.path.join(out, "IMG_0001.jpg")).st_mtime
            check("还原拍摄时间戳", abs(mt - 1700000000) < 2, str(mt))

        print("\n【7】断点续传：重跑不应重复下载")
        p = run(["download", "--cookie-json", '{"BDUSS":"abc"}', "--out", out,
                 "--jobs", "3", "--file-retries", "3"], expect_code=1)
        # 1001/1002/1004 已下载 + 1003 已去重落盘 = 4 项跳过；仅 1005 仍失败
        check("第二次跳过已完成项", "跳过 4" in p.stdout, p.stdout)
        check("第二次不再重复下载", "新下载 0" in p.stdout, p.stdout)

        print("\n【8】verify 应检出 MD5 不一致的文件")
        p = run(["verify", "--out", out], expect_code=0)
        # 1001、1002、1004 下载 + 1003 去重落盘 = 4 个合格文件
        check("校验通过 4 个文件", "4 个通过 MD5 比对" in p.stdout, p.stdout)
        check("失败记录不计入校验", "未纳入校验" in p.stdout, p.stdout)

        # 人为篡改一个文件，verify 必须发现
        victim = os.path.join(out, "IMG_0001.jpg")
        with open(victim, "ab") as fh:
            fh.write(b"tampered")
        p = run(["verify", "--out", out], expect_code=1)
        check("篡改后 verify 失败", "MD5 与云端不一致" in p.stdout, p.stdout)

        print("\n【9】--layout year-month 应按年月归档")
        out2 = os.path.join(tmp, "dl2")
        p = run(["download", "--cookie-json", '{"BDUSS":"abc"}', "--out", out2,
                 "--layout", "year-month", "--jobs", "2", "--file-retries", "3"], expect_code=1)
        dirs = set()
        for root, dnames, _ in os.walk(out2):
            for d in dnames:
                dirs.add(os.path.relpath(os.path.join(root, d), out2))
        check("生成 2023/11 目录", "2023/11" in dirs, str(sorted(dirs)))
        check("生成 2020/09 目录", "2020/09" in dirs, str(sorted(dirs)))
        check("生成 unknown 目录", "unknown" in dirs, str(sorted(dirs)))

        print("\n【10】--album 只导出指定相册")
        out3 = os.path.join(tmp, "dl3")
        p = run(["download", "--cookie-json", '{"BDUSS":"abc"}', "--out", out3,
                 "--album", "9001", "--jobs", "2"], expect_code=0)
        check("相册模式成功", "新下载 2" in p.stdout, p.stdout)

        print("\n【11】--limit 应限制数量")
        out4 = os.path.join(tmp, "dl4")
        p = run(["download", "--cookie-json", '{"BDUSS":"abc"}', "--out", out4,
                 "--limit", "1", "--jobs", "1"], expect_code=0)
        check("只下载 1 项", "新下载 1" in p.stdout, p.stdout)

        print("\n【12】分页异常（has_more=1 但游标为空）不得静默漏下载")
        # 回归测试：曾出现 has_more=1 + cursor="" 被当作末页，静默只下第一批
        out5 = os.path.join(tmp, "dl5")
        BAD_CURSOR["on"] = True
        try:
            p = run(["download", "--cookie-json", '{"BDUSS":"abc"}', "--out", out5,
                     "--jobs", "1"], expect_code=1)
        finally:
            BAD_CURSOR["on"] = False
        check("报告分页异常警告", "清单可能不完整" in p.stdout + p.stderr,
              p.stdout + p.stderr)
        check("在下载前即中止", "未开始下载" in p.stdout + p.stderr, p.stdout + p.stderr)
        leftover = []
        for root, _, fnames in os.walk(out5):
            leftover += [f for f in fnames if f.endswith((".jpg", ".mp4"))]
        check("中止时不落盘任何媒体文件", not leftover, str(leftover))

        print("\n【14】失败报告不得泄漏 dlink 签名 / bdstoken")
        # dlink 是带签名的临时直链，report.json 常被随手分享或提交
        out7 = os.path.join(tmp, "dl7")
        LEAK["on"] = True
        try:
            p = run(["download", "--cookie-json", '{"BDUSS":"abc"}', "--out", out7,
                     "--jobs", "1", "--file-retries", "1"], expect_code=1)
        finally:
            LEAK["on"] = False
        report_path = os.path.join(out7, "yike-export-report.json")
        state_path = os.path.join(out7, ".yike-state.json")
        combined = ""
        for path in (report_path, state_path):
            if os.path.exists(path):
                combined += open(path, encoding="utf-8").read()
        combined += p.stdout + p.stderr
        check("报告不含 dlink 签名", LEAK_SIG not in combined,
              "签名被写进了报告/输出")
        check("报告不含 bdstoken", LEAK_TOKEN not in combined,
              "bdstoken 被写进了报告/输出")
        check("错误信息仍可读", "已脱敏" in combined, combined[-400:])

        print("\n【15】--allow-partial 应允许在已知不完整时继续")
        out6 = os.path.join(tmp, "dl6")
        BAD_CURSOR["on"] = True
        try:
            p = run(["download", "--cookie-json", '{"BDUSS":"abc"}', "--out", out6,
                     "--jobs", "1", "--allow-partial"], expect_code=0)
        finally:
            BAD_CURSOR["on"] = False
        check("仍下载已有清单", "新下载 1" in p.stdout, p.stdout)
        check("依然打印警告", "清单可能不完整" in p.stdout + p.stderr, p.stdout)

        print("\n【16】S-1 回归：跨运行顺序变化 + 同名同尺寸，不得覆盖原图")
        # 曾出现：两台相机的 IMG_0001.jpg 同为 4096B，第 2 轮新增照片插队后
        # 旧原图被覆盖且永久丢失，工具还报成功。
        out8 = os.path.join(tmp, "shift")
        SHIFT["on"] = True
        SHIFT["round"] = 1
        try:
            p1 = run(["download", "--cookie-json", '{"BDUSS":"abc"}', "--out", out8,
                      "--jobs", "1"], expect_code=0)
        finally:
            SHIFT["on"] = False
        md5_a = hashlib.md5(SHIFT_A[2]).hexdigest()
        md5_b = hashlib.md5(SHIFT_B[2]).hexdigest()

        def disk_md5s(root):
            found = {}
            for r, _, fns in os.walk(root):
                for f in fns:
                    if f.endswith(".jpg"):
                        found[f] = hashlib.md5(open(os.path.join(r, f), "rb").read()).hexdigest()
            return found

        first = disk_md5s(out8)
        check("第1轮两张原图都在", md5_a in first.values() and md5_b in first.values(),
              str(first))

        SHIFT["on"] = True
        SHIFT["round"] = 2
        try:
            p2 = run(["download", "--cookie-json", '{"BDUSS":"abc"}', "--out", out8,
                      "--jobs", "1"], expect_code=0)
        finally:
            SHIFT["on"] = False
        second = disk_md5s(out8)
        md5_x = hashlib.md5(SHIFT_X[2]).hexdigest()
        check("第2轮后 A 的原图仍在（未被覆盖）", md5_a in second.values(), str(second))
        check("第2轮后 B 的原图仍在", md5_b in second.values(), str(second))
        check("第2轮新增的 X 也下来了", md5_x in second.values(), str(second))

        # state 里每个 fsid 记录的文件内容必须与其云端 md5 相符
        st = json.load(open(os.path.join(out8, ".yike-state.json"), encoding="utf-8"))
        mismatched = []
        for fsid, rec in st["items"].items():
            if rec.get("status") != "ok" or not rec.get("md5"):
                continue
            fp = rec.get("file")
            if not fp or not os.path.exists(fp):
                mismatched.append((fsid, "文件不存在"))
                continue
            if hashlib.md5(open(fp, "rb").read()).hexdigest() != rec["md5"]:
                mismatched.append((fsid, "内容与记录 md5 不符"))
        check("state 记录与实际内容全部对应", not mismatched, str(mismatched))

        print("\n【17】S-4 回归：非 dict JSON 响应应报错而非裸崩")
        out9 = os.path.join(tmp, "nondict")
        NON_DICT["on"] = True
        try:
            p = run(["check", "--cookie-json", '{"BDUSS":"abc"}'])
        finally:
            NON_DICT["on"] = False
        check("退出码为 1（不是未捕获异常）", p.returncode == 1, f"rc={p.returncode}")
        check("无 Python traceback", "Traceback" not in (p.stdout + p.stderr),
              (p.stdout + p.stderr)[-400:])
        check("给出可读的接口错误", "接口返回的不是 JSON 对象" in (p.stdout + p.stderr),
              (p.stdout + p.stderr)[-400:])

        print("\n【18】M-1 回归：has_more 的各种真值形态都应被识别为「还有下一页」")
        # 曾出现：只认 (1,"1",True)，遇到 "true"/2 就当末页 → 静默只导出第一页
        for label, value in (("'true'", "true"), ("2", 2), ("'1'", "1"), ("True", True)):
            out10 = os.path.join(tmp, "hm-" + re.sub(r"\W", "", label))
            HAS_MORE["value"] = value
            try:
                p = run(["list", "--cookie-json", '{"BDUSS":"abc"}', "--out", out10])
            finally:
                HAS_MORE["value"] = None
            jl = os.path.join(out10, "yike-inventory.jsonl")
            n = 0
            if os.path.exists(jl):
                n = len([l for l in open(jl, encoding="utf-8") if l.strip()])
            check(f"has_more={label} 时导出全部 5 项（实际 {n}）", n == 5,
                  f"只导出了 {n} 项，说明被当成末页静默截断")

        print("\n【19】M-2 回归：空清单不得报成功")
        out11 = os.path.join(tmp, "empty")
        EMPTY["on"] = True
        try:
            p = run(["download", "--cookie-json", '{"BDUSS":"abc"}', "--out", out11,
                     "--jobs", "1"])
        finally:
            EMPTY["on"] = False
        check("空清单退出码非 0", p.returncode == 1, f"rc={p.returncode}\n{p.stdout}")
        check("明确警告未下载任何文件",
              "云端清单为空" in (p.stdout + p.stderr), (p.stdout + p.stderr)[-300:])
        check("不宣称备份完成", "✅ 完成" not in p.stdout, p.stdout[-300:])

        print("\n【20】S-2 回归：去重不得把内容不符的文件当可信源")
        # 预置一个同名同尺寸、但内容错误的文件，工具必须重新下载正确内容，
        # 且绝不能把错误内容硬链接/复制给同 md5 的其它项。
        out12 = os.path.join(tmp, "dedupwrong")
        os.makedirs(out12, exist_ok=True)
        real_bytes = _blob("a", 4096)          # PHOTOS[0] 与 PHOTOS[2] 的真实内容
        open(os.path.join(out12, "IMG_0001.jpg"), "wb").write(_blob("WRONG", 4096))
        p = run(["download", "--cookie-json", '{"BDUSS":"abc"}', "--out", out12,
                 "--limit", "3", "--jobs", "1", "--file-retries", "1"], expect_code=0)
        real_md5 = hashlib.md5(real_bytes).hexdigest()
        wrong_md5 = hashlib.md5(_blob("WRONG", 4096)).hexdigest()
        on_disk = {}
        for r, _, fns in os.walk(out12):
            for f in fns:
                if f.endswith(".jpg"):
                    on_disk[f] = hashlib.md5(open(os.path.join(r, f), "rb").read()).hexdigest()
        check("正确内容已下载到磁盘", real_md5 in on_disk.values(), str(on_disk))
        check("错误内容未被复制给其它项",
              list(on_disk.values()).count(wrong_md5) <= 1, str(on_disk))
        check("提示既有同名文件被占用",
              "已被内容不同的既有文件占用" in (p.stdout + p.stderr), p.stdout[-400:])

    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 62)
    print(f"通过 {len(PASS)} 项，失败 {len(FAIL)} 项")
    if FAIL:
        print("\n失败明细：")
        for name, detail in FAIL:
            print(f"  ❌ {name}\n{detail}")
        return 1
    print("🎉 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

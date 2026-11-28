#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一刻相册长时间续传驱动。

背景：百度对 `file/v2/download` 接口做了**账号级**限流（errno 50005）。
一旦触发，短则几十分钟、长则一天才恢复。手工反复重试只会加剧封禁。

本脚本的策略：
  1. 用一个**单次**轻量探测判断下载接口是否已解封（绝不狂刷）。
  2. 未解封 → 指数退避等待（最长 45 分钟一次），期间完全不发请求。
  3. 已解封 → 调用 yike_export.py 下载，并发保守（2），失败项少。
  4. 每轮结束检查状态文件；全部成功则退出。
  5. 全程写日志到 ~/Pictures/yike/resume.log，可随时 Ctrl-C。

用法：
    python3 yike-resume.py              # 默认最长跑 24 小时
    python3 yike-resume.py --max-hours 48
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime

HOME = os.path.expanduser("~")
OUT = os.path.join(HOME, "Pictures", "yike")
LOG = os.path.join(OUT, "resume.log")
STATE = os.path.join(OUT, ".yike-state.json")
COOKIE = "/tmp/yike-cookie.txt"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADER = os.path.join(SCRIPT_DIR, "yike_export.py")
BASE = "https://photo.baidu.com"

EXPECTED_TOTAL = 7405   # 云端总数，用于判断是否真的下完


def log(msg: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    os.makedirs(OUT, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def read_cookies() -> str:
    with open(COOKIE, "r", encoding="utf-8") as fh:
        return fh.read().strip()


def state_counts() -> tuple[int, int, int]:
    """返回 (ok, failed, total_records)。"""
    try:
        with open(STATE, "r", encoding="utf-8") as fh:
            items = json.load(fh)["items"]
    except Exception:
        return 0, 0, 0
    ok = sum(1 for v in items.values() if v.get("status") == "ok")
    bad = sum(1 for v in items.values() if v.get("status") == "failed")
    return ok, bad, len(items)


def probe_download() -> str:
    """用单次请求探测下载接口状态。返回 'ok' / 'limited' / 'auth' / 'error'。"""
    import requests

    cookies = {}
    for chunk in read_cookies().split(";"):
        if "=" in chunk:
            k, _, v = chunk.partition("=")
            cookies[k.strip()] = v.strip()

    s = requests.Session()
    s.cookies.update(cookies)
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"{BASE}/photo/web/home",
    })
    try:
        # 先拿一个 fsid（列表接口不受限流影响）
        r = s.get(f"{BASE}/youai/file/v1/list",
                  params={"clienttype": 70, "need_filter_hidden": 0}, timeout=30)
        data = r.json()
        if data.get("errno") == -6:
            return "auth"
        lst = data.get("list") or []
        if not lst:
            return "error"
        fsid = lst[0].get("fsid")

        # 探测下载接口
        r2 = s.get(f"{BASE}/youai/file/v2/download",
                   params={"clienttype": 70, "fsid": fsid}, timeout=30)
        d2 = r2.json()
        errno = d2.get("errno")
        if errno == 0:
            return "ok"
        if errno == -6:
            return "auth"
        if errno == 50005:
            return "limited"
        return "error"
    except Exception as exc:
        log(f"  探测异常：{type(exc).__name__}: {exc}")
        return "error"


def run_download() -> int:
    """调用下载器。返回其退出码。"""
    cmd = [
        sys.executable, DOWNLOADER, "download",
        "--cookie-file", COOKIE,
        "--out", OUT,
        "--jobs", "2",
        "--file-retries", "2",
        "--layout", "year-month",
    ]
    log(f"  启动下载：{' '.join(cmd[-8:])}")
    try:
        p = subprocess.run(cmd, timeout=6 * 3600)
        return p.returncode
    except subprocess.TimeoutExpired:
        log("  下载单轮超时（6h），将重启下一轮")
        return 1
    except KeyboardInterrupt:
        log("  用户中断")
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-hours", type=float, default=24.0,
                    help="最长运行小时数（默认 24）")
    args = ap.parse_args()

    if not os.path.exists(COOKIE):
        log(f"❌ 找不到 Cookie 文件：{COOKIE}")
        return 3

    log("=" * 60)
    log(f"续传驱动启动（最长 {args.max_hours} 小时）")
    ok, bad, total = state_counts()
    log(f"起始状态：已完成 {ok} / 失败 {bad} / 已记录 {total}（云端 {EXPECTED_TOTAL}）")

    deadline = time.time() + args.max_hours * 3600
    wait_round = 0

    while time.time() < deadline:
        ok, bad, total = state_counts()

        # 完成判据：没有失败项，且记录数接近云端总数
        if bad == 0 and ok >= EXPECTED_TOTAL * 0.995:
            log(f"🎉 全部完成：{ok} 个文件，无失败项")
            return 0

        log(f"--- 当前 {ok} 完成 / {bad} 失败 / 共记录 {total} ---")

        status = probe_download()
        log(f"  下载接口探测：{status}")

        if status == "auth":
            log("❌ Cookie 已失效，无法继续。请重新获取 Cookie 后重启本脚本。")
            return 2
        if status == "error":
            log("  接口异常（非限流），等待 10 分钟后重试")
            time.sleep(600)
            continue

        if status == "limited":
            wait_round += 1
            # 5, 10, 20, 30, 45, 45... 分钟
            minutes = min(5 * (2 ** (wait_round - 1)), 45)
            jitter = random.uniform(0, 120)
            wait = minutes * 60 + jitter
            remain = deadline - time.time()
            if wait > remain:
                log(f"  下次等待 {wait/60:.0f} 分钟会超出时限，退出")
                return 1
            log(f"  仍被限流，静默等待 {wait/60:.1f} 分钟（不发任何请求）")
            time.sleep(wait)
            continue

        # status == "ok"
        wait_round = 0
        log("  ✅ 下载接口已解封，开始下载")
        rc = run_download()
        ok2, bad2, total2 = state_counts()
        gained = ok2 - ok
        log(f"  本轮结束 rc={rc}：完成 {ok2}（+{gained}）/ 失败 {bad2} / 记录 {total2}")

        if gained == 0 and bad2 > 0:
            # 一个都没下成，可能是刚又触发限流，退避后再试
            log("  本轮无进展，等待 10 分钟后重新探测")
            time.sleep(600)
        elif gained > 0:
            # 有进展就稍作停顿，避免连续高压
            time.sleep(random.uniform(20, 60))

    log("⏰ 达到最长运行时间，退出。重跑本脚本可继续。")
    ok, bad, _ = state_counts()
    log(f"最终状态：已完成 {ok} / 失败 {bad}")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("已手动中断。重跑本脚本可继续。")
        sys.exit(1)

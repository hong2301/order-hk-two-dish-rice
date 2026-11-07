#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""启动一个带登录态的浏览器（通用：Threads / Instagram / 其他平台）。

用法：
  python scripts/browse_session.py --profile threads --port 9225 --url https://www.threads.com/
  python scripts/browse_session.py --profile threads --port 9225 --login     # 打开登录页
  python scripts/browse_session.py --port 9225 --check                       # 只看登录态

登录态存在 profile 目录里（不是端口上）：同一 profile 重复启动会复用已登录会话。
"""
from __future__ import annotations

import argparse
import json
import os
import time

from DrissionPage import Chromium, ChromiumOptions

PROFILE_ROOT = r"C:\Users\jiang\.pi\agent\browser-profile"
BROWSER = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROXY = os.environ.get("PROXY_URL", "http://192.168.31.238:7897")


def port_alive(port: int) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def launch(profile: str, port: int, url: str, proxy: str, headless: bool = False):
    prof = os.path.join(PROFILE_ROOT, profile)
    os.makedirs(prof, exist_ok=True)
    if port_alive(port):
        br = Chromium(port)
        print(f"[附着] 端口 {port} 已有浏览器")
    else:
        co = ChromiumOptions()
        co.set_browser_path(BROWSER)
        co.set_user_data_path(prof)
        co.set_local_port(port)
        if proxy and proxy.lower() != "none":
            co.set_proxy(proxy)
        co.set_argument("--no-first-run")
        co.set_argument("--disable-blink-features=AutomationControlled")
        co.headless(headless)
        br = Chromium(co)
        try:
            br.set.window.size(1500, 950)
        except Exception:
            pass
        print(f"[启动] profile={profile} 端口={port} 代理={proxy}")
    tab = br.latest_tab
    tab.get(url)
    return br, tab


def status(tab):
    try:
        ck = tab.cookies()
    except Exception:
        ck = []
    names = {c.get("name") for c in ck}
    who = ""
    for k in ("ds_user_id", "user_id", "user_id_v2"):
        for c in ck:
            if c.get("name") == k:
                who = c.get("value")
                break
        if who:
            break
    return {"url": tab.url, "title": (tab.title or "")[:40], "cookies": len(ck),
            "session": bool(names & {"sessionid", "sessionid_ss", "csrftoken"}),
            "user_id": who}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="threads")
    ap.add_argument("--port", type=int, default=9225)
    ap.add_argument("--proxy", default=PROXY)
    ap.add_argument("--url", default="https://www.threads.com/")
    ap.add_argument("--login", action="store_true", help="打开登录页")
    ap.add_argument("--check", action="store_true", help="只检查登录态，不导航")
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()

    if args.check:
        if not port_alive(args.port):
            print(f"端口 {args.port} 没有浏览器，先启动一个")
            return
        br = Chromium(args.port)
        print(json.dumps(status(br.latest_tab), ensure_ascii=False))
        return

    url = args.url
    if args.login:
        if "threads" in url:
            url = "https://www.threads.com/login/"
        elif "instagram" in url:
            url = "https://www.instagram.com/accounts/login/"
    br, tab = launch(args.profile, args.port, url, args.proxy, args.headless)
    time.sleep(4)
    print("状态:", json.dumps(status(tab), ensure_ascii=False))
    print(f"\n浏览器已打开（端口 {args.port}，profile {args.profile}）。登录完成后告诉我。")


if __name__ == "__main__":
    main()

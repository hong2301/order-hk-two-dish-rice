#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""采集 YouTube 视频字幕（正文 spoken content）。

用登录后的 cookies（.tmp/yt_cookies.txt，由 scripts/browse_session.py 的 profile 导出）
+ yt-dlp 只解析信息（不下载视频），取 subtitles / automatic_captions 里的 json3 轨，
拼成全文。

用法：
  python scripts/fetch_youtube_subs.py            # 全量（断点续跑）
  python scripts/fetch_youtube_subs.py --limit 10 # 小样
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import requests
from yt_dlp import YoutubeDL

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
OUT = os.path.join(DATA, "youtube_subs.jsonl")
COOKIES = os.path.join(BASE, ".tmp", "yt_cookies.txt")
PROXY = os.environ.get("PROXY_URL", "http://192.168.31.238:7897")

PREF = ("zh-Hant", "zh-Hans", "zh-TW", "zh-HK", "zh", "en", "en-US")
LOCK = threading.Lock()
STAT = defaultdict(int)
REQ = requests.Session()
REQ.proxies = {"http": PROXY, "https": PROXY}
REQ.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"})


def load_cookies(path):
    if not os.path.exists(path):
        return
    try:
        from http.cookiejar import MozillaCookieJar
        jar = MozillaCookieJar(path)
        jar.load(ignore_discard=True, ignore_expires=True)
        REQ.cookies.update(jar)
    except Exception:
        pass


load_cookies(COOKIES)


def now_cn():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def vtt_to_text(raw: str) -> str:
    lines = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln or "-->" in ln or ln.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        if re.fullmatch(r"\d+", ln):
            continue
        lines.append(re.sub(r"<[^>]+>", "", ln))
    out = " ".join(lines)
    return " ".join(out.split())


def json3_to_text(url: str, ext: str = "json3") -> str:
    try:
        r = REQ.get(url, timeout=45)
        if r.status_code != 200 or not r.text.strip():
            return ""
        if ext != "json3":
            return vtt_to_text(r.text)
        j = r.json()
        parts = []
        for e in j.get("events") or []:
            for s in e.get("segs") or []:
                parts.append(s.get("utf8") or "")
            parts.append(" ")
        txt = "".join(parts)
        return " ".join(txt.split())
    except Exception:
        return ""


def job(row):
    vid = row["video_id"]
    out = {"video_id": vid, "title": row.get("title", ""), "channel": row.get("channel", ""),
           "published_at": row.get("published_at", ""), "lang": "", "kind": "",
           "text": "", "text_len": 0, "status": "", "fetched_at": now_cn()}
    opts = {
        "cookiefile": COOKIES if os.path.exists(COOKIES) else None,
        "quiet": True, "no_warnings": True, "skip_download": True,
        "ignore_no_formats_error": True, "proxy": PROXY,
    }
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
    except Exception as e:
        out["status"] = f"err_{type(e).__name__}"
        return out

    manual = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    if not manual and not auto:
        out["status"] = "no_subs"
        return out
    for pool, kind in ((manual, "manual"), (auto, "auto")):
        for lang in PREF:
            if lang not in pool:
                continue
            fmts = pool[lang] or []
            pick = next((f for f in fmts if f.get("ext") == "json3"), None) or \
                   next((f for f in fmts if f.get("ext") in ("vtt", "srv1", "srv3")), None)
            if not pick:
                continue
            txt = json3_to_text(pick["url"]) if pick.get("ext") == "json3" else ""
            if txt:
                out.update({"lang": lang, "kind": kind, "text": txt,
                            "text_len": len(txt), "status": "ok"})
                return out
    out["status"] = "no_text"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--retry", action="store_true", help="重跑 no_text / 错误项")
    ap.add_argument("--delay", type=float, default=1.5, help="每个视频处理后的等待秒数")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(os.path.join(DATA, "youtube_2022-2026.csv"), encoding="utf-8-sig")))
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT, encoding="utf-8"):
            try:
                d = json.loads(line)
                if d.get("status") in (("ok", "no_subs", "no_text") if not args.retry else ("ok", "no_subs")):
                    done.add(d["video_id"])
            except Exception:
                pass
    todo = [r for r in rows if r["video_id"] not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"共 {len(rows)} 条，已完成 {len(done)}，待采 {len(todo)}", flush=True)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex, open(OUT, "a", encoding="utf-8") as f:
        for i, res in enumerate(ex.map(job, todo), start=1):
            with LOCK:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
                f.flush()
                STAT[res["status"]] += 1
            if i % 20 == 0:
                print(f"  {i}/{len(todo)} {dict(STAT)} {time.time()-t0:.0f}s", flush=True)
    print("完成:", dict(STAT), flush=True)
    print("输出:", OUT, flush=True)


if __name__ == "__main__":
    main()

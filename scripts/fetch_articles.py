#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""抓取需求 2 报道/节目页的正文全文。

输入：data/google_news_2022-2026.csv（报社、电视台、生活媒体、聚合页）
输出：data/articles.jsonl（每行一篇：url/title/正文/字数/抓取状态）

用法：
  python scripts/fetch_articles.py            # 全量（断点续跑）
  python scripts/fetch_articles.py --limit 30 # 小样
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import requests
import trafilatura

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
OUT = os.path.join(DATA, "articles.jsonl")
PROXY = os.environ.get("PROXY_URL", "http://192.168.31.238:7897")
PROXIES = {"http": PROXY, "https": PROXY}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

TARGET_TYPES = ("news", "tv", "lifestyle", "aggregator", "intl_media")
LOCK = threading.Lock()
DOMAIN_SEM = defaultdict(lambda: threading.Semaphore(2))   # 单域名最多 2 并发


def now_cn():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def fetch_one(r):
    url = r.get("url") or ""
    domain = r.get("source_domain") or ""
    out = {
        "url": url,
        "title": r.get("title", ""),
        "published_at": (r.get("published_at") or "")[:10],
        "source_type": r.get("source_type", ""),
        "source_name": r.get("source_name", ""),
        "domain": domain,
        "keyword": r.get("keyword", ""),
        "text": "",
        "text_len": 0,
        "status": "pending",
        "fetched_at": now_cn(),
    }
    if not url:
        out["status"] = "no_url"
        return out

    sem = DOMAIN_SEM[domain]
    with sem:
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=30)
                if resp.status_code == 200:
                    txt = trafilatura.extract(resp.text, include_comments=False,
                                              include_tables=False, favor_recall=True) or ""
                    out["text"] = txt
                    out["text_len"] = len(txt)
                    out["status"] = "ok" if len(txt) >= 80 else ("short" if txt else "empty")
                    return out
                out["status"] = f"http_{resp.status_code}"
                if resp.status_code in (403, 404, 410):
                    return out
            except Exception as e:
                out["status"] = f"err_{type(e).__name__}"
            time.sleep(1.5 * (attempt + 1) + random.uniform(0, 1))
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    rows = []
    with open(os.path.join(DATA, "google_news_2022-2026.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("source_type") in TARGET_TYPES:
                rows.append(r)

    done = set()
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if d.get("status") in ("ok", "short"):
                        done.add(d["url"])
                except Exception:
                    pass
    todo = [r for r in rows if r.get("url") and r["url"] not in done]
    # 优先抓新闻/电视，再生活媒体
    order = {"news": 0, "tv": 1, "aggregator": 2, "intl_media": 3, "lifestyle": 4}
    todo.sort(key=lambda r: (order.get(r.get("source_type"), 9), r.get("published_at", "")))
    if args.limit:
        todo = todo[:args.limit]
    print(f"目标 {len(rows)} 条，已完成 {len(done)} 条，本轮待抓 {len(todo)} 条", flush=True)

    stat = defaultdict(int)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex, open(OUT, "a", encoding="utf-8") as f:
        for i, res in enumerate(ex.map(fetch_one, todo), start=1):
            with LOCK:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
                f.flush()
                stat[res["status"]] += 1
            if i % 50 == 0:
                el = time.time() - t0
                print(f"  {i}/{len(todo)}  用时 {el/60:.1f}min  "
                      f"ok={stat['ok']} short={stat['short']} empty={stat['empty']} "
                      f"err={sum(v for k, v in stat.items() if k.startswith(('err', 'http')))}", flush=True)

    print("\n完成：", dict(stat), flush=True)
    print(f"输出：{OUT}", flush=True)


if __name__ == "__main__":
    main()

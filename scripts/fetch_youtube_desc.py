#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""补采 YouTube 视频简介（正文）与缺失的点赞数。

输入：data/youtube_2022-2026.csv
输出：data/youtube_details.jsonl（video_id / description / like_count / 状态）

用法：python scripts/fetch_youtube_desc.py
"""
from __future__ import annotations

import csv
import json
import os
import re
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
OUT = os.path.join(DATA, "youtube_details.jsonl")
PROXY = os.environ.get("PROXY_URL", "http://192.168.31.238:7897")
PROXIES = {"http": PROXY, "https": PROXY}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "zh-HK,zh;q=0.9",
}
LOCK = threading.Lock()
STAT = defaultdict(int)


def now_cn():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def unescape(s: str) -> str:
    return (s.replace("\\n", "\n").replace("\\\"", "\"").replace("\\/", "/")
             .replace("\\u003c", "<").replace("\\u003e", ">").replace("\\u0026", "&"))


def job(row):
    vid = row["video_id"]
    out = {"video_id": vid, "title": row.get("title", ""), "published_at": row.get("published_at", ""),
           "channel": row.get("channel", ""), "description": "", "desc_len": 0,
           "like_count": None, "status": "", "fetched_at": now_cn()}
    for attempt in range(3):
        try:
            r = requests.get(f"https://www.youtube.com/watch?v={vid}",
                             params={"hl": "zh-HK", "gl": "HK"},
                             headers=HEADERS, proxies=PROXIES, timeout=30)
            if r.status_code != 200:
                out["status"] = f"http_{r.status_code}"
                time.sleep(2 + attempt * 2)
                continue
            t = r.text
            m = re.search(r'"shortDescription":"(.*?)","isCrawlable"', t, re.S)
            if not m:
                m = re.search(r'"attributedDescription":\{"content":"(.*?)","commandRuns"', t, re.S)
            desc = unescape(m.group(1)) if m else ""
            out["description"] = desc
            out["desc_len"] = len(desc)
            ml = re.search(r'"accessibilityText":"(?:與另外 )?([\d,]+) ?(?:人對此影片點讚|人讚好|個讚|likes)', t)
            if ml:
                out["like_count"] = int(re.sub(r"[^\d]", "", ml.group(1)))
            out["status"] = "ok" if desc else "no_desc"
            return out
        except Exception as e:
            out["status"] = f"err_{type(e).__name__}"
            time.sleep(2 + attempt * 2)
    return out


def main():
    rows = list(csv.DictReader(open(os.path.join(DATA, "youtube_2022-2026.csv"), encoding="utf-8-sig")))
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT, encoding="utf-8"):
            try:
                d = json.loads(line)
                if d.get("status") in ("ok", "no_desc"):
                    done.add(d["video_id"])
            except Exception:
                pass
    todo = [r for r in rows if r["video_id"] not in done]
    print(f"共 {len(rows)} 条，已完成 {len(done)}，待抓 {len(todo)}", flush=True)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=6) as ex, open(OUT, "a", encoding="utf-8") as f:
        for i, res in enumerate(ex.map(job, todo), start=1):
            with LOCK:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
                f.flush()
                STAT[res["status"]] += 1
            if i % 40 == 0:
                print(f"  {i}/{len(todo)} {dict(STAT)} {time.time()-t0:.0f}s", flush=True)
    print("完成:", dict(STAT), flush=True)


if __name__ == "__main__":
    main()

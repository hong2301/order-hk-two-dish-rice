# -*- coding: utf-8 -*-
"""修复历史上被 unicode 转义截断的 Google News 解码 URL。

原因：batchexecute 返回的 URL 把 `=` 写成 `\u003d`，旧代码用 split 截断，
导致 watch?v= / ?newsId= / ?id= 一类链接丢失参数部分。
"""
import csv
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
RAW = os.path.join(DATA, "raw")
CSV_PATH = os.path.join(DATA, "google_news_2022-2026.csv")
JSON_PATH = os.path.join(RAW, "google_news_2022-2026.json")
CACHE = os.path.join(RAW, "url_decode_cache.json")
PROXIES = {"http": "http://192.168.31.238:7897", "https": "http://192.168.31.238:7897"}

BS = chr(92)   # 反斜杠
ESC_EQ = BS + "u003d"
ESC_AMP = BS + "u0026"
ESC_SLASH = BS + "u002f"
ESC_QUOTE = BS + '"'


def clean(u: str) -> str:
    for a, b in ((ESC_EQ, "="), (ESC_AMP, "&"), (ESC_SLASH, "/"), (BS + "/", "/")):
        u = u.replace(a, b)
    return u.rstrip(ESC_QUOTE).split(BS + "u")[0]


def sess():
    s = requests.Session()
    s.proxies = PROXIES
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"})
    return s


def decode(s, aid: str) -> str:
    h = s.get("https://news.google.com/rss/articles/" + aid, timeout=25).text
    sg = re.search(r'data-n-a-sg="([^"]+)"', h)
    ts = re.search(r'data-n-a-ts="([^"]+)"', h)
    if not (sg and ts):
        return ""
    payload = ["garturlreq", [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1,
                               None, None, None, None, None, 0, 1], "X", "X", 1, [1, 1, 1],
                               1, 1, None, 0, 0, None, 0], aid, ts.group(1), sg.group(1)]
    freq = json.dumps([[["Fbv4je", json.dumps(payload)]]])
    r = s.post("https://news.google.com/_/DotsSplashUi/data/batchexecute",
               data={"f.req": freq},
               headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
               timeout=25)
    m = re.search(r"(https?://[^" + BS + '"]+)', r.text)
    if not m:
        return ""
    return clean(m.group(1))


def truncated(u: str) -> bool:
    if not u:
        return False
    return bool(re.search(r"[?&][A-Za-z_]+$", u)) or u.endswith("?")


def main():
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8-sig")))
    cols = list(rows[0].keys())
    bad = [r for r in rows if truncated(r["url"])]
    print("待修复", len(bad), flush=True)
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}

    def job(r):
        m = re.search(r"/rss/articles/([A-Za-z0-9_\-]+)", r["google_link"])
        if not m:
            return r, ""
        aid = m.group(1)
        for _ in range(2):
            try:
                u = decode(sess(), aid)
                if u and not truncated(u):
                    return r, u
            except Exception:
                pass
            time.sleep(1.5)
        return r, ""

    fixed = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        for i, (r, u) in enumerate(ex.map(job, bad), start=1):
            if u:
                r["url"] = u
                fixed += 1
                cache[r.get("article_id", "")] = u
            if i % 60 == 0:
                print("  %d/%d 修复 %d" % (i, len(bad), fixed), flush=True)

    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    json.dump(rows, open(JSON_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    left = sum(1 for r in rows if truncated(r["url"]))
    print("修复 %d 条，仍截断 %d 条" % (fixed, left), flush=True)


if __name__ == "__main__":
    main()

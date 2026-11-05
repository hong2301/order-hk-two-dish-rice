#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""采集 Google 新闻中关于香港「兩餸飯」的报道（2022-01 ~ 2026-10）。

流程：
1. Google News RSS 按 关键词 × 年份 查询（RSS 自带 pubDate，可按时间过滤）
2. 对每条 news.google.com 链接解码出媒体原始 URL（batchexecute）
3. 去重、按发布时间过滤，输出 CSV + JSON

用法：python scripts/collect_google_news.py
"""
import csv
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

PROXY = os.environ.get("PROXY_URL", "http://192.168.31.238:7897")
PROXIES = {"http": PROXY, "https": PROXY}
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
RAW = os.path.join(DATA, "raw")
CACHE = os.path.join(RAW, "url_decode_cache.json")

START = datetime(2022, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 11, 1, tzinfo=timezone.utc)  # 不含，即截至 2026-10-31

KEYWORDS = [
    "兩餸飯",
    '"兩餸飯" 香港',
    "三餸飯",
    "兩𩠌飯",
    "兩餸飯 報道",
    "兩餸飯 評論",
    "兩餸飯 結業",
    "兩餸飯 價錢",
    '"two dish rice" hong kong',
    "兩餸飯 社企",
    "雙餸飯",
    "兩餸飯 推薦",
    "兩餸飯 小店",
    # 定向站点检索（电视台 / 报社 / 视频平台）
    "兩餸飯 site:news.tvb.com",
    "兩餸飯 site:tvb.com",
    "兩餸飯 site:rthk.hk",
    "兩餸飯 site:viutv.com",
    "兩餸飯 site:hoy.tv",
    "兩餸飯 site:news.now.com",
    "兩餸飯 site:i-cable.com",
    "兩餸飯 site:youtube.com",
    "兩餸飯 site:facebook.com",
    "兩餸飯 site:instagram.com",
    "兩餸飯 site:mpweekly.com",
    "兩餸飯 site:mingpao.com",
    "兩餸飯 site:scmp.com",
]

YEARS = [(2022, "2022-01-01", "2023-01-01"), (2023, "2023-01-01", "2024-01-01"),
         (2024, "2024-01-01", "2025-01-01"), (2025, "2025-01-01", "2026-01-01"),
         (2026, "2026-01-01", "2026-11-01")]

# 电视台 / 报纸归类
TV_DOMAINS = ["tvb.com", "viutv", "hoy.tv", "rthk", "cabletv", "news.now.com", "nowtv",
              "i-cable", "mytvsuper", "hk01.com/tv"]
LIFESTYLE_DOMAINS = ["weekendhk", "ufood", "ulifestyle", "gotrip", "tkww", "mpweekly", "skypost",
                     "dotdotnews", "orangenews", "thecollectivehk", "theinitium", "szet", "kkday",
                     "foodpanda", "openrice", "trip.com", "hktdc", "businessfocus", "edigest",
                     "ezone", "adaymag", "sundaykiss", "ohpama", "am1470", "hk01.com/食"]
AGGREGATOR_DOMAINS = ["yahoo.com", "msn.com", "line.me", "linetoday", "google.com"]
SOCIAL_DOMAINS = ["facebook.com", "instagram.com", "threads.net", "threads.com", "youtube.com",
                  "youtu.be", "x.com", "twitter.com", "tiktok.com", "reddit.com", "lihkg",
                  "discuss.com.hk", "uwants", "dailymotion", "bilibili"]
NEWS_DOMAINS = ["hk01", "stheadline", "singtao", "mingpao", "wenweipo", "bastillepost", "am730",
                "hket", "orientaldaily", "on.cc", "epaper", "thestandnews", "inmediahk",
                "scmp", "nytimes", "bbc", "cnn", "dw.com", "reuters", "bloomberg"]


def session():
    s = requests.Session()
    s.proxies = PROXIES
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"})
    return s


def fetch_rss(s, q, after, before):
    url = ("https://news.google.com/rss/search?q=" + requests.utils.quote(f"{q} after:{after} before:{before}")
           + "&hl=zh-HK&gl=HK&ceid=HK:zh-Hant")
    for attempt in range(3):
        try:
            r = s.get(url, timeout=30)
            if r.status_code == 200:
                return r.text
        except Exception as e:
            print(f"  ! rss retry {attempt}: {e}", file=sys.stderr)
        time.sleep(2 + attempt * 3)
    return ""


def parse_items(xml, kw):
    out = []
    for it in re.findall(r"<item>(.*?)</item>", xml, re.S):
        def g(tag):
            m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", it, re.S)
            if not m:
                return ""
            v = m.group(1)
            v = re.sub(r"^<!\[CDATA\[|\]\]>$", "", v)
            return (v.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                     .replace("&#39;", "'").replace("&quot;", '"').replace("&nbsp;", " ").strip())
        link = g("link")
        m = re.search(r"/rss/articles/([A-Za-z0-9_\-]+)", link)
        pub = g("pubDate")
        try:
            pub_dt = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
        except Exception:
            pub_dt = None
        src = re.search(r'<source url="([^"]*)"[^>]*>(.*?)</source>', it, re.S)
        out.append({
            "title": g("title"),
            "google_link": link,
            "article_id": m.group(1) if m else "",
            "pub_raw": pub,
            "published_at": pub_dt.isoformat() if pub_dt else "",
            "source_name": (src.group(2).strip() if src else ""),
            "source_url": (src.group(1) if src else ""),
            "keyword": kw,
        })
    return out


def decode_url(s, aid, cache):
    if not aid:
        return ""
    if aid in cache:
        return cache[aid]
    for attempt in range(2):
        try:
            h = s.get(f"https://news.google.com/rss/articles/{aid}", timeout=25).text
            sg = re.search(r'data-n-a-sg="([^"]+)"', h)
            ts = re.search(r'data-n-a-ts="([^"]+)"', h)
            if sg and ts:
                payload = ["garturlreq", [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1,
                                           None, None, None, None, None, 0, 1], "X", "X", 1, [1, 1, 1],
                                           1, 1, None, 0, 0, None, 0], aid, ts.group(1), sg.group(1)]
                freq = json.dumps([[["Fbv4je", json.dumps(payload)]]])
                r2 = s.post("https://news.google.com/_/DotsSplashUi/data/batchexecute",
                            data={"f.req": freq},
                            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
                            timeout=25)
                m = re.search(r'(https?://[^\\"]+)', r2.text)
                if m:
                    cache[aid] = m.group(1).split("\\u003d")[0]
                    return cache[aid]
            break
        except Exception:
            time.sleep(1 + attempt * 2)
    cache[aid] = ""
    return ""


def classify(src_name, real_url):
    from urllib.parse import urlparse
    dom = urlparse(real_url or "").netloc.lower().replace("www.", "")
    blob = (src_name + " " + dom).lower()
    if any(k in blob for k in ["youtube", "youtu.be", "bilibili", "dailymotion"]):
        return "youtube"
    if any(k in blob for k in TV_DOMAINS):
        return "tv"
    if any(k in blob for k in ["facebook.com", "fb.com"]):
        return "facebook"
    if any(k in blob for k in ["instagram.com"]):
        return "instagram"
    if any(k in blob for k in ["threads.net", "threads.com"]):
        return "threads"
    if any(k in blob for k in AGGREGATOR_DOMAINS):
        return "aggregator"
    if any(k in blob for k in ["bbc", "cnn.com", "dw.com", "reuters", "bloomberg", "nytimes", "scmp",
                               "aljazeera", "theguardian", "nikkei", "ft.com", "asahi"]):
        return "intl_media"
    if any(k in blob for k in NEWS_DOMAINS):
        return "news"
    if any(k in blob for k in LIFESTYLE_DOMAINS):
        return "lifestyle"
    if any(k in blob for k in SOCIAL_DOMAINS):
        return "social_other"
    return "other"


def main():
    os.makedirs(RAW, exist_ok=True)
    s = session()
    raw_items = []
    for kw in KEYWORDS:
        for year, after, before in YEARS:
            xml = fetch_rss(s, kw, after, before)
            items = parse_items(xml, kw)
            print(f"[rss] {kw} {year}: {len(items)}")
            raw_items.extend(items)
            time.sleep(1.2)

    # 去重（article_id 优先，其次标题+来源）
    seen, items = set(), []
    for it in raw_items:
        key = it["article_id"] or (it["title"][:60] + it["source_name"])
        if key in seen:
            continue
        seen.add(key)
        items.append(it)
    print(f"[dedup] {len(raw_items)} -> {len(items)}")

    # 时间过滤
    items = [i for i in items if i["published_at"] and
             START <= datetime.fromisoformat(i["published_at"]) < END]
    print(f"[time] {len(items)} in 2022-01 ~ 2026-10")

    cache = {}
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            cache = json.load(f)

    def job(it):
        return decode_url(session(), it["article_id"], cache)

    print("[decode] resolving real URLs ...")
    with ThreadPoolExecutor(max_workers=8) as ex:
        urls = list(ex.map(job, items))

    for it, u in zip(items, urls):
        it["url"] = u
        from urllib.parse import urlparse
        it["url"] = u
        it["source_domain"] = urlparse(u or it["source_url"] or "").netloc.lower().replace("www.", "")
        it["source_type"] = classify(it["source_name"], u or it["source_url"])

    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)

    items.sort(key=lambda x: x["published_at"])
    out_csv = os.path.join(DATA, "google_news_2022-2026.csv")
    cols = ["published_at", "source_type", "source_name", "source_domain", "title", "url",
            "google_link", "source_url", "keyword"]
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(items)
    with open(os.path.join(RAW, "google_news_2022-2026.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)

    from collections import Counter
    print(f"[saved] {len(items)} rows -> {out_csv}")
    print("[by type]", dict(Counter(i["source_type"] for i in items)))
    print("[by year]", dict(sorted(Counter(i["published_at"][:4] for i in items).items())))
    print("[no url]", sum(1 for i in items if not i["url"]))


if __name__ == "__main__":
    main()

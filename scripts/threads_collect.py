#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Threads 关键词搜索采集器（帖子）。

原理与 IG 版一致：
1. 用端口 9225 上已登录的浏览器打开 threads.com/search?q=关键词，抓首屏
   `BarcelonaSearchResultsRefetchableQuery` 的完整表单与请求头
2. requests 复放，用 page_info.end_cursor 翻页（after 参数）
3. 时间窗口过滤 2022-01-01 ~ 2026-10-31（UTC+8）

用法：
  python scripts/threads_collect.py --port 9225 --pages 40
  python scripts/threads_collect.py --keywords "兩餸飯" --pages 3      # 小样
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
import urllib.parse as up

import requests
from DrissionPage import Chromium

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data", "threads")
TMP = os.path.join(BASE, ".tmp")
PROXY = os.environ.get("PROXY_URL", "http://192.168.31.238:7897")
PROXIES = {"http": PROXY, "https": PROXY}

DOC_SEARCH = "40358208533770195"
FN_SEARCH = "BarcelonaSearchResultsRefetchableQuery"

WIN_START = 1640966400   # 2022-01-01 00:00 +08
WIN_END = 1793462399     # 2026-10-31 23:59 +08

KEYWORDS = [
    "兩餸飯", "两餸饭", "三餸飯", "雙餸飯", "兩餸飯關注組", "兩餸飯 香港",
    "兩餸飯 平價", "兩餸飯 抵食", "兩餸飯 深水埗", "兩餸飯 觀塘", "兩餸飯 旺角",
    "兩餸飯 荃灣", "兩餸飯 沙田", "兩餸飯 屯門", "兩餸飯 天水圍", "兩餸飯 灣仔",
    "社企兩餸飯", "兩餸飯 社企", "窮人恩物 兩餸飯", "兩餸飯 結業",
    "two dish rice", "this this rice",
]

RELEVANT = ["餸飯", "餸饭", "𩠌飯", "𩠌饭", "dish rice", "this this rice"]


def now_cn():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def extract_posts(sr: dict) -> list:
    out = []
    for e in sr.get("edges") or []:
        th = (e.get("node") or {}).get("thread") or {}
        for item in th.get("thread_items") or []:
            p = item.get("post")
            if isinstance(p, dict) and p.get("code"):
                out.append(p)
    return out


def slim(p: dict, query: str) -> dict:
    u = p.get("user") or {}
    tp = p.get("text_post_app_info") or {}
    cap = (p.get("caption") or {}).get("text") or ""
    imgs = [c.get("url") for c in ((p.get("image_versions2") or {}).get("candidates") or [])[:2] if c.get("url")]
    vids = [c.get("url") for c in ((p.get("video_versions") or [])[:1]) if c.get("url")]
    place = p.get("meta_place") or p.get("metaPlace") or {}
    return {
        "platform": "threads",
        "collect_channel": "keyword_search",
        "query": query,
        "code": p.get("code"),
        "pk": str(p.get("pk") or ""),
        "taken_at": p.get("taken_at"),
        "published_at": time.strftime("%Y-%m-%d", time.localtime(p.get("taken_at") or 0)),
        "user_username": u.get("username"),
        "user_fullname": u.get("full_name"),
        "user_pk": str(u.get("pk") or u.get("id") or ""),
        "is_verified": u.get("is_verified"),
        "text": cap,
        "hashtags": ",".join(sorted(set(re.findall(r"#([0-9A-Za-z_\u4e00-\u9fff]+)", cap)))),
        "like_count": p.get("like_count"),
        "reply_count": tp.get("direct_reply_count"),
        "repost_count": tp.get("repost_count"),
        "quote_count": tp.get("quote_count"),
        "reshare_count": tp.get("reshare_count"),
        "is_reply": tp.get("is_reply"),
        "media_type": p.get("media_type"),
        "image_urls": " | ".join(imgs),
        "video_url": vids[0] if vids else "",
        "location_name": place.get("name") if isinstance(place, dict) else None,
        "url": f"https://www.threads.com/@{u.get('username')}/post/{p.get('code')}",
        "collected_at": now_cn(),
    }


def grab_template(port: int, query: str, recent: int = 0):
    """打开搜索页，抓首屏请求的表单 + 头 + 已渲染的帖子"""
    br = Chromium(port)
    tab = br.latest_tab
    url = f"https://www.threads.com/search?q={up.quote(query)}&serp_type=default"
    if recent:
        url += "&filter=recent"
    for attempt in range(3):
        try:
            tab.listen.start(targets="graphql")
            tab.get(url)
            time.sleep(10)
            for _ in range(60):
                try:
                    p = next(tab.listen.steps(count=1, timeout=2))
                except Exception:
                    break
                if not p:
                    break
                try:
                    pd = p.request.postData
                except Exception:
                    continue
                if not isinstance(pd, str):
                    continue
                q = up.parse_qs(pd)
                if FN_SEARCH not in q.get("fb_api_req_friendly_name", [""])[0]:
                    continue
                tmpl = {k: v[0] for k, v in q.items()}
                hdrs = dict(p.request.headers)
                ck = {c["name"]: c["value"] for c in tab.cookies()}
                try:
                    body = p.response.body
                    sr = (body.get("data") or {}).get("searchResults") or {}
                except Exception:
                    sr = {}
                tab.listen.stop()
                return tmpl, hdrs, ck, sr
            tab.listen.stop()
        except Exception as e:
            print(f"    ! tmpl {attempt}: {type(e).__name__}", flush=True)
            try:
                tab.listen.stop()
            except Exception:
                pass
            time.sleep(3)
    return None, None, None, {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9225)
    ap.add_argument("--keywords", default="")
    ap.add_argument("--pages", type=int, default=40, help="每关键词最多翻页数（每页约 10 帖）")
    ap.add_argument("--delay", default="2,3.5")
    ap.add_argument("--recent", type=int, default=0, help="1=按时间排序（近期）")
    ap.add_argument("--out", default=os.path.join(DATA, "posts.jsonl"))
    args = ap.parse_args()

    os.makedirs(DATA, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    kws = [k.strip() for k in args.keywords.split(",") if k.strip()] or KEYWORDS
    delay = tuple(float(x) for x in args.delay.split(","))

    seen = set()
    if os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as f:
            for line in f:
                try:
                    seen.add(json.loads(line)["pk"])
                except Exception:
                    pass
    print(f"已有 {len(seen)} 帖，关键词 {len(kws)} 个", flush=True)

    total_new = 0
    for q in kws:
        tmpl, hdrs, ck, sr = grab_template(args.port, q, args.recent)
        if not tmpl:
            print(f"[{q}] 模板抓取失败，跳过", flush=True)
            continue
        sess = requests.Session()
        for k, v in ck.items():
            sess.cookies.set(k, v, domain=".threads.com")
        sess.headers.update({k: v for k, v in hdrs.items() if k.lower().startswith("x-")})
        sess.headers["content-type"] = "application/x-www-form-urlencoded"
        sess.proxies = PROXIES

        posts = extract_posts(sr)
        rows = []
        for p in posts:
            pk = str(p.get("pk") or "")
            ts = p.get("taken_at") or 0
            blob = ((p.get("caption") or {}).get("text") or "").lower()
            if pk in seen or not (WIN_START <= ts <= WIN_END):
                continue
            if not any(k in blob for k in RELEVANT):
                continue
            seen.add(pk)
            rows.append(slim(p, q))
        if rows:
            with open(args.out, "a", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
        total_new += len(rows)
        print(f"[{q}] 首页 {len(posts)} 帖，窗口内相关 {len(rows)}（累计 {total_new}）", flush=True)

        cursor = ((sr.get("page_info") or {}).get("end_cursor")) or ""
        base_vars = json.loads(tmpl["variables"])
        page = 1
        while page < args.pages and cursor:
            page += 1
            v = dict(base_vars)
            v["after"] = cursor
            v["first"] = 10
            d = dict(tmpl)
            d["variables"] = json.dumps(v)
            try:
                r = sess.post("https://www.threads.com/graphql/query", data=d, timeout=60)
                if r.status_code != 200:
                    print(f"  ! [{q}] p{page} HTTP {r.status_code}", flush=True)
                    break
                j = r.json()
                sr2 = (j.get("data") or {}).get("searchResults") or {}
                posts = extract_posts(sr2)
                rows = []
                for p in posts:
                    pk = str(p.get("pk") or "")
                    ts = p.get("taken_at") or 0
                    blob = ((p.get("caption") or {}).get("text") or "").lower()
                    if pk in seen or not (WIN_START <= ts <= WIN_END):
                        continue
                    if not any(k in blob for k in RELEVANT):
                        continue
                    seen.add(pk)
                    rows.append(slim(p, q))
                if rows:
                    with open(args.out, "a", encoding="utf-8") as f:
                        for x in rows:
                            f.write(json.dumps(x, ensure_ascii=False) + "\n")
                total_new += len(rows)
                cursor = ((sr2.get("page_info") or {}).get("end_cursor")) or ""
                has_next = (sr2.get("page_info") or {}).get("has_next_page")
                print(f"  [{q}] p{page}: {len(posts)} 帖 +{len(rows)}（累计 {total_new}）", flush=True)
                if not has_next or not posts:
                    break
            except Exception as e:
                print(f"  ! [{q}] p{page} {type(e).__name__}: {str(e)[:70]}", flush=True)
                break
            time.sleep(random.uniform(*delay))

    print(f"\n完成：新增 {total_new} 条 → {args.out}", flush=True)


if __name__ == "__main__":
    main()

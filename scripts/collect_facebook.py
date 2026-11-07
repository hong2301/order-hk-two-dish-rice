#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""采集 Facebook 上关于「兩餸飯」的帖子（需求 1 · Facebook 部分）。

做法：用已登录浏览器（端口 9227）打开 facebook 帖子搜索页，滚动加载，
从 /api/graphql/ 的 `data.serpResponse` 响应里解析帖子（正文、作者、群组、时间、互动）。

温和节奏：每次滚动间隔 6~9 秒，关键词之间 10~20 秒；总量默认 500 条。

用法：
  python scripts/collect_facebook.py --max-posts 500
  python scripts/collect_facebook.py --max-posts 12 --keywords "兩餸飯"   # 小样
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time
import urllib.parse as up

from DrissionPage import Chromium

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data", "facebook")
NL = "\n"

KEYWORDS = [
    "兩餸飯", "两餸饭", "三餸飯", "雙餸飯", "兩餸飯 香港",
    "香港兩餸飯關注組", "兩餸飯 平價", "兩餸飯 深水埗", "兩餸飯 觀塘",
    "兩餸飯 沙田", "兩餸飯 荃灣", "two dish rice",
]
RELEVANT = ["餸飯", "餸饭", "𩠌飯", "dish rice", "this this rice"]


def now_cn():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def dig(o, *names, default=None):
    """在嵌套结构里按 key 名找第一个非空值"""
    if isinstance(o, dict):
        for n in names:
            v = o.get(n)
            if v not in (None, "", [], {}):
                return v
        for v in o.values():
            r = dig(v, *names, default=None)
            if r not in (None, "", [], {}):
                return r
    elif isinstance(o, list):
        for v in o[:6]:
            r = dig(v, *names, default=None)
            if r not in (None, "", [], {}):
                return r
    return default


def parse_story(st, query):
    cs = st.get("comet_sections") or {}
    content_story = (cs.get("content") or {}).get("story") or {}
    ctx_story = (cs.get("context_layout") or {}).get("story") or {}
    msg = (content_story.get("message") or {}).get("text") or \
          (ctx_story.get("message") or {}).get("text") or ""
    if not msg:
        return None
    actors = content_story.get("actors") or ctx_story.get("actors") or []
    author, author_url = "", ""
    if actors:
        author = actors[0].get("name") or ""
        author_url = actors[0].get("url") or ""
    group = ""
    tg = content_story.get("target_group") or {}
    if isinstance(tg, dict):
        group = tg.get("name") or ""
    if not group:
        ag = dig(st.get("feedback") or {}, "associated_group", default={}) or {}
        if isinstance(ag, dict):
            group = ag.get("name") or ""
    url = content_story.get("wwwURL") or st.get("wwwURL") or ""
    pid = str(st.get("post_id") or "")
    if not url and pid:
        url = "https://www.facebook.com/" + pid
    fbc = cs.get("feedback") or {}
    rc = dig(fbc, "reaction_count", "count")
    if isinstance(rc, dict):
        rc = rc.get("count")
    cc = dig(fbc, "comment_count", "total_count")
    if isinstance(cc, dict):
        cc = cc.get("total_count") or cc.get("count")
    sc = dig(fbc, "share_count", "count")
    if isinstance(sc, dict):
        sc = sc.get("count")
    if not group:
        u = (content_story.get("wwwURL") or st.get("wwwURL") or "")
        if "/groups/" in u:
            group = u.split("/groups/")[1].split("/")[0]
    return {
        "platform": "facebook",
        "collect_channel": "search",
        "query": query,
        "post_id": pid,
        "url": url,
        "author": author,
        "author_url": author_url,
        "group": group,
        "text": msg,
        "published_at": time.strftime("%Y-%m-%d", time.localtime(st.get("creation_time") or 0)),
        "created_ts": st.get("creation_time"),
        "reaction_count": rc,
        "comment_count": cc,
        "share_count": sc,
        "collected_at": now_cn(),
    }


def drain(tab, query, rows, seen):
    got = 0
    while True:
        try:
            p = next(tab.listen.steps(count=1, timeout=1))
        except Exception:
            break
        if not p:
            break
        if "graphql" not in str(getattr(p, "url", "")):
            continue
        try:
            b = p.response.body
        except Exception:
            continue
        if not isinstance(b, dict):
            continue
        sr = (b.get("data") or {}).get("serpResponse")
        if not isinstance(sr, dict):
            continue
        for e in ((sr.get("results") or {}).get("edges") or []):
            st = dig(e, "story") or {}
            if not isinstance(st, dict) or not st.get("post_id"):
                continue
            pid = str(st["post_id"])
            if pid in seen:
                continue
            row = parse_story(st, query)
            if not row:
                continue
            if not any(k in (row["text"] or "").lower() for k in RELEVANT):
                continue
            seen.add(pid)
            rows.append(row)
            got += 1
    return got


def append_rows(path, rows):
    if not rows:
        return
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + NL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9227)
    ap.add_argument("--max-posts", type=int, default=500)
    ap.add_argument("--keywords", default="")
    ap.add_argument("--scroll-wait", default="6,9")
    ap.add_argument("--kw-wait", default="10,20")
    ap.add_argument("--max-scrolls", type=int, default=60)
    ap.add_argument("--out", default=os.path.join(DATA, "posts.jsonl"))
    args = ap.parse_args()

    os.makedirs(DATA, exist_ok=True)
    kws = [k.strip() for k in args.keywords.split(",") if k.strip()] or KEYWORDS
    sw = tuple(float(x) for x in args.scroll_wait.split(","))
    kw_wait = tuple(float(x) for x in args.kw_wait.split(","))

    seen = set()
    if os.path.exists(args.out):
        for line in open(args.out, encoding="utf-8"):
            try:
                seen.add(json.loads(line)["post_id"])
            except Exception:
                pass
    print("已有 %d 帖，目标 %d 条，关键词 %d 个" % (len(seen), args.max_posts, len(kws)), flush=True)

    br = Chromium(args.port)
    tab = br.latest_tab
    tab.get("https://www.facebook.com/")
    time.sleep(5)

    total = 0
    for q in kws:
        if total >= args.max_posts:
            break
        tab.listen.start(targets="graphql")
        tab.get("https://www.facebook.com/search/posts/?q=" + up.quote(q))
        time.sleep(random.uniform(9, 12))
        rows = []
        n = drain(tab, q, rows, seen)
        append_rows(args.out, rows)
        total += n
        print("[%s] 首屏 +%d（累计 %d）" % (q, n, total), flush=True)

        no_new = 0
        for i in range(args.max_scrolls):
            if total >= args.max_posts:
                break
            tab.scroll.to_bottom()
            time.sleep(random.uniform(*sw))
            rows = []
            n = drain(tab, q, rows, seen)
            append_rows(args.out, rows)
            total += n
            print("  [%s] 滚动 %d: +%d（累计 %d）" % (q, i + 1, n, total), flush=True)
            no_new = 0 if n else no_new + 1
            if no_new >= 4:
                print("  [%s] 连续 %d 次无新增，换词" % (q, no_new), flush=True)
                break
        tab.listen.stop()
        time.sleep(random.uniform(*kw_wait))

    print("\n完成：新增 %d 条 → %s" % (total, args.out), flush=True)


if __name__ == "__main__":
    main()

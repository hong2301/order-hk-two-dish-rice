#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""采集 Facebook 帖子的一页评论（需求 1 · Facebook 部分）。

配合 collect_facebook.py：逐帖打开 permalink，等评论加载（只取第一页），
从 /api/graphql/ 响应里解析评论（作者、正文、时间、点赞）。

温和节奏：每帖之间 6~10 秒。

用法：
  python scripts/collect_facebook_comments.py --limit 50
  python scripts/collect_facebook_comments.py            # 全量（断点续跑）
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time

from DrissionPage import Chromium

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data", "facebook")
TMP = os.path.join(BASE, ".tmp")
NL = "\n"


def now_cn():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def walk_comments(o, out, post):
    """递归收集评论对象（Comet 的评论节点带 body.text + created_time）"""
    if isinstance(o, dict):
        body = o.get("body")
        if isinstance(body, dict) and isinstance(body.get("text"), str) and o.get("created_time"):
            author = ""
            a = o.get("author")
            if isinstance(a, dict):
                author = a.get("name") or ""
            if not author:
                au = o.get("author_info") or {}
                author = (au.get("name") or "") if isinstance(au, dict) else ""
            text = body["text"]
            if text:
                out.append({
                    "platform": "facebook",
                    "post_id": post["post_id"],
                    "post_url": post["url"],
                    "post_published_at": post.get("published_at", ""),
                    "comment_id": str(o.get("id") or o.get("legacy_fbid") or ""),
                    "parent_id": str(o.get("parent_comment_id") or ""),
                    "level": 1 if not o.get("parent_comment_id") else 2,
                    "author": author,
                    "text": text,
                    "published_at": time.strftime("%Y-%m-%d",
                                                  time.localtime(o.get("created_time") or 0)),
                    "created_ts": o.get("created_time"),
                    "like_count": None,
                    "collected_at": now_cn(),
                })
        for k, v in o.items():
            if k != "body":
                walk_comments(v, out, post)
    elif isinstance(o, list):
        for v in o:
            walk_comments(v, out, post)


def collect(tab, post, out):
    """打开帖子页，收集第一页评论"""
    tab.listen.start(targets="graphql")
    tab.get(post["url"])
    time.sleep(random.uniform(7, 10))
    seen = set()
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
        rows = []
        walk_comments(b, rows, post)
        for r in rows:
            key = r["comment_id"] or (r["author"] + r["text"][:20])
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
            got += 1
    tab.listen.stop()
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9227)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-comments", type=int, default=1)
    ap.add_argument("--delay", default="6,10")
    ap.add_argument("--posts", default=os.path.join(DATA, "posts.jsonl"))
    ap.add_argument("--out", default=os.path.join(DATA, "comments.jsonl"))
    args = ap.parse_args()

    posts = []
    for line in open(args.posts, encoding="utf-8"):
        try:
            p = json.loads(line)
        except Exception:
            continue
        if int(p.get("comment_count") or 0) >= args.min_comments:
            posts.append(p)
    posts.sort(key=lambda p: -int(p.get("comment_count") or 0))

    done = set()
    done_path = os.path.join(TMP, "fb_comments_done.jsonl")
    if os.path.exists(done_path):
        for line in open(done_path, encoding="utf-8"):
            try:
                done.add(json.loads(line)["post_id"])
            except Exception:
                pass
    posts = [p for p in posts if p["post_id"] not in done]
    if args.limit:
        posts = posts[:args.limit]
    print("待采评论帖子 %d 条（已完成 %d）" % (len(posts), len(done)), flush=True)

    br = Chromium(args.port)
    tab = br.latest_tab
    delay = tuple(float(x) for x in args.delay.split(","))
    total = 0
    for i, post in enumerate(posts, start=1):
        rows = []
        try:
            n = collect(tab, post, rows)
        except Exception as e:
            print("[%d/%d] %s 失败 %s" % (i, len(posts), post["post_id"], type(e).__name__), flush=True)
            time.sleep(5)
            continue
        if rows:
            with open(args.out, "a", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + NL)
        with open(done_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"post_id": post["post_id"], "n": len(rows)}) + NL)
        total += len(rows)
        print("[%d/%d] %s 声明 %s → 采到 %d（累计 %d）" %
              (i, len(posts), post["post_id"], post.get("comment_count"), len(rows), total), flush=True)
        time.sleep(random.uniform(*delay))

    print("\n完成：%d 条评论 → %s" % (total, args.out), flush=True)


if __name__ == "__main__":
    main()

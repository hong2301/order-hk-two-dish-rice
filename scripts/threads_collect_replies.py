#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Threads 回复采集器（配合 threads_collect.py 的帖子）。

做法：逐帖打开 /@user/post/{code}，用浏览器自己发出的
`BarcelonaPostPageDirectRepliesRefetchQuery` 响应取回复（不自己复放，避免 token 校验），
可选滚动 1~2 屏补充。

用法：
  python scripts/threads_collect_replies.py --port 9225 --max-pages 2
  python scripts/threads_collect_replies.py --limit 5        # 小样
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time

from DrissionPage import Chromium

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data", "threads")
TMP = os.path.join(BASE, ".tmp")


def now_cn():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _walk_posts(o, out):
    """递归收集所有 post 对象（Threads 的回复嵌在 posts.edges[].node.posts.edges[] 里）"""
    if isinstance(o, dict):
        if "code" in o and isinstance(o.get("user"), dict) and (
                "caption" in o or "text_post_app_info" in o):
            out.append(o)
            return
        for v in o.values():
            _walk_posts(v, out)
    elif isinstance(o, list):
        for v in o:
            _walk_posts(v, out)


def collect_from_packets(tab, post_pk: str, post_code: str, post_date: str, rows: list):
    """把监听队列里的 media 响应解析成回复行"""
    got = 0
    while True:
        try:
            p = next(tab.listen.steps(count=1, timeout=1))
        except Exception:
            break
        if not p:
            break
        try:
            body = p.response.body
        except Exception:
            continue
        if not isinstance(body, dict):
            continue
        data = body.get("data") or {}
        if "media" not in data:
            continue
        posts = []
        _walk_posts(data["media"], posts)
        for rp in posts:
            if not rp.get("code"):
                continue
            if str(rp.get("pk")) == str(post_pk):
                continue
            u = rp.get("user") or {}
            tp = rp.get("text_post_app_info") or {}
            rows.append({
                "platform": "threads",
                "post_pk": str(post_pk),
                "post_code": post_code,
                "post_published_at": post_date,
                "post_url": f"https://www.threads.com/post/{post_code}",
                "reply_pk": str(rp.get("pk") or ""),
                "reply_code": rp.get("code"),
                "parent_pk": str((tp.get("reply_to_author") or {}).get("id") or ""),
                "text": (rp.get("caption") or {}).get("text") or "",
                "created_at": rp.get("taken_at"),
                "published_at": time.strftime("%Y-%m-%d", time.localtime(rp.get("taken_at") or 0)),
                "user_username": u.get("username"),
                "user_pk": str(u.get("pk") or ""),
                "like_count": rp.get("like_count"),
                "reply_count": tp.get("direct_reply_count"),
                "url": f"https://www.threads.com/@{u.get('username')}/post/{rp.get('code')}",
                "collected_at": now_cn(),
            })
            got += 1
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9225)
    ap.add_argument("--max-pages", type=int, default=2, help="每帖滚动几次（每屏约 10 条回复）")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--wait", default="5,8")
    ap.add_argument("--posts", default=os.path.join(DATA, "posts.jsonl"))
    ap.add_argument("--out", default=os.path.join(DATA, "replies.jsonl"))
    args = ap.parse_args()

    os.makedirs(DATA, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)

    posts = []
    with open(args.posts, encoding="utf-8") as f:
        for line in f:
            try:
                p = json.loads(line)
            except Exception:
                continue
            if int(p.get("reply_count") or 0) > 0:
                posts.append(p)
    posts.sort(key=lambda p: -int(p.get("reply_count") or 0))

    done_path = os.path.join(TMP, "threads_replies_done.jsonl")
    done = set()
    if os.path.exists(done_path):
        with open(done_path, encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["post_pk"])
                except Exception:
                    pass
    posts = [p for p in posts if str(p["pk"]) not in done]
    if args.limit:
        posts = posts[:args.limit]
    print(f"待采回复的帖子 {len(posts)} 条（已完成 {len(done)}）", flush=True)

    br = Chromium(args.port)
    tab = br.latest_tab
    tab.get("https://www.threads.com/")
    time.sleep(4)
    tab.listen.start(targets="graphql")

    wait = tuple(float(x) for x in args.wait.split(","))
    total = 0
    for i, p in enumerate(posts, start=1):
        rows = []
        try:
            tab.get(p["url"])
            time.sleep(random.uniform(*wait))
            collect_from_packets(tab, p["pk"], p["code"], p["published_at"], rows)
            for _ in range(max(args.max_pages - 1, 0)):
                tab.scroll.to_bottom()
                time.sleep(random.uniform(2.5, 4.5))
                collect_from_packets(tab, p["pk"], p["code"], p["published_at"], rows)
            # 去重
            uniq = {}
            for r in rows:
                uniq.setdefault(r["reply_pk"], r)
            rows = list(uniq.values())
            if rows:
                with open(args.out, "a", encoding="utf-8") as f:
                    for r in rows:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
            with open(done_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"post_pk": str(p["pk"]), "replies": len(rows)}, ensure_ascii=False) + "\n")
            total += len(rows)
            print(f"[{i}/{len(posts)}] {p['code']} 声明回复 {p['reply_count']} → 采到 {len(rows)}（累计 {total}）", flush=True)
        except Exception as e:
            print(f"[{i}] {p['code']} 失败 {type(e).__name__}: {str(e)[:60]}", flush=True)
        time.sleep(random.uniform(1.5, 3.0))

    tab.listen.stop()
    print(f"\n完成：{total} 条回复 → {args.out}", flush=True)


if __name__ == "__main__":
    main()

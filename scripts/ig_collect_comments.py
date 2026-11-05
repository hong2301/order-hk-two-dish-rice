#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Instagram 评论采集器（配合 ig_collect_keyword.py 的产物）。

对 data/ig/posts.jsonl 里 comment_count > 0 的帖子逐条拉评论（一级 + 内嵌二级回复）。
走浏览器上下文 fetch，复用已登录的 3 个 profile，多端口并行。

用法：
  python scripts/ig_collect_comments.py --ports 9222,9223,9224 --max-pages 2
  python scripts/ig_collect_comments.py --limit 50            # 先拿 50 帖试水
"""
from __future__ import annotations

import argparse
import json
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from DrissionPage import Chromium

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data", "ig")
TMP = os.path.join(BASE, ".tmp")

JS = r"""
async (pk, minId) => {
  const base = '/api/v1/media/' + pk + '/comments/?can_support_threading=true&permalink_enabled=false&order_by=recent';
  const url = minId ? base + '&min_id=' + encodeURIComponent(minId) : base;
  const r = await fetch(url, {headers: {'x-ig-app-id': '936619743392459'}, credentials: 'include'});
  const raw = await r.text();
  let j = null;
  try { j = JSON.parse(raw); } catch (e) { return {status: r.status_code, error: raw.slice(0, 120)}; }
  if (!j) return {status: r.status_code, error: raw.slice(0, 120)};
  const map = (c, level, parent) => ({
    pk: String(c.pk), text: c.text || '', created_at: c.created_at,
    likes: c.comment_like_count || 0, user: (c.user || {}).username || '',
    uid: String((c.user || {}).pk || ''), level: level, parent: parent || '',
    child: c.child_comment_count || 0
  });
  const list = [];
  for (const c of (j.comments || [])) {
    list.push(map(c, 1, ''));
    const kids = c.preview_child_comments || c.child_comments || [];
    for (const cc of kids) list.push(map(cc, 2, String(c.pk)));
  }
  return {status: r.status_code, count: j.comment_count, more: !!j.has_more_comments,
          next: j.next_min_id ? String(j.next_min_id) : '', comments: list};
}
"""


def now_cn():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ports", default="9222,9223,9224")
    ap.add_argument("--max-pages", type=int, default=5, help="每帖最多翻几页评论（每页约 15 条）")
    ap.add_argument("--limit", type=int, default=0, help="最多处理多少帖（0=全部）")
    ap.add_argument("--min-comments", type=int, default=1)
    ap.add_argument("--delay", default="1.2,2.6")
    ap.add_argument("--posts", default=os.path.join(DATA, "posts.jsonl"))
    ap.add_argument("--out", default=os.path.join(DATA, "comments.jsonl"))
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
            if int(p.get("comment_count") or 0) >= args.min_comments:
                posts.append(p)
    posts.sort(key=lambda p: -int(p.get("comment_count") or 0))

    done_path = os.path.join(TMP, "ig_comments_done.jsonl")
    done = set()
    if os.path.exists(done_path):
        with open(done_path, encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["post_pk"])
                except Exception:
                    pass
    posts = [p for p in posts if p["pk"] not in done]
    if args.limit:
        posts = posts[:args.limit]
    print(f"待采评论帖子 {len(posts)} 条（已有 {len(done)} 条完成）", flush=True)

    ports = [int(x) for x in args.ports.split(",") if x.strip()]
    buckets = {p: [] for p in ports}
    for i, p in enumerate(posts):
        buckets[ports[i % len(ports)]].append(p)

    lock = threading.Lock()
    delay = tuple(float(x) for x in args.delay.split(","))
    stat = {"comments": 0, "posts": 0, "err": 0}

    def worker(port, items):
        br = Chromium(port)
        tab = br.latest_tab
        tab.get("https://www.instagram.com/")
        for _ in range(20):
            if "instagram.com" in (tab.url or ""):
                break
            time.sleep(1)
        time.sleep(4)
        for it in items:
            rows, ok = [], False
            min_id = ""
            for page in range(args.max_pages):
                res = None
                for attempt in range(3):
                    try:
                        if "instagram.com" not in (tab.url or ""):
                            tab.get("https://www.instagram.com/")
                            time.sleep(4)
                        res = tab.run_js(JS, str(it["pk"]), min_id)
                    except Exception as e:
                        res = None
                        print(f"  ! {it['code']} {type(e).__name__}: {str(e)[:60]}", flush=True)
                    if res:
                        break
                    time.sleep(2 + attempt * 2)
                if not res or "comments" not in res:
                    stat["err"] += 1
                    try:
                        dbg = f"url={tab.url[:60]} ready={tab.run_js('document.readyState', as_expr=True)}"
                    except Exception as e:
                        dbg = f"dbg_fail={type(e).__name__}"
                    print(f"  ! {it['code']} res={res} {dbg}", flush=True)
                    break
                for c in res.get("comments") or []:
                    ca = c.get("created_at") or 0
                    rows.append({
                        "platform": "instagram",
                        "post_pk": it["pk"],
                        "post_code": it["code"],
                        "post_published_at": it["published_at"],
                        "post_url": it["url"],
                        "comment_pk": c["pk"],
                        "parent_pk": c["parent"],
                        "level": c["level"],
                        "text": c["text"],
                        "created_at": ca,
                        "published_at": time.strftime("%Y-%m-%d", time.localtime(ca)) if ca else "",
                        "user_username": c["user"],
                        "user_pk": c["uid"],
                        "like_count": c["likes"],
                        "child_count": c["child"],
                        "collected_at": now_cn(),
                    })
                ok = True
                min_id = res.get("next") or ""
                if not min_id or not (res.get("comments") or []):
                    break
                time.sleep(random.uniform(*delay))
            with lock:
                if rows:
                    with open(args.out, "a", encoding="utf-8") as f:
                        for r in rows:
                            f.write(json.dumps(r, ensure_ascii=False) + "\n")
                if ok:
                    with open(done_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"post_pk": it["pk"], "comments": len(rows)}, ensure_ascii=False) + "\n")
                    stat["posts"] += 1
                stat["comments"] += len(rows)
                if stat["posts"] % 20 == 0:
                    print(f"  进度：{stat['posts']} 帖 / {stat['comments']} 条评论 / {stat['err']} 错误", flush=True)
            time.sleep(random.uniform(*delay))

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=len(ports)) as ex:
        for p in ports:
            ex.submit(worker, p, buckets[p])

    print(f"\n完成：{stat['posts']} 帖，{stat['comments']} 条评论，{stat['err']} 错误，"
          f"用时 {(time.time()-t0)/60:.1f} 分钟", flush=True)
    print(f"输出：{args.out}", flush=True)


if __name__ == "__main__":
    main()

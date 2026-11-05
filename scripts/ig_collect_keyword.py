#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Instagram 关键词搜索采集器（帖子）。

原理：
1. 用已登录的浏览器（端口 9222/9223/9224）打开关键词搜索页，抓首屏 GraphQL 请求的
   完整表单与请求头作为模板（lsd / fb_dtsg / X-FB-Entry-Nonce 等一次性 token）
2. 用 requests 复放首屏请求（PolarisKeywordSearchExplorePageRelayQuery）
3. 用 page_info.end_cursor 翻页（PolarisKeywordSearchExplorePageRelayPaginationQuery）
4. 只保留 taken_at 落在 2022-01-01 ~ 2026-10-31（UTC+8）的帖子

用法：
  python scripts/ig_collect_keyword.py --ports 9222,9223,9224 --pages 30
  python scripts/ig_collect_keyword.py --keywords "#兩餸飯,兩餸飯" --pages 3   # 小样测试
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import threading
import time
import urllib.parse as up
import uuid

import requests
from DrissionPage import Chromium

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data", "ig")
TMP = os.path.join(BASE, ".tmp")
PROXY = os.environ.get("PROXY_URL", "http://192.168.31.238:7897")
PROXIES = {"http": PROXY, "https": PROXY}

DOC_FIRST = "37324993597144881"
DOC_PAGE = "28656899673911396"
NAME_FIRST = "PolarisKeywordSearchExplorePageRelayQuery"
NAME_PAGE = "PolarisKeywordSearchExplorePageRelayPaginationQuery"

# 北京时间 2022-01-01 00:00:00 ~ 2026-10-31 23:59:59
WIN_START = 1640966400
WIN_END = 1793462399

KEYWORDS = [
    "#兩餸飯", "#三餸飯", "#雙餸飯", "#兩餸飯關注組", "#香港兩餸飯", "#兩餸飯放題",
    "#兩餸飯推介", "#兩餸飯店", "#兩餸飯經濟", "#平價兩餸飯", "#兩餸飯地圖",
    "#twodishrice", "#twodishesrice",
    "兩餸飯", "两餸饭", "兩𩠌飯", "三餸飯", "雙餸飯",
]

# 相关性过滤：正文/标签必须真的提到「兩餸飯」一类说法
RELEVANT = ["餸飯", "餸饭", "𩠌飯", "𩠌饭", "dish rice", "this this rice", "two dishes rice"]

LOCK = threading.Lock()
STOP = threading.Event()


def log(*a):
    with LOCK:
        print(*a, flush=True)


def now_cn() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def extract_medias(node: dict) -> dict:
    """从 top_serp 响应里取出 media，key = pk"""
    out = {}
    for e in node.get("edges") or []:
        for it in ((e.get("node") or {}).get("items") or []):
            m = it.get("media") if isinstance(it.get("media"), dict) else it
            if isinstance(m, dict) and m.get("code"):
                out[m.get("pk")] = m
    return out


def slim(m: dict, query: str) -> dict:
    imgs = [c.get("url") for c in ((m.get("image_versions2") or {}).get("candidates") or [])[:3] if c.get("url")]
    vids = [c.get("url") for c in ((m.get("video_versions") or [])[:2]) if c.get("url")]
    cap = (m.get("caption") or {}).get("text") or ""
    user = m.get("user") or {}
    loc = m.get("location") or {}
    coa = [c.get("username") for c in (m.get("coauthor_producers") or []) if c.get("username")]
    return {
        "platform": "instagram",
        "collect_channel": "keyword_search",
        "query": query,
        "code": m.get("code"),
        "pk": m.get("pk"),
        "media_id": m.get("id"),
        "taken_at": m.get("taken_at"),
        "published_at": time.strftime("%Y-%m-%d", time.localtime(m.get("taken_at") or 0)),
        "user_username": user.get("username"),
        "user_fullname": user.get("full_name"),
        "user_pk": user.get("pk"),
        "is_verified": user.get("is_verified"),
        "media_type": m.get("media_type"),
        "product_type": m.get("product_type"),
        "caption": cap,
        "hashtags": ",".join(sorted(set(re.findall(r"#([0-9A-Za-z_\u4e00-\u9fff]+)", cap)))),
        "like_count": m.get("like_count"),
        "comment_count": m.get("comment_count"),
        "view_count": m.get("play_count") or m.get("view_count"),
        "carousel_count": len(m.get("carousel_media") or []) or 1,
        "image_urls": " | ".join(imgs),
        "video_url": vids[0] if vids else "",
        "location_name": loc.get("name"),
        "location_id": str(loc.get("pk") or loc.get("facebook_places_id") or ""),
        "coauthors": ",".join(coa),
        "url": f"https://www.instagram.com/p/{m.get('code')}/",
        "collected_at": now_cn(),
    }


class Worker(threading.Thread):
    def __init__(self, port: int, keywords: list[str], pages: int, seen: set, out_path: str,
                 cursor_path: str, delay: tuple[float, float]):
        super().__init__(daemon=True)
        self.port = port
        self.keywords = keywords
        self.pages = pages
        self.seen = seen
        self.out_path = out_path
        self.cursor_path = cursor_path
        self.delay = delay
        self.n_new = 0
        self.n_page = 0
        self.fails = 0

    # ---------- 会话模板 ----------
    def grab_template(self, query: str):
        br = Chromium(self.port)
        tab = br.latest_tab
        url = "https://www.instagram.com/explore/search/keyword/?q=" + up.quote(query)
        for attempt in range(3):
            try:
                tab.listen.start(targets="graphql")
                tab.get(url)
                time.sleep(8)
                first = None
                for _ in range(40):
                    try:
                        p = next(tab.listen.steps(count=1, timeout=2))
                    except Exception:
                        break
                    if not p:
                        break
                    try:
                        b = p.response.body
                    except Exception:
                        continue
                    if isinstance(b, dict) and "xdt_fbsearch__top_serp_graphql" in (b.get("data") or {}):
                        first = p
                        break
                tab.listen.stop()
                if first:
                    tmpl = {k: v[0] for k, v in up.parse_qs(first.request.postData).items()}
                    hdrs = dict(first.request.headers)
                    ck = {c["name"]: c["value"] for c in tab.cookies()}
                    return tmpl, hdrs, ck, extract_medias(
                        first.response.body["data"]["xdt_fbsearch__top_serp_graphql"])
            except Exception as e:
                log(f"    ! tmpl {self.port} {attempt}: {type(e).__name__}")
                try:
                    tab.listen.stop()
                except Exception:
                    pass
                time.sleep(3)
        return None, None, None, {}

    def make_session(self, hdrs, ck):
        s = requests.Session()
        for k, v in ck.items():
            s.cookies.set(k, v, domain=".instagram.com")
        s.headers.update({k: v for k, v in hdrs.items() if k.lower().startswith("x-")})
        s.headers["content-type"] = "application/x-www-form-urlencoded"
        s.proxies = PROXIES
        return s

    # ---------- 主流程 ----------
    def run(self):
        for q in self.keywords:
            if STOP.is_set():
                return
            self.do_keyword(q)

    def do_keyword(self, q):
        state = {}
        if os.path.exists(self.cursor_path):
            try:
                state = json.load(open(self.cursor_path, encoding="utf-8"))
            except Exception:
                state = {}
        start_page = 0
        cursor = ""
        if state.get("query") == q and state.get("port") == self.port:
            cursor = state.get("cursor", "")
            start_page = state.get("page", 0)
            if start_page >= self.pages:
                log(f"[{q}] 已达页数上限，跳过")
                return
        log(f"[{q}] @{self.port} 开始（从第 {start_page} 页）")
        tmpl, hdrs, ck, first_medias = self.grab_template(q)
        if not tmpl:
            log(f"[{q}] 模板抓取失败，跳过")
            return
        sess = self.make_session(hdrs, ck)
        self.flush(first_medias, q, pages_done=0)

        page = 0
        while page < self.pages and not STOP.is_set():
            page += 1
            try:
                v = json.loads(tmpl["variables"])
                d = dict(tmpl)
                if page == 1:
                    d["doc_id"] = DOC_FIRST
                    d["fb_api_req_friendly_name"] = NAME_FIRST
                    sess.headers["X-FB-Friendly-Name"] = NAME_FIRST
                    d["variables"] = json.dumps({
                        "query": v["query"], "search_session_id": v["search_session_id"],
                        "serp_session_id": v["serp_session_id"]})
                else:
                    d["doc_id"] = DOC_PAGE
                    d["fb_api_req_friendly_name"] = NAME_PAGE
                    sess.headers["X-FB-Friendly-Name"] = NAME_PAGE
                    d["variables"] = json.dumps({
                        "after": cursor, "first": 24, "query": v["query"],
                        "search_session_id": v["search_session_id"],
                        "serp_session_id": v["serp_session_id"]})
                r = sess.post("https://www.instagram.com/api/graphql", data=d, timeout=90)
                if r.status_code != 200:
                    self.fails += 1
                    log(f"  ! [{q}] p{page} HTTP {r.status_code}")
                    if self.fails >= 3:
                        # token 可能过期，重抓模板
                        tmpl, hdrs, ck, _ = self.grab_template(q)
                        if tmpl:
                            sess = self.make_session(hdrs, ck)
                            self.fails = 0
                        else:
                            break
                    time.sleep(5)
                    continue
                j = r.json()
                node = (j.get("data") or {}).get("xdt_fbsearch__top_serp_graphql") or {}
                medias = extract_medias(node)
                pi = node.get("page_info") or {}
                self.n_page += 1
                self.flush(medias, q, pages_done=page)
                cursor = pi.get("end_cursor") or ""
                json.dump({"query": q, "port": self.port, "page": page, "cursor": cursor},
                          open(self.cursor_path, "w", encoding="utf-8"))
                if not pi.get("has_next_page") or not cursor:
                    log(f"[{q}] 到底（{page} 页）")
                    break
            except Exception as e:
                self.fails += 1
                log(f"  ! [{q}] p{page} {type(e).__name__}: {str(e)[:70]}")
                if self.fails >= 5:
                    break
                time.sleep(4)
                continue
            time.sleep(random.uniform(*self.delay))
        # 清掉游标（该词已处理完）
        try:
            os.remove(self.cursor_path)
        except Exception:
            pass

    def flush(self, medias: dict, q: str, pages_done: int):
        rows = []
        with LOCK:
            for pk, m in medias.items():
                ts = m.get("taken_at") or 0
                if pk in self.seen:
                    continue
                if not (WIN_START <= ts <= WIN_END):
                    continue
                blob = ((m.get("caption") or {}).get("text") or "").lower()
                if not any(k in blob for k in RELEVANT):
                    continue
                self.seen.add(pk)
                rows.append(slim(m, q))
            if rows:
                with open(self.out_path, "a", encoding="utf-8") as f:
                    for r in rows:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
                self.n_new += len(rows)
        if medias:
            log(f"  [{q}] @{self.port} p{pages_done}: {len(medias)} 帖，窗口内新增 {len(rows)}（累计 {self.n_new}）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ports", default="9222,9223,9224")
    ap.add_argument("--keywords", default="")
    ap.add_argument("--pages", type=int, default=30, help="每个关键词最多翻多少页（每页 24 帖）")
    ap.add_argument("--delay", default="2,4")
    ap.add_argument("--out", default=os.path.join(DATA, "posts.jsonl"))
    args = ap.parse_args()

    os.makedirs(DATA, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    ports = [int(p) for p in args.ports.split(",") if p.strip()]
    kws = [k.strip() for k in args.keywords.split(",") if k.strip()] or KEYWORDS

    seen = set()
    if os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as f:
            for line in f:
                try:
                    seen.add(json.loads(line)["pk"])
                except Exception:
                    pass
    log(f"已有 {len(seen)} 条帖子，关键词 {len(kws)} 个，端口 {ports}")

    # 关键词轮转分配到各端口
    buckets = {p: [] for p in ports}
    for i, k in enumerate(kws):
        buckets[ports[i % len(ports)]].append(k)

    delay = tuple(float(x) for x in args.delay.split(","))
    workers = [Worker(p, buckets[p], args.pages, seen, args.out,
                      os.path.join(TMP, f"ig_cursor_{p}.json"), delay) for p in ports]
    t0 = time.time()
    for w in workers:
        w.start()
    try:
        for w in workers:
            w.join()
    except KeyboardInterrupt:
        STOP.set()
        log("中断，等待线程退出 ...")
        for w in workers:
            w.join(timeout=30)

    total_new = sum(w.n_new for w in workers)
    total_pages = sum(w.n_page for w in workers)
    log(f"\n完成：新增 {total_new} 条，翻页 {total_pages} 次，用时 {(time.time()-t0)/60:.1f} 分钟")
    log(f"输出：{args.out}")


if __name__ == "__main__":
    main()

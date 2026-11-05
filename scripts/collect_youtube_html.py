#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""采集 YouTube 上关于香港「兩餸飯」的视频（2022-01 ~ 2026-10）。

走网页 / innertube 接口（无需登录），比 yt-dlp 的 player 接口更稳：
1. 搜索结果页 HTML → videoRenderer（标题 / 频道 / 相对发布时间 / 播放量 / 时长）
2. innertube search continuation → 每个关键词取 3 页（约 60 条）
3. 对候选视频抓 watch 页，取精确上载日期（dateText）
4. 按 2022-01-01 ~ 2026-10-31 过滤，输出 CSV + JSON

用法：python scripts/collect_youtube_html.py
"""
import csv
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import requests

PROXY = os.environ.get("PROXY_URL", "http://192.168.31.238:7897")
PROXIES = {"http": PROXY, "https": PROXY}
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
RAW = os.path.join(DATA, "raw")
CACHE = os.path.join(BASE, ".tmp", "watch_cache.json")

START, END = date(2022, 1, 1), date(2026, 10, 31)
TODAY = date(2026, 11, 5)
PAGES = 3

QUERIES = [
    "兩餸飯", "兩餸飯 香港", "兩餸飯 探店", "兩餸飯 推介", "兩餸飯 邊間好",
    "兩餸飯 平價", "兩餸飯 開箱", "兩餸飯 評測", "兩餸飯 挑戰", "兩餸飯 vlog",
    "三餸飯", "雙餸飯", "兩餸飯 深水埗", "兩餸飯 觀塘", "兩餸飯 旺角",
    "兩餸飯 40蚊", "兩餸飯 米芝蓮", "兩餸飯 社企", "兩餸飯 窮人恩物",
    "two dish rice hong kong", "this this rice hong kong", "兩餸飯 統計",
    "兩餸飯 結業", "兩餸飯 街訪", "兩餸飯 比較", "兩餸飯 電視",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
}


def session():
    s = requests.Session()
    s.proxies = PROXIES
    s.headers.update(HEADERS)
    return s


def req(s, method, url, **kw):
    for i in range(4):
        try:
            r = s.request(method, url, timeout=40, **kw)
            if r.status_code == 200:
                return r
        except Exception:
            pass
        time.sleep(2 + i * 3)
    return None


def walk(obj, key, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                out.append(v)
            else:
                walk(v, key, out)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, key, out)


def parse_relative(txt):
    """'3 年前' / '2 個月前' -> (估算 date, 精度)"""
    if not txt:
        return None, ""
    t = txt.replace(" ", "")
    m = re.match(r"(\d+)\s*(秒|分鐘|分|小時|時|天|日|星期|週|個月|月|年)前", t)
    if not m:
        return None, ""
    n, unit = int(m.group(1)), m.group(2)
    if unit in ("秒",):
        return TODAY, "second"
    if unit in ("分鐘", "分", "小時", "時"):
        return TODAY, "hour"
    if unit in ("天", "日"):
        return TODAY - timedelta(days=n), "day"
    if unit in ("星期", "週"):
        return TODAY - timedelta(weeks=n), "week"
    if unit in ("個月", "月"):
        return TODAY - timedelta(days=30 * n), "month"
    return TODAY.replace(year=TODAY.year - n), "year"


def num(txt):
    if not txt:
        return None
    d = re.sub(r"[^\d]", "", txt)
    return int(d) if d else None


def parse_duration(txt):
    """'1:02:03' / '14:12' -> 秒"""
    if not txt:
        return None
    parts = txt.split(":")
    try:
        parts = [int(p) for p in parts]
    except Exception:
        return None
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return None


def extract_videos(data):
    out = []
    for v in data:
        try:
            title = "".join(r.get("text", "") for r in v["title"].get("runs", [])) or \
                    v["title"].get("simpleText", "")
            ch = ""
            if v.get("ownerText"):
                ch = "".join(r.get("text", "") for r in v["ownerText"].get("runs", []))
            elif v.get("longBylineText"):
                ch = "".join(r.get("text", "") for r in v["longBylineText"].get("runs", []))
            desc = ""
            if v.get("descriptionSnippet"):
                desc = "".join(r.get("text", "") for r in v["descriptionSnippet"].get("runs", []))
            ptxt = (v.get("publishedTimeText") or {}).get("simpleText", "")
            est, prec = parse_relative(ptxt)
            out.append({
                "video_id": v.get("videoId", ""),
                "title": title,
                "channel": ch,
                "channel_id": (v.get("ownerText") and v.get("ownerText", {}).get("runs", [{}])[0]
                               .get("navigationEndpoint", {}).get("browseEndpoint", {}).get("browseId", "")) or "",
                "url": f"https://www.youtube.com/watch?v={v.get('videoId', '')}",
                "published_text": ptxt,
                "approx_date": est.isoformat() if est else "",
                "date_precision": prec,
                "view_count_text": (v.get("viewCountText") or {}).get("simpleText", ""),
                "duration": (v.get("lengthText") or {}).get("simpleText", ""),
                "desc_snippet": desc[:300],
            })
        except Exception:
            continue
    return out


def search_all(s, q):
    r = req(s, "GET", "https://www.youtube.com/results",
            params={"search_query": q, "hl": "zh-HK", "gl": "HK"})
    if not r:
        return []
    t = r.text
    try:
        key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', t).group(1)
        ver = re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"', t).group(1)
        data = json.loads(re.search(r"var ytInitialData = (\{.*?\});</script>", t).group(1))
    except Exception:
        return []
    raw = []
    walk(data, "videoRenderer", raw)
    items = extract_videos(raw)

    token = None
    m = re.search(r'"continuationCommand":\{"token":"([^"]+)"', t)
    if m:
        token = m.group(1)
    for _ in range(PAGES - 1):
        if not token:
            break
        body = {"context": {"client": {"clientName": "WEB", "clientVersion": ver,
                                       "hl": "zh-HK", "gl": "HK"}},
                "continuation": token}
        r2 = req(s, "POST", f"https://www.youtube.com/youtubei/v1/search?key={key}&prettyPrint=false",
                 json=body)
        if not r2:
            break
        try:
            j = r2.json()
        except Exception:
            break
        raw = []
        walk(j, "videoRenderer", raw)
        items.extend(extract_videos(raw))
        toks = []
        walk(j, "continuationCommand", toks)
        token = toks[-1].get("token") if toks else None
        time.sleep(0.6)
    return items


def watch_date(s, vid, cache):
    if vid in cache:
        return cache[vid]
    r = req(s, "GET", f"https://www.youtube.com/watch?v={vid}", params={"hl": "zh-HK", "gl": "HK"})
    res = {"date": "", "views": None, "likes": None, "duration_sec": None}
    if r:
        t = r.text
        m = re.search(r'"dateText":\{"simpleText":"([^"]+)"', t)
        if m:
            txt = m.group(1)  # 2025年5月18日 / May 18, 2025
            mm = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", txt)
            if mm:
                res["date"] = f"{int(mm.group(1)):04d}-{int(mm.group(2)):02d}-{int(mm.group(3)):02d}"
            else:
                for fmt in ("%b %d, %Y", "%d %b %Y", "%B %d, %Y"):
                    try:
                        res["date"] = datetime.strptime(txt.strip(), fmt).date().isoformat()
                        break
                    except Exception:
                        pass
        mv = re.search(r'"viewCount":\{"simpleText":"([^"]+)"', t) or re.search(r'"viewCount":"(\d+)"', t)
        if mv:
            res["views"] = num(mv.group(1))
        # 点赞：新版页面在 accessibilityText 里（中文「與另外 N 人對此影片點讚」/ 英文 "N likes"）
        ml = (re.search(r'"accessibilityText":"(?:與另外 )?([\d,]+) ?(?:人對此影片點讚|人讚好|個讚|likes|other people)', t)
              or re.search(r'"likeCount":\{"simpleText":"([^"]+)"', t)
              or re.search(r'"likeCount":"(\d+)"', t))
        if ml:
            res["likes"] = num(ml.group(1))
        md = re.search(r'"lengthSeconds":"(\d+)"', t)
        if md:
            res["duration_sec"] = int(md.group(1))
    cache[vid] = res
    return res


def main():
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    s = session()

    cand, seen = [], set()
    for q in QUERIES:
        items = search_all(s, q)
        new = 0
        for it in items:
            vid = it["video_id"]
            if not vid or vid in seen:
                continue
            seen.add(vid)
            it["query"] = q
            cand.append(it)
            new += 1
        print(f"[search] {q}: {len(items)} hits, +{new} (total {len(cand)})")
        time.sleep(1.0)

    # 先用相对时间粗筛：明显早于 2022 的（>=4 年前，且精度为 year）先保留待核
    def maybe_in_range(it):
        if not it["approx_date"]:
            return True
        d = date.fromisoformat(it["approx_date"])
        if it["date_precision"] in ("year", "month"):
            return d >= date(START.year - 1, 1, 1) and d <= date(END.year, 12, 31)
        return START <= d <= END

    todo = [it for it in cand if maybe_in_range(it)]
    print(f"[prefilter] {len(cand)} -> {len(todo)} candidates need exact date")

    cache = {}
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            cache = json.load(f)

    def job(it):
        return watch_date(session(), it["video_id"], cache)

    with ThreadPoolExecutor(max_workers=8) as ex:
        infos = list(ex.map(job, todo))
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)

    rows, seen2 = [], set()
    for it, inf in zip(todo, infos):
        d = inf.get("date") or it["approx_date"]
        if not d:
            continue
        dd = date.fromisoformat(d)
        if not (START <= dd <= END):
            continue
        if it["video_id"] in seen2:
            continue
        seen2.add(it["video_id"])
        it["published_at"] = d
        it["date_source"] = "watch_page" if inf.get("date") else "approx_relative"
        it["view_count"] = inf.get("views") if inf.get("views") is not None else num(it["view_count_text"])
        it["like_count"] = inf.get("likes")
        it["duration_sec"] = inf.get("duration_sec") or parse_duration(it.get("duration", ""))
        rows.append(it)

    rows.sort(key=lambda x: x["published_at"])
    cols = ["published_at", "date_source", "date_precision", "video_id", "title", "channel", "channel_id",
            "url", "duration_sec", "duration", "view_count", "like_count", "published_text",
            "desc_snippet", "query"]
    out = os.path.join(DATA, "youtube_2022-2026.csv")
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(RAW, "youtube_2022-2026.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)

    from collections import Counter
    print(f"[saved] {len(rows)} rows -> {out}")
    print("[by year]", dict(sorted(Counter(r["published_at"][:4] for r in rows).items())))
    print("[date source]", dict(Counter(r["date_source"] for r in rows)))
    print("[top channels]")
    for ch, n in Counter(r["channel"] for r in rows).most_common(20):
        print(f"   {n:3d}  {ch}")


if __name__ == "__main__":
    main()

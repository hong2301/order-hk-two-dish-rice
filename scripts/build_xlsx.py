#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成 3 份交付 Excel + 1 份统计说明。

  1) data/1_社交平台_帖子_兩餸飯_2022-2026.xlsx   Instagram / Threads / Facebook 帖子
  2) data/2_Google与媒体_兩餸飯_2022-2026.xlsx    报社 / 电视台 / 生活媒体 / YouTube
  3) data/3_评论与回复_兩餸飯_2022-2026.xlsx       IG 评论 + Threads 回复（关联到帖子）
  4) data/采集统计.md                              数据量统计

用法：python scripts/build_xlsx.py
"""
import csv
import json
import os
from collections import Counter
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
IG = os.path.join(DATA, "ig")
TH = os.path.join(DATA, "threads")
FB = os.path.join(DATA, "facebook")

OUT1 = os.path.join(DATA, "1_社交平台_帖子_兩餸飯_2022-2026.xlsx")
OUT2 = os.path.join(DATA, "2_Google与媒体_兩餸飯_2022-2026.xlsx")
OUT3 = os.path.join(DATA, "3_评论与回复_兩餸飯_2022-2026.xlsx")
OUTMD = os.path.join(DATA, "采集统计.md")

COLLECTED = "2026-11-07"
PERIOD = "2022-01-01 ~ 2026-10-31"

# 内容表（需求1 / 需求2 共用）
COLS = [
    ("序号", 7, "center"),
    ("平台", 13, "center"),
    ("采集通道", 16, "center"),
    ("来源类型", 13, "center"),
    ("来源名称", 22, "left"),
    ("域名", 20, "left"),
    ("标题", 40, "left"),
    ("正文", 60, "left"),
    ("发布日期", 12, "center"),
    ("采集日期", 12, "center"),
    ("链接", 42, "left"),
    ("播放量", 11, "right"),
    ("点赞数", 10, "right"),
    ("评论数", 9, "right"),
    ("时长(秒)", 9, "right"),
    ("检索关键词", 16, "left"),
    ("标题命中", 9, "center"),
    ("正文字数", 10, "right"),
    ("备注", 30, "left"),
]

# 评论表
COMMENT_COLS = [
    ("序号", 7, "center"),
    ("平台", 11, "center"),
    ("帖子链接", 42, "left"),
    ("帖子 ID", 20, "left"),
    ("帖子作者", 18, "left"),
    ("帖子发布日期", 13, "center"),
    ("帖子正文摘要", 46, "left"),
    ("层级", 7, "center"),
    ("父评论 ID", 18, "left"),
    ("评论者", 18, "left"),
    ("评论内容", 58, "left"),
    ("评论日期", 12, "center"),
    ("点赞数", 9, "right"),
    ("子回复数", 9, "right"),
    ("采集日期", 12, "center"),
]

PLATFORM = {
    "instagram": "Instagram", "facebook": "Facebook", "threads": "Threads", "youtube": "YouTube",
    "tv": "电视台", "news": "报社 / 网媒", "lifestyle": "生活饮食媒体",
    "aggregator": "新闻聚合", "intl_media": "境外媒体",
    "social_other": "其他社交平台", "other": "其他网站",
}
DOMAIN_NAME = {
    "i-cable.com": "有线新闻", "www.i-cable.com": "有线新闻", "tvb.com": "TVB",
    "news.tvb.com": "TVB 新闻", "programme.tvb.com": "TVB 节目", "mytvsuper.com": "myTV SUPER",
    "news.now.com": "Now 新闻", "hoy.tv": "HOY TV", "news.rthk.hk": "香港电台",
    "app2.rthk.hk": "香港电台", "ol.mingpao.com": "明报 OL", "news.mingpao.com": "明报",
    "mingpao.com": "明报", "stheadline.com": "星岛头条", "eastweek.stheadline.com": "东周刊",
    "hk01.com": "香港01", "hket.com": "经济日报", "topick.hket.com": "TOPick",
    "ps.hket.com": "经济日报", "news.hket.com": "经济日报", "wenweipo.com": "文汇报",
    "am730.com.hk": "am730", "bastillepost.com": "巴士的报", "hk.on.cc": "东网",
    "orientaldaily.com": "东方日报", "mpweekly.com": "明周", "weekendhk.com": "新假期",
    "ufood.com.hk": "U Food", "hk.ulifestyle.com.hk": "ULifestyle", "gotrip.hk": "Gotrip",
    "tkww.hk": "Talkfood", "skypost.hk": "晴报", "dotdotnews.com": "点新闻",
    "orangenews.hk": "橙新闻", "scmp.com": "南华早报", "bbc.com": "BBC",
    "hk.news.yahoo.com": "Yahoo 新闻", "youtube.com": "YouTube",
    "instagram.com": "Instagram", "facebook.com": "Facebook", "threads.com": "Threads",
}
MEDIA_TYPE = {1: "单图", 2: "视频", 8: "多图"}
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def load_csv(name):
    with open(os.path.join(DATA, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def fmt_date(s):
    if not s:
        return ""
    s = str(s).strip()
    try:
        return s[:10] if "T" in s else date.fromisoformat(s[:10]).isoformat()
    except Exception:
        return s[:10]


def norm(v):
    if v is None or v == "":
        return ""
    if isinstance(v, dict):
        v = v.get("count") or v.get("total_count")
    try:
        return int(float(v))
    except Exception:
        return ""


def pretty_source(name, domain):
    name = (name or "").strip()
    d = (domain or "").lower().replace("www.", "")
    if not name or name.lower().replace("www.", "") in (d, (domain or "").lower()):
        return DOMAIN_NAME.get((domain or "").lower(), DOMAIN_NAME.get(d, name or d))
    if name in ("YouTube", "Instagram", "Facebook", "Threads"):
        return DOMAIN_NAME.get(d, name)
    return name


def write_sheet(ws, rows, cols):
    for i, (name, width, align) in enumerate(cols, start=1):
        c = ws.cell(row=1, column=i, value=name)
        c.font = Font(bold=True, color="FFFFFF", size=11, name="Microsoft YaHei")
        c.fill = PatternFill("solid", fgColor="1F4E79")
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDER
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.row_dimensions[1].height = 24
    ws.freeze_panes = "A2"
    wrap = {"标题", "正文", "评论内容", "帖子正文摘要"}
    for idx, r in enumerate(rows, start=1):
        vals = [idx] + [r.get(n, "") for n, _, _ in cols[1:]]
        for j, v in enumerate(vals, start=1):
            name, _, align = cols[j - 1]
            c = ws.cell(row=idx + 1, column=j, value=v)
            c.font = Font(size=10, name="Microsoft YaHei")
            c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=name in wrap)
            c.border = BORDER
            if name == "链接" and v:
                c.hyperlink = v
                c.font = Font(size=10, name="Microsoft YaHei", color="0563C1", underline="single")
            if idx % 2 == 0:
                c.fill = PatternFill("solid", fgColor="F2F7FB")
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{len(rows) + 1}"
    return ws


def write_info(ws, lines, dist, dist_title="平台分布"):
    for i, (k, v) in enumerate(lines, start=1):
        ws.cell(row=i, column=1, value=k).font = Font(
            bold=(i == 1), size=14 if i == 1 else 10, name="Microsoft YaHei")
        ws.cell(row=i, column=2, value=v).font = Font(size=10, name="Microsoft YaHei")
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 92
    row = len(lines) + 2
    ws.cell(row=row, column=1, value=dist_title).font = Font(bold=True, size=11, name="Microsoft YaHei")
    for i, (k, v) in enumerate(dist, start=row + 1):
        ws.cell(row=i, column=1, value=k).font = Font(size=10, name="Microsoft YaHei")
        ws.cell(row=i, column=2, value=f"{v} 条").font = Font(size=10, name="Microsoft YaHei")


def write_stats(ws, rows, years=("2022", "2023", "2024", "2025", "2026"), date_key="发布日期"):
    pc = Counter(r["平台"] for r in rows)
    for j, h in enumerate(["平台"] + list(years) + ["合计"], start=1):
        c = ws.cell(row=1, column=j, value=h)
        c.font = Font(bold=True, color="FFFFFF", size=11, name="Microsoft YaHei")
        c.fill = PatternFill("solid", fgColor="1F4E79")
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDER
    ws.column_dimensions["A"].width = 20
    for j in range(2, len(years) + 3):
        ws.column_dimensions[get_column_letter(j)].width = 11
    r_i = 2
    for p, _ in pc.most_common():
        sub = [r for r in rows if r["平台"] == p]
        vals = [p] + [sum(1 for r in sub if r[date_key].startswith(y)) for y in years] + [len(sub)]
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=r_i, column=j, value=v)
            c.font = Font(size=10, name="Microsoft YaHei")
            c.alignment = Alignment(horizontal="center" if j > 1 else "left", vertical="center")
            c.border = BORDER
            if r_i % 2 == 0:
                c.fill = PatternFill("solid", fgColor="F2F7FB")
        r_i += 1
    vals = ["合计"] + [sum(1 for r in rows if r[date_key].startswith(y)) for y in years] + [len(rows)]
    for j, v in enumerate(vals, start=1):
        c = ws.cell(row=r_i, column=j, value=v)
        c.font = Font(bold=True, size=10, name="Microsoft YaHei")
        c.fill = PatternFill("solid", fgColor="DDEBF7")
        c.alignment = Alignment(horizontal="center" if j > 1 else "left", vertical="center")
        c.border = BORDER
    ws.freeze_panes = "A2"
    return pc


WIN_START = "2022-01-01"
WIN_END = "2026-10-31"


def in_window(d):
    return bool(d) and WIN_START <= str(d)[:10] <= WIN_END


def blank(s=""):
    return {"平台": s, "采集通道": "", "来源类型": "", "来源名称": "", "域名": "",
            "标题 / 正文": "", "发布日期": "", "采集日期": "", "链接": "",
            "播放量": "", "点赞数": "", "评论数": "", "时长(秒)": "",
            "检索关键词": "", "标题命中": "", "正文字数": "", "备注": ""}


# ---------------- 1. 社交平台帖子 ----------------

def build_part1():
    posts = load_jsonl(os.path.join(IG, "posts.jsonl"))
    th_posts = load_jsonl(os.path.join(TH, "posts.jsonl"))
    fb_posts = load_jsonl(os.path.join(FB, "posts.jsonl"))

    rows = []
    for p in posts:
        txt = (p.get("caption") or "").strip()
        mt = MEDIA_TYPE.get(p.get("media_type"), "")
        note = mt
        if p.get("carousel_count") and p["carousel_count"] > 1:
            note += f"×{p['carousel_count']}"
        rows.append({
            "平台": "Instagram",
            "采集通道": "IG 标签搜索" if str(p.get("query", "")).startswith("#") else "IG 关键词搜索",
            "来源类型": "IG 贴文", "来源名称": p.get("user_username") or "",
            "域名": "instagram.com", "标题": "", "正文": txt,
            "发布日期": fmt_date(p.get("published_at")), "采集日期": COLLECTED,
            "链接": p.get("url", ""), "播放量": norm(p.get("view_count")),
            "点赞数": norm(p.get("like_count")), "评论数": norm(p.get("comment_count")),
            "时长(秒)": "", "检索关键词": p.get("query", ""), "标题命中": "是",
            "正文字数": len(txt), "备注": note, "_sort": fmt_date(p.get("published_at")),
        })
    for p in th_posts:
        txt = p.get("text") or ""
        note = f"赞{p.get('like_count') or 0}/回复{p.get('reply_count') or 0}/转发{p.get('repost_count') or 0}"
        rows.append({
            "平台": "Threads", "采集通道": "Threads 搜索", "来源类型": "Threads 贴文",
            "来源名称": p.get("user_username") or "", "域名": "threads.com",
            "标题": "", "正文": txt, "发布日期": fmt_date(p.get("published_at")),
            "采集日期": COLLECTED, "链接": p.get("url", ""), "播放量": "",
            "点赞数": norm(p.get("like_count")), "评论数": norm(p.get("reply_count")),
            "时长(秒)": "", "检索关键词": p.get("query", ""), "标题命中": "是",
            "正文字数": len(txt), "备注": note, "_sort": fmt_date(p.get("published_at")),
        })
    for p in fb_posts:
        txt = p.get("text") or ""
        note = f"赞{p.get('reaction_count') or 0}/评{p.get('comment_count') or 0}"
        if p.get("group"):
            note += "｜群组 " + p["group"]
        rows.append({
            "平台": "Facebook", "采集通道": "Facebook 搜索", "来源类型": "Facebook 贴文",
            "来源名称": p.get("author") or "", "域名": "facebook.com",
            "标题": "", "正文": txt, "发布日期": fmt_date(p.get("published_at")),
            "采集日期": COLLECTED, "链接": p.get("url", ""), "播放量": "",
            "点赞数": norm(p.get("reaction_count")), "评论数": norm(p.get("comment_count")),
            "时长(秒)": "", "检索关键词": p.get("query", ""), "标题命中": "是",
            "正文字数": len(txt), "备注": note, "_sort": fmt_date(p.get("published_at")),
        })
    rows = [r for r in rows if in_window(r["_sort"])]
    rows.sort(key=lambda x: (x["_sort"], x["平台"]))

    wb = Workbook()
    ws = wb.active
    ws.title = "说明"
    dist = Counter(r["平台"] for r in rows)
    write_info(ws, [
        ("需求 1 · 社交平台「兩餸飯」帖子", ""),
        ("", ""),
        ("采集时间范围", PERIOD),
        ("抓取日期", COLLECTED),
        ("帖子总数", f"{len(rows)} 条"),
        ("数据来源", "Instagram（标签/关键词搜索）｜ Threads（关键词搜索）｜ Facebook（帖子搜索）"),
        ("说明", "评论与回复见「3_评论与回复」文件"),
    ], dist.most_common())
    write_sheet(wb.create_sheet("全部帖子"), rows, COLS)
    for name, plat in (("Instagram", "Instagram"), ("Threads", "Threads"), ("Facebook", "Facebook")):
        sub = [r for r in rows if r["平台"] == plat]
        if sub:
            write_sheet(wb.create_sheet(name), sub, COLS)
    write_stats(wb.create_sheet("平台统计"), rows)
    wb.save(OUT1)
    return rows


# ---------------- 2. Google 与媒体 ----------------

def build_part2():
    news = load_csv("google_news_2022-2026.csv")
    yt = load_csv("youtube_2022-2026.csv")
    articles = load_jsonl(os.path.join(DATA, "articles.jsonl"))
    ytdesc = load_jsonl(os.path.join(DATA, "youtube_details.jsonl"))

    art_by_url = {}
    for a in articles:
        if a.get("status") == "ok" and a.get("text"):
            art_by_url.setdefault(a["url"], a)
    desc_by_vid = {d["video_id"]: d for d in ytdesc if d.get("description")}
    yt_ids = {r["video_id"] for r in yt}

    rows = []
    for r in news:
        st = r["source_type"]
        if st in ("facebook", "instagram", "threads"):
            continue
        url = r.get("url", "")
        if st == "youtube":
            vid = url.split("v=")[-1].split("&")[0] if "watch?v=" in url else ""
            if vid and vid in yt_ids:
                continue
        remark = "原链接解码失败" if not url else ""
        a = art_by_url.get(url)
        rows.append({
            "平台": PLATFORM.get(st, "其他网站"), "采集通道": "Google News",
            "来源类型": {"news": "报社网媒", "tv": "电视台", "lifestyle": "生活媒体",
                         "aggregator": "新闻聚合", "intl_media": "境外媒体",
                         "youtube": "YouTube视频", "other": "其他网站"}.get(st, st),
            "来源名称": pretty_source(r.get("source_name"), r.get("source_domain")),
            "域名": r.get("source_domain", ""), "标题": r.get("title", ""),
            "正文": ((a or {}).get("text") or "")[:30000],
            "发布日期": fmt_date(r.get("published_at")), "采集日期": COLLECTED,
            "链接": url or r.get("google_link", ""), "播放量": "", "点赞数": "",
            "评论数": "", "时长(秒)": "", "检索关键词": r.get("keyword", ""),
            "标题命中": "是" if r.get("title_hit") == "1" else "否",
            "正文字数": (a or {}).get("text_len", "") or "",
            "备注": remark, "_sort": fmt_date(r.get("published_at")),
        })
    for r in yt:
        rows.append({
            "平台": "YouTube", "采集通道": "YouTube 搜索", "来源类型": "YouTube视频",
            "来源名称": r.get("channel", ""), "域名": "youtube.com",
            "标题": r.get("title", ""), "正文": ((desc_by_vid.get(r.get("video_id")) or {}).get("description") or "")[:30000],
            "发布日期": fmt_date(r.get("published_at")),
            "采集日期": COLLECTED, "链接": r.get("url", ""),
            "播放量": norm(r.get("view_count")), "点赞数": norm(r.get("like_count")),
            "评论数": "", "时长(秒)": norm(r.get("duration_sec")),
            "检索关键词": r.get("query", ""),
            "标题命中": "是" if r.get("title_hit") == "1" else "否",
            "正文字数": (desc_by_vid.get(r.get("video_id")) or {}).get("desc_len", "") or "",
            "备注": "", "_sort": fmt_date(r.get("published_at")),
        })
    rows = [r for r in rows if in_window(r["_sort"])]
    rows.sort(key=lambda x: (x["_sort"], x["平台"]))

    body_n = sum(1 for r in rows if (r.get("正文") or "").strip())
    body_words = sum(len(r.get("正文") or "") for r in rows)

    wb = Workbook()
    ws = wb.active
    ws.title = "说明"
    dist = Counter(r["平台"] for r in rows)
    write_info(ws, [
        ("需求 2 · Google 检索与媒体「兩餸飯」报道、节目与视频", ""),
        ("", ""),
        ("采集时间范围", PERIOD),
        ("抓取日期", COLLECTED),
        ("内容条数", f"{len(rows)} 条"),
        ("正文全文", f"{body_n} 条有正文，合计 {body_words:,} 字（见「正文」列）"),
        ("数据来源", "Google News 索引（报社 / 电视台 / 网媒）｜ YouTube 搜索"),
    ], dist.most_common())
    write_sheet(wb.create_sheet("全部内容"), rows, COLS)
    write_sheet(wb.create_sheet("报刊网媒"),
                [r for r in rows if r["平台"] in ("报社 / 网媒", "生活饮食媒体", "境外媒体",
                                              "其他网站", "新闻聚合")], COLS)
    write_sheet(wb.create_sheet("电视台"), [r for r in rows if r["平台"] == "电视台"], COLS)
    write_sheet(wb.create_sheet("YouTube视频"), [r for r in rows if r["平台"] == "YouTube"
                                            and r["采集通道"] == "YouTube 搜索"], COLS)
    write_stats(wb.create_sheet("平台统计"), rows)
    wb.save(OUT2)
    return rows, body_n, body_words


# ---------------- 3. 评论与回复 ----------------

def build_part3():
    posts = load_jsonl(os.path.join(IG, "posts.jsonl"))
    comments = load_jsonl(os.path.join(IG, "comments.jsonl"))
    th_posts = load_jsonl(os.path.join(TH, "posts.jsonl"))
    th_replies = load_jsonl(os.path.join(TH, "replies.jsonl"))

    ig_map = {str(p["pk"]): p for p in posts}
    th_map = {str(p["pk"]): p for p in th_posts}

    rows = []
    for c in comments:
        p = ig_map.get(str(c.get("post_pk")), {})
        txt = (p.get("caption") or "").strip()
        rows.append({
            "平台": "Instagram", "帖子链接": c.get("post_url", ""),
            "帖子 ID": c.get("post_code", ""), "帖子作者": p.get("user_username", ""),
            "帖子发布日期": fmt_date(c.get("post_published_at")),
            "帖子正文摘要": txt[:80],
            "层级": "一级" if c.get("level") == 1 else "回复",
            "父评论 ID": c.get("parent_pk", ""), "评论者": c.get("user_username", ""),
            "评论内容": c.get("text", ""), "评论日期": fmt_date(c.get("published_at")),
            "点赞数": norm(c.get("like_count")), "子回复数": norm(c.get("child_count")),
            "采集日期": COLLECTED, "_sort": fmt_date(c.get("published_at")),
        })
    for c in th_replies:
        p = th_map.get(str(c.get("post_pk")), {})
        txt = (p.get("text") or "").strip()
        rows.append({
            "平台": "Threads",
            "帖子链接": (f"https://www.threads.com/@{p['user_username']}/post/{c.get('post_code')}"
                     if p.get("user_username") else f"https://www.threads.com/post/{c.get('post_code')}"),
            "帖子 ID": c.get("post_code", ""), "帖子作者": p.get("user_username", ""),
            "帖子发布日期": fmt_date(c.get("post_published_at")),
            "帖子正文摘要": txt[:80], "层级": "回复",
            "父评论 ID": c.get("parent_pk", ""), "评论者": c.get("user_username", ""),
            "评论内容": c.get("text", ""), "评论日期": fmt_date(c.get("published_at")),
            "点赞数": norm(c.get("like_count")), "子回复数": norm(c.get("reply_count")),
            "采集日期": COLLECTED, "_sort": fmt_date(c.get("published_at")),
        })
    rows = [r for r in rows if str(r.get("评论内容") or "").strip()]
    seen3, uniq3 = set(), []
    for r in rows:
        k = (r["平台"], r["帖子链接"], r["评论者"], str(r["评论内容"])[:40], r["评论日期"])
        if k in seen3:
            continue
        seen3.add(k)
        uniq3.append(r)
    rows = uniq3
    rows.sort(key=lambda x: (x["_sort"], x["平台"]))

    wb = Workbook()
    ws = wb.active
    ws.title = "说明"
    dist = Counter(r["平台"] for r in rows)
    ig_posts_n = len({r["帖子 ID"] for r in rows if r["平台"] == "Instagram"})
    th_posts_n = len({r["帖子 ID"] for r in rows if r["平台"] == "Threads"})
    write_info(ws, [
        ("需求 1 · 社交平台「兩餸飯」评论与回复", ""),
        ("", ""),
        ("评论时间范围", PERIOD),
        ("抓取日期", COLLECTED),
        ("评论总数", f"{len(rows)} 条"),
        ("覆盖帖子", f"Instagram {ig_posts_n} 帖 ｜ Threads {th_posts_n} 帖"),
        ("数据来源", "Instagram 帖子评论（一级 + 二级回复）｜ Threads 帖子回复"),
        ("匹配方式", "「帖子链接」「帖子 ID」对应「1_社交平台_帖子」中的记录，可直接用 VLOOKUP 关联"),
        ("说明", "Facebook 按需求不采评论"),
    ], dist.most_common(), "平台分布")
    write_sheet(wb.create_sheet("全部评论"), rows, COMMENT_COLS)
    for plat in ("Instagram", "Threads"):
        sub = [r for r in rows if r["平台"] == plat]
        if sub:
            write_sheet(wb.create_sheet(plat), sub, COMMENT_COLS)
    write_stats(wb.create_sheet("平台统计"), rows, date_key="评论日期")
    wb.save(OUT3)
    return rows


# ---------------- 4. 统计 md ----------------

def build_md(rows1, rows2, body_n, body_words, rows3):
    def ystat(rows):
        return {y: sum(1 for r in rows if r["发布日期"].startswith(y)) for y in
                ("2022", "2023", "2024", "2025", "2026")}

    L = []
    A = L.append
    A("# 数据采集统计\n")
    A(f"- 时间范围：**{PERIOD}**")
    A(f"- 抓取日期：{COLLECTED}\n")

    A("## 一、需求 1 · 社交平台帖子\n")
    A(f"合计 **{len(rows1)} 条**（`1_社交平台_帖子_兩餸飯_2022-2026.xlsx`）\n")
    A("| 平台 | 帖子 | 2022 | 2023 | 2024 | 2025 | 2026 |")
    A("| --- | --- | --- | --- | --- | --- | --- |")
    for p in ("Instagram", "Threads", "Facebook"):
        sub = [r for r in rows1 if r["平台"] == p]
        s = ystat(sub)
        A(f"| {p} | {len(sub)} | " + " | ".join(str(s[y]) for y in s) + " |")
    s = ystat(rows1)
    A(f"| **合计** | **{len(rows1)}** | " + " | ".join(f"**{s[y]}**" for y in s) + " |\n")

    A("## 二、需求 2 · Google 与媒体\n")
    A(f"合计 **{len(rows2)} 条**（`2_Google与媒体_兩餸飯_2022-2026.xlsx`）\n")
    A("| 平台 | 条数 | 2022 | 2023 | 2024 | 2025 | 2026 |")
    A("| --- | --- | --- | --- | --- | --- | --- |")
    for p in ("报社 / 网媒", "电视台", "生活饮食媒体", "YouTube", "新闻聚合", "境外媒体", "其他网站"):
        sub = [r for r in rows2 if r["平台"] == p]
        if not sub:
            continue
        s = ystat(sub)
        A(f"| {p} | {len(sub)} | " + " | ".join(str(s[y]) for y in s) + " |")
    s = ystat(rows2)
    A(f"| **合计** | **{len(rows2)}** | " + " | ".join(f"**{s[y]}**" for y in s) + " |")
    A(f"\n正文全文：**{body_n} 篇 / {body_words:,} 字**（报道正文 + 视频简介）\n")

    A("## 三、评论与回复\n")
    A(f"合计 **{len(rows3)} 条**（`3_评论与回复_兩餸飯_2022-2026.xlsx`）\n")
    A("| 平台 | 评论数 | 覆盖帖子 |")
    A("| --- | --- | --- |")
    for p in ("Instagram", "Threads"):
        sub = [r for r in rows3 if r["平台"] == p]
        A(f"| {p} | {len(sub)} | {len({r['帖子 ID'] for r in sub})} |")
    A(f"| **合计** | **{len(rows3)}** | — |\n")

    A("## 四、文件清单\n")
    A("| 文件 | 内容 |")
    A("| --- | --- |")
    A("| `1_社交平台_帖子_兩餸飯_2022-2026.xlsx` | IG / Threads / Facebook 帖子 |")
    A("| `2_Google与媒体_兩餸飯_2022-2026.xlsx` | 报社、电视台、生活媒体、YouTube（含报道正文） |")
    A("| `3_评论与回复_兩餸飯_2022-2026.xlsx` | IG 评论 + Threads 回复，含帖子链接与摘要 |")
    A("| `采集统计.md` | 本文件 |")

    open(OUTMD, "w", encoding="utf-8").write("\n".join(L) + "\n")


def main():
    rows1 = build_part1()
    print(f"[1] {OUT1}  → {len(rows1)} 条")
    rows2, body_n, body_words = build_part2()
    print(f"[2] {OUT2}  → {len(rows2)} 条 / 正文 {body_n} 篇 {body_words:,} 字")
    rows3 = build_part3()
    print(f"[3] {OUT3}  → {len(rows3)} 条")
    build_md(rows1, rows2, body_n, body_words, rows3)
    print(f"[md] {OUTMD}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把采集结果分成两份 Excel（需求1 / 需求2 分开）。

需求 1（社交平台）：
  data/需求1_社交平台_兩餸飯_2022-2026.xlsx
  Instagram 帖子 + 评论、Threads 帖子 + 回复、Facebook 线索

需求 2（Google 检索与媒体）：
  data/需求2_Google与媒体_兩餸飯_2022-2026.xlsx
  报社 / 电视台 / 生活媒体 / 新闻聚合 / YouTube，以及报道正文全文

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
OUT1 = os.path.join(DATA, "需求1_社交平台_兩餸飯_2022-2026.xlsx")
OUT2 = os.path.join(DATA, "需求2_Google与媒体_兩餸飯_2022-2026.xlsx")
COLLECTED = "2026-11-07"
PERIOD = "2022-01-01 ~ 2026-10-31"

COLS = [
    ("序号", 7, "center"),
    ("平台", 13, "center"),
    ("采集通道", 16, "center"),
    ("来源类型", 13, "center"),
    ("来源名称", 22, "left"),
    ("域名", 20, "left"),
    ("标题 / 正文", 58, "left"),
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

COMMENT_COLS = [
    ("序号", 7, "center"),
    ("平台", 11, "center"),
    ("帖子链接", 42, "left"),
    ("帖子发布日期", 13, "center"),
    ("层级", 7, "center"),
    ("父评论 ID", 18, "left"),
    ("评论者", 20, "left"),
    ("评论内容", 60, "left"),
    ("评论日期", 12, "center"),
    ("点赞数", 9, "right"),
    ("子回复数", 9, "right"),
    ("采集日期", 12, "center"),
]

BODY_COLS = [
    ("序号", 7, "center"),
    ("平台", 13, "center"),
    ("正文类型", 12, "center"),
    ("来源名称", 22, "left"),
    ("标题", 50, "left"),
    ("发布日期", 12, "center"),
    ("链接", 40, "left"),
    ("字数", 8, "right"),
    ("正文全文", 120, "left"),
]

PLATFORM = {
    "instagram": "Instagram", "facebook": "Facebook", "threads": "Threads", "youtube": "YouTube",
    "tv": "电视台", "news": "报社 / 网媒", "lifestyle": "生活饮食媒体",
    "aggregator": "新闻聚合", "intl_media": "境外媒体",
    "social_other": "其他社交平台", "other": "其他网站",
}
SOURCE_TYPE_CN = {
    "news": "报社网媒", "tv": "电视台", "lifestyle": "生活媒体", "youtube": "YouTube视频",
    "youtube_video": "YouTube视频", "ig_post": "IG贴文", "facebook": "Facebook",
    "instagram": "Instagram", "threads": "Threads", "aggregator": "新闻聚合",
    "intl_media": "境外媒体", "other": "其他网站", "social_other": "其他社交",
}
MEDIA_TYPE = {1: "单图", 2: "视频", 8: "多图"}
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
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def load_csv(name):
    with open(os.path.join(DATA, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
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


def write_sheet(ws, rows, cols=COLS):
    for i, (name, width, align) in enumerate(cols, start=1):
        c = ws.cell(row=1, column=i, value=name)
        c.font = Font(bold=True, color="FFFFFF", size=11, name="Microsoft YaHei")
        c.fill = PatternFill("solid", fgColor="1F4E79")
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDER
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.row_dimensions[1].height = 24
    ws.freeze_panes = "A2"
    for idx, r in enumerate(rows, start=1):
        vals = [idx] + [r.get(n, "") for n, _, _ in cols[1:]]
        for j, v in enumerate(vals, start=1):
            name, _, align = cols[j - 1]
            c = ws.cell(row=idx + 1, column=j, value=v)
            c.font = Font(size=10, name="Microsoft YaHei")
            c.alignment = Alignment(horizontal=align, vertical="center",
                                    wrap_text=name in ("标题 / 正文", "评论内容", "正文全文"))
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
        kc = ws.cell(row=i, column=1, value=k)
        kc.font = Font(bold=(i == 1), size=14 if i == 1 else 10, name="Microsoft YaHei")
        ws.cell(row=i, column=2, value=v).font = Font(size=10, name="Microsoft YaHei")
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 95
    row = len(lines) + 2
    ws.cell(row=row, column=1, value=dist_title).font = Font(bold=True, size=11, name="Microsoft YaHei")
    for i, (k, v) in enumerate(dist, start=row + 1):
        ws.cell(row=i, column=1, value=k).font = Font(size=10, name="Microsoft YaHei")
        ws.cell(row=i, column=2, value=f"{v} 条").font = Font(size=10, name="Microsoft YaHei")


def write_stats(ws, rows, years=("2022", "2023", "2024", "2025", "2026")):
    pc = Counter(r["平台"] for r in rows)
    header = ["平台"] + list(years) + ["合计"]
    for j, h in enumerate(header, start=1):
        c = ws.cell(row=1, column=j, value=h)
        c.font = Font(bold=True, color="FFFFFF", size=11, name="Microsoft YaHei")
        c.fill = PatternFill("solid", fgColor="1F4E79")
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDER
    ws.column_dimensions["A"].width = 20
    for j in range(2, len(header) + 1):
        ws.column_dimensions[get_column_letter(j)].width = 11
    r_i = 2
    for p, _ in pc.most_common():
        sub = [r for r in rows if r["平台"] == p]
        counts = [sum(1 for r in sub if r["发布日期"].startswith(y)) for y in years]
        for j, v in enumerate([p] + counts + [len(sub)], start=1):
            c = ws.cell(row=r_i, column=j, value=v)
            c.font = Font(size=10, name="Microsoft YaHei")
            c.alignment = Alignment(horizontal="center" if j > 1 else "left", vertical="center")
            c.border = BORDER
            if r_i % 2 == 0:
                c.fill = PatternFill("solid", fgColor="F2F7FB")
        r_i += 1
    totals = ["合计"] + [sum(1 for r in rows if r["发布日期"].startswith(y)) for y in years] + [len(rows)]
    for j, v in enumerate(totals, start=1):
        c = ws.cell(row=r_i, column=j, value=v)
        c.font = Font(bold=True, size=10, name="Microsoft YaHei")
        c.fill = PatternFill("solid", fgColor="DDEBF7")
        c.alignment = Alignment(horizontal="center" if j > 1 else "left", vertical="center")
        c.border = BORDER
    ws.freeze_panes = "A2"
    return pc


# ---------------- 需求 1：社交平台 ----------------

def build_part1():
    posts = load_jsonl(os.path.join(IG, "posts.jsonl"))
    comments = load_jsonl(os.path.join(IG, "comments.jsonl"))
    th_posts = load_jsonl(os.path.join(TH, "posts.jsonl"))
    th_replies = load_jsonl(os.path.join(TH, "replies.jsonl"))
    fb_posts = load_jsonl(os.path.join(DATA, "facebook", "posts.jsonl"))
    news = load_csv("google_news_2022-2026.csv")
    social = [r for r in news if r["source_type"] in ("facebook", "instagram", "threads")]

    rows = []
    for p in posts:
        ch = "IG 标签搜索" if str(p.get("query", "")).startswith("#") else "IG 关键词搜索"
        mt = MEDIA_TYPE.get(p.get("media_type"), "")
        note = mt
        if p.get("carousel_count") and p["carousel_count"] > 1:
            note += f"×{p['carousel_count']}"
        if p.get("hashtags"):
            note += f"｜#{p['hashtags'].replace(',', ' #')}"
        rows.append({
            "平台": "Instagram", "采集通道": ch, "来源类型": SOURCE_TYPE_CN["ig_post"],
            "来源名称": p.get("user_username") or "", "域名": "instagram.com",
            "标题 / 正文": (p.get("caption") or "").strip(),
            "发布日期": fmt_date(p.get("published_at")), "采集日期": COLLECTED,
            "链接": p.get("url", ""), "播放量": norm(p.get("view_count")),
            "点赞数": norm(p.get("like_count")), "评论数": norm(p.get("comment_count")),
            "时长(秒)": "", "检索关键词": p.get("query", ""), "标题命中": "是",
            "正文字数": len(p.get("caption") or ""), "备注": note,
            "_sort": fmt_date(p.get("published_at")),
        })
    for p in th_posts:
        txt = p.get("text") or ""
        note = f"赞{p.get('like_count') or 0}/回复{p.get('reply_count') or 0}/转发{p.get('repost_count') or 0}"
        if p.get("hashtags"):
            note += f"｜#{p['hashtags'].replace(',', ' #')}"
        rows.append({
            "平台": "Threads", "采集通道": "Threads 搜索", "来源类型": SOURCE_TYPE_CN["threads"],
            "来源名称": p.get("user_username") or "", "域名": "threads.com",
            "标题 / 正文": txt, "发布日期": fmt_date(p.get("published_at")),
            "采集日期": COLLECTED, "链接": p.get("url", ""), "播放量": "",
            "点赞数": norm(p.get("like_count")), "评论数": norm(p.get("reply_count")),
            "时长(秒)": "", "检索关键词": p.get("query", ""), "标题命中": "是",
            "正文字数": len(txt), "备注": note, "_sort": fmt_date(p.get("published_at")),
        })
    for p in fb_posts:
        txt = p.get("text") or ""
        note = "赞%s/评%s" % (p.get("reaction_count") or 0, p.get("comment_count") or 0)
        if p.get("group"):
            note += "｜群组 " + p["group"]
        rows.append({
            "平台": "Facebook", "采集通道": "Facebook 搜索", "来源类型": "Facebook贴文",
            "来源名称": p.get("author") or "", "域名": "facebook.com",
            "标题 / 正文": txt, "发布日期": fmt_date(p.get("published_at")),
            "采集日期": COLLECTED, "链接": p.get("url", ""), "播放量": "",
            "点赞数": norm(p.get("reaction_count")), "评论数": norm(p.get("comment_count")),
            "时长(秒)": "", "检索关键词": p.get("query", ""), "标题命中": "是",
            "正文字数": len(txt), "备注": note, "_sort": fmt_date(p.get("published_at")),
        })
    social_rows = []
    for r in social:
        st = r["source_type"]
        social_rows.append({
            "平台": PLATFORM.get(st, st), "采集通道": "Google News 索引",
            "来源类型": SOURCE_TYPE_CN.get(st, st),
            "来源名称": pretty_source(r.get("source_name"), r.get("source_domain")),
            "域名": r.get("source_domain", ""), "标题 / 正文": r.get("title", ""),
            "发布日期": fmt_date(r.get("published_at")), "采集日期": COLLECTED,
            "链接": r.get("url") or r.get("google_link", ""), "播放量": "", "点赞数": "",
            "评论数": "", "时长(秒)": "", "检索关键词": r.get("keyword", ""),
            "标题命中": "是" if r.get("title_hit") == "1" else "否", "正文字数": "",
            "备注": "链接线索，未采正文/评论", "_sort": fmt_date(r.get("published_at")),
        })
    rows.sort(key=lambda x: (x["_sort"], x["平台"]))

    # 评论 / 回复
    crow = [{
        "平台": "Instagram", "帖子链接": c.get("post_url", ""),
        "帖子发布日期": c.get("post_published_at", ""),
        "层级": "一级" if c.get("level") == 1 else "回复",
        "父评论 ID": c.get("parent_pk", ""), "评论者": c.get("user_username", ""),
        "评论内容": c.get("text", ""), "评论日期": fmt_date(c.get("published_at")),
        "点赞数": norm(c.get("like_count")), "子回复数": norm(c.get("child_count")),
        "采集日期": COLLECTED,
    } for c in comments]
    trow = [{
        "平台": "Threads", "帖子链接": f"https://www.threads.com/post/{c.get('post_code')}",
        "帖子发布日期": c.get("post_published_at", ""), "层级": "回复",
        "父评论 ID": c.get("parent_pk", ""), "评论者": c.get("user_username", ""),
        "评论内容": c.get("text", ""), "评论日期": fmt_date(c.get("published_at")),
        "点赞数": norm(c.get("like_count")), "子回复数": norm(c.get("reply_count")),
        "采集日期": COLLECTED,
    } for c in th_replies]

    wb = Workbook()
    ws = wb.active
    ws.title = "说明"
    dist = Counter(r["平台"] for r in rows)
    write_info(ws, [
        ("需求 1 · 社交平台「兩餸飯」贴文与评论", ""),
        ("", ""),
        ("采集时间范围", PERIOD),
        ("抓取日期", COLLECTED),
        ("内容条数", f"{len(rows)} 条（Instagram {dist['Instagram']} / Threads {dist['Threads']} / Facebook {dist['Facebook']}）"),
        ("评论与回复", "Instagram %d 条 ｜ Threads %d 条（Facebook 按需求不采评论）" % (len(crow), len(trow))),
        ("数据来源", "Instagram 标签/关键词搜索（3 账号轮换）｜ Threads 关键词搜索 ｜ Facebook 帖子搜索"),
        ("", ""),
        ("字段说明", ""),
        ("平台", "Instagram / Threads / Facebook"),
        ("采集通道", "IG 标签搜索 / IG 关键词搜索 / Threads 搜索 / Google News 索引"),
        ("来源名称", "IG 或 Threads 账号；Facebook 为页面名"),
        ("标题 / 正文", "贴文正文（caption / text），已过滤掉与「兩餸飯」无关的内容"),
        ("播放量 / 点赞数 / 评论数", "IG、Threads 的互动数据；Facebook 线索为空"),
        ("检索关键词", "命中该贴文时使用的标签或关键词"),
        ("正文字数", "贴文正文字符数"),
        ("备注", "媒体形态、话题标签、互动摘要"),
    ], dist.most_common())
    write_sheet(wb.create_sheet("全部内容"), rows)
    write_sheet(wb.create_sheet("Instagram帖子"), [r for r in rows if r["平台"] == "Instagram"
                                              and r["采集通道"].startswith("IG")])
    write_sheet(wb.create_sheet("Instagram评论"), crow, COMMENT_COLS)
    write_sheet(wb.create_sheet("Threads帖子"), [r for r in rows if r["平台"] == "Threads"
                                             and r["采集通道"] == "Threads 搜索"])
    write_sheet(wb.create_sheet("Threads回复"), trow, COMMENT_COLS)
    write_sheet(wb.create_sheet("Facebook帖子"), [r for r in rows if r["采集通道"] == "Facebook 搜索"])
    write_sheet(wb.create_sheet("Google News线索"), social_rows)
    write_stats(wb.create_sheet("平台统计"), rows)
    wb.save(OUT1)
    return len(rows), len(crow), len(trow)


# ---------------- 需求 2：Google 检索与媒体 ----------------

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

    media = [r for r in news if r["source_type"] in ("news", "tv", "lifestyle", "aggregator", "intl_media")]
    yt_ids = {r["video_id"] for r in yt}
    rows = []

    for r in media:
        st = r["source_type"]
        url = r.get("url", "")
        remark = ""
        if not url:
            remark = "原链接解码失败，链接列为 Google News 跳转"
        a = art_by_url.get(url)
        rows.append({
            "平台": PLATFORM.get(st, "其他网站"), "采集通道": "Google News",
            "来源类型": SOURCE_TYPE_CN.get(st, st),
            "来源名称": pretty_source(r.get("source_name"), r.get("source_domain")),
            "域名": r.get("source_domain", ""), "标题 / 正文": r.get("title", ""),
            "发布日期": fmt_date(r.get("published_at", "")), "采集日期": COLLECTED,
            "链接": url or r.get("google_link", ""), "播放量": "", "点赞数": "",
            "评论数": "", "时长(秒)": "", "检索关键词": r.get("keyword", ""),
            "标题命中": "是" if r.get("title_hit") == "1" else "否",
            "正文字数": (a or {}).get("text_len", "") or "",
            "备注": remark, "_sort": fmt_date(r.get("published_at", "")),
        })
    for r in news:
        if r["source_type"] != "youtube":
            continue
        url = r.get("url", "")
        vid = url.split("v=")[-1].split("&")[0] if "watch?v=" in url else ""
        remark = "Google News 索引的视频页"
        if vid in yt_ids:
            remark += "；另有详细元数据"
        rows.append({
            "平台": "YouTube", "采集通道": "Google News", "来源类型": "YouTube视频",
            "来源名称": pretty_source(r.get("source_name"), r.get("source_domain")),
            "域名": "youtube.com", "标题 / 正文": r.get("title", ""),
            "发布日期": fmt_date(r.get("published_at", "")), "采集日期": COLLECTED,
            "链接": url, "播放量": "", "点赞数": "", "评论数": "", "时长(秒)": "",
            "检索关键词": r.get("keyword", ""),
            "标题命中": "是" if r.get("title_hit") == "1" else "否", "正文字数": "",
            "备注": remark, "_sort": fmt_date(r.get("published_at", "")),
        })
    for r in yt:
        rows.append({
            "平台": "YouTube", "采集通道": "YouTube 搜索", "来源类型": "YouTube视频",
            "来源名称": r.get("channel", ""), "域名": "youtube.com",
            "标题 / 正文": r.get("title", ""), "发布日期": fmt_date(r.get("published_at", "")),
            "采集日期": COLLECTED, "链接": r.get("url", ""),
            "播放量": norm(r.get("view_count")), "点赞数": norm(r.get("like_count")),
            "评论数": "", "时长(秒)": norm(r.get("duration_sec")),
            "检索关键词": r.get("query", ""),
            "标题命中": "是" if r.get("title_hit") == "1" else "否",
            "正文字数": (desc_by_vid.get(r.get("video_id")) or {}).get("desc_len", "") or "",
            "备注": "精确日期" if r.get("date_source") == "watch_page" else "日期由相对时间估算",
            "_sort": fmt_date(r.get("published_at", "")),
        })
    rows.sort(key=lambda x: (x["_sort"], x["平台"]))

    body_rows = []
    for a in articles:
        if a.get("status") != "ok" or not a.get("text"):
            continue
        body_rows.append({
            "平台": PLATFORM.get(a.get("source_type"), "其他网站"), "正文类型": "报道正文",
            "来源名称": DOMAIN_NAME.get((a.get("domain") or "").lower(),
                                    (a.get("domain") or "").replace("www.", "")),
            "标题": a.get("title", ""), "发布日期": fmt_date(a.get("published_at")),
            "链接": a.get("url", ""), "字数": a.get("text_len", 0),
            "正文全文": (a.get("text") or "")[:30000],
        })
    for d in ytdesc:
        if not d.get("description"):
            continue
        body_rows.append({
            "平台": "YouTube", "正文类型": "视频简介", "来源名称": d.get("channel", ""),
            "标题": d.get("title", ""), "发布日期": fmt_date(d.get("published_at")),
            "链接": f"https://www.youtube.com/watch?v={d.get('video_id')}",
            "字数": d.get("desc_len", 0), "正文全文": (d.get("description") or "")[:30000],
        })
    body_rows.sort(key=lambda x: x["发布日期"])

    wb = Workbook()
    ws = wb.active
    ws.title = "说明"
    dist = Counter(r["平台"] for r in rows)
    total_words = sum(r["字数"] or 0 for r in body_rows)
    write_info(ws, [
        ("需求 2 · Google 检索与媒体「兩餸飯」报道、节目与视频", ""),
        ("", ""),
        ("采集时间范围", PERIOD),
        ("抓取日期", COLLECTED),
        ("内容条数", f"{len(rows)} 条"),
        ("正文", f"{len(body_rows)} 篇，合计 {total_words:,} 字"),
        ("数据来源", "Google News 索引（报社/电视台/网媒）｜ YouTube 搜索（视频元数据、简介、字幕）"),
        ("", ""),
        ("字段说明", ""),
        ("平台", "报社 / 网媒、电视台、生活饮食媒体、新闻聚合、境外媒体、YouTube"),
        ("采集通道", "Google News / YouTube 搜索"),
        ("来源名称", "媒体名、电视台频道名或 YouTube 频道"),
        ("标题 / 正文", "报道标题或视频标题（正文全文见「报道正文」sheet）"),
        ("发布日期", "发布时间 YYYY-MM-DD（Google News 为原发布日，YouTube 为上载日）"),
        ("播放量 / 点赞数", "仅 YouTube 有值"),
        ("正文字数", "该条已抓到的正文（报道全文或视频简介）字符数，空 = 未抓或抓取失败"),
        ("备注", "链接状态、日期精度等提示"),
    ], dist.most_common())
    write_sheet(wb.create_sheet("全部内容"), rows)
    write_sheet(wb.create_sheet("报刊网媒"), [r for r in rows if r["平台"] in
                                         ("报社 / 网媒", "生活饮食媒体", "境外媒体", "其他网站", "新闻聚合")])
    write_sheet(wb.create_sheet("电视台"), [r for r in rows if r["平台"] == "电视台"])
    write_sheet(wb.create_sheet("YouTube视频"), [r for r in rows if r["采集通道"] == "YouTube 搜索"])
    write_sheet(wb.create_sheet("报道正文"), body_rows, BODY_COLS)
    write_stats(wb.create_sheet("平台统计"), rows)
    wb.save(OUT2)
    return len(rows), len(body_rows), total_words


def main():
    n1, c1, r1 = build_part1()
    print(f"[需求1] {OUT1}")
    print(f"        内容 {n1} 条 ｜ IG 评论 {c1} ｜ Threads 回复 {r1}")
    n2, b2, w2 = build_part2()
    print(f"[需求2] {OUT2}")
    print(f"        内容 {n2} 条 ｜ 正文 {b2} 篇 / {w2:,} 字")


if __name__ == "__main__":
    main()

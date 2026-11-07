#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把采集结果整理成一份格式统一的 Excel（表头对齐、平台标注）。

数据源：
  data/google_news_2022-2026.csv   报社 / 电视台 / 网媒 / 社交线索（Google News 索引）
  data/youtube_2022-2026.csv       YouTube 视频
  data/ig/posts.jsonl              Instagram 帖子
  data/ig/comments.jsonl           Instagram 评论

输出：data/兩餸飯_跨平台传播_2022-2026.xlsx
sheet：说明 / 全部数据 / Instagram帖子 / Instagram评论 / YouTube视频 / 报刊网媒 / 电视台 / 平台统计
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
OUT = os.path.join(DATA, "兩餸飯_跨平台传播_2022-2026.xlsx")
COLLECTED = "2026-11-05"

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

PLATFORM = {
    "instagram": "Instagram",
    "facebook": "Facebook",
    "threads": "Threads",
    "youtube": "YouTube",
    "tv": "电视台",
    "news": "报社 / 网媒",
    "lifestyle": "生活饮食媒体",
    "aggregator": "新闻聚合",
    "intl_media": "境外媒体",
    "social_other": "其他社交平台",
    "other": "其他网站",
}

MEDIA_TYPE = {1: "单图", 2: "视频", 8: "多图"}

SOURCE_TYPE_CN = {
    "news": "报社网媒", "tv": "电视台", "lifestyle": "生活媒体", "youtube": "YouTube",
    "youtube_video": "YouTube视频", "ig_post": "IG贴文", "facebook": "Facebook",
    "instagram": "Instagram", "threads": "Threads", "aggregator": "新闻聚合",
    "intl_media": "境外媒体", "other": "其他网站", "social_other": "其他社交",
}

# 域名 → 媒体名（Google News 的 source_name 常直接给域名）
DOMAIN_NAME = {
    "i-cable.com": "有线新闻", "www.i-cable.com": "有线新闻",
    "tvb.com": "TVB", "news.tvb.com": "TVB 新闻", "programme.tvb.com": "TVB 节目",
    "mytvsuper.com": "myTV SUPER", "news.now.com": "Now 新闻", "hoy.tv": "HOY TV",
    "news.rthk.hk": "香港电台", "app2.rthk.hk": "香港电台",
    "ol.mingpao.com": "明报 OL", "news.mingpao.com": "明报", "mingpao.com": "明报",
    "stheadline.com": "星岛头条", "eastweek.stheadline.com": "东周刊",
    "hk01.com": "香港01", "hket.com": "经济日报", "topick.hket.com": "TOPick",
    "ps.hket.com": "经济日报", "news.hket.com": "经济日报",
    "wenweipo.com": "文汇报", "am730.com.hk": "am730", "bastillepost.com": "巴士的报",
    "hk.on.cc": "东网", "orientaldaily.com": "东方日报", "singtao.ca": "星岛(加)",
    "singtaousa.com": "星岛(美)", "mpweekly.com": "明周", "weekendhk.com": "新假期",
    "ufood.com.hk": "U Food", "hk.ulifestyle.com.hk": "ULifestyle", "gotrip.hk": "Gotrip",
    "tkww.hk": "Talkfood", "skypost.hk": "晴报", "dotdotnews.com": "点新闻",
    "orangenews.hk": "橙新闻", "scmp.com": "南华早报", "bbc.com": "BBC",
    "hk.news.yahoo.com": "Yahoo 新闻", "yahoo.com": "Yahoo", "youtube.com": "YouTube",
    "instagram.com": "Instagram", "facebook.com": "Facebook", "threads.com": "Threads",
}


def pretty_source(name: str, domain: str, st: str) -> str:
    name = (name or "").strip()
    d = (domain or "").lower().replace("www.", "")
    if not name or name.lower().replace("www.", "") in (d, domain.lower()):
        return DOMAIN_NAME.get(domain.lower(), DOMAIN_NAME.get(d, name or d))
    if name in ("YouTube", "Instagram", "Facebook", "Threads"):
        return DOMAIN_NAME.get(d, name)
    return name

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


def build_rows():
    news = load_csv("google_news_2022-2026.csv")
    yt = load_csv("youtube_2022-2026.csv")
    posts = load_jsonl(os.path.join(IG, "posts.jsonl"))
    articles = load_jsonl(os.path.join(DATA, "articles.jsonl"))
    ytdesc = load_jsonl(os.path.join(DATA, "youtube_details.jsonl"))
    th_posts = load_jsonl(os.path.join(DATA, "threads", "posts.jsonl"))
    th_replies = load_jsonl(os.path.join(DATA, "threads", "replies.jsonl"))

    yt_ids = {r["video_id"] for r in yt}
    art_by_url = {}
    for a in articles:
        if a.get("status") == "ok" and a.get("text"):
            art_by_url.setdefault(a["url"], a)
    desc_by_vid = {d["video_id"]: d for d in ytdesc if d.get("description")}
    rows = []

    for r in news:
        st = r["source_type"]
        url = r.get("url", "")
        vid = url.split("v=")[-1].split("&")[0] if "watch?v=" in url else ""
        remark = ""
        if st == "youtube" and vid in yt_ids:
            remark = "Google News 索引的视频页；另有 YouTube 详细元数据"
        elif st == "youtube":
            remark = "Google News 索引的视频页"
        elif st in ("facebook", "instagram", "threads"):
            remark = "社交平台链接线索，正文/评论另采"
        if not url:
            remark = (remark + "；" if remark else "") + "原链接解码失败，链接列为 Google News 跳转"
        rows.append({
            "平台": PLATFORM.get(st, "其他网站"),
            "采集通道": "Google News",
            "来源类型": SOURCE_TYPE_CN.get(st, st),
            "来源名称": pretty_source(r.get("source_name", ""), r.get("source_domain", ""), st),
            "域名": r.get("source_domain", ""),
            "标题 / 正文": r.get("title", ""),
            "发布日期": fmt_date(r.get("published_at", "")),
            "采集日期": COLLECTED,
            "链接": url or r.get("google_link", ""),
            "播放量": "",
            "点赞数": "",
            "评论数": "",
            "时长(秒)": "",
            "检索关键词": r.get("keyword", ""),
            "标题命中": "是" if r.get("title_hit") == "1" else "否",
            "正文字数": art_by_url.get(url, {}).get("text_len", "") or "",
            "备注": remark,
            "_sort": fmt_date(r.get("published_at", "")),
        })

    for r in yt:
        rows.append({
            "平台": "YouTube",
            "采集通道": "YouTube 搜索",
            "来源类型": SOURCE_TYPE_CN["youtube_video"],
            "来源名称": r.get("channel", ""),
            "域名": "youtube.com",
            "标题 / 正文": r.get("title", ""),
            "发布日期": fmt_date(r.get("published_at", "")),
            "采集日期": COLLECTED,
            "链接": r.get("url", ""),
            "播放量": norm(r.get("view_count")),
            "点赞数": norm(r.get("like_count")),
            "评论数": "",
            "时长(秒)": norm(r.get("duration_sec")),
            "检索关键词": r.get("query", ""),
            "标题命中": "是" if r.get("title_hit") == "1" else "否",
            "正文字数": desc_by_vid.get(r.get("video_id"), {}).get("desc_len", "") or "",
            "备注": "精确日期" if r.get("date_source") == "watch_page" else "日期由相对时间估算",
            "_sort": fmt_date(r.get("published_at", "")),
        })

    for p in posts:
        ch = "IG 标签搜索" if str(p.get("query", "")).startswith("#") else "IG 关键词搜索"
        mt = MEDIA_TYPE.get(p.get("media_type"), "")
        note = f"{mt}"
        if p.get("carousel_count") and p["carousel_count"] > 1:
            note += f"×{p['carousel_count']}"
        if p.get("hashtags"):
            note += f"｜#{p['hashtags'].replace(',', ' #')}"
        rows.append({
            "平台": "Instagram",
            "采集通道": ch,
            "来源类型": SOURCE_TYPE_CN["ig_post"],
            "来源名称": p.get("user_username") or "",
            "域名": "instagram.com",
            "标题 / 正文": (p.get("caption") or "").strip(),
            "发布日期": fmt_date(p.get("published_at")),
            "采集日期": COLLECTED,
            "链接": p.get("url", ""),
            "播放量": norm(p.get("view_count")),
            "点赞数": norm(p.get("like_count")),
            "评论数": norm(p.get("comment_count")),
            "时长(秒)": "",
            "检索关键词": p.get("query", ""),
            "标题命中": "是",
            "正文字数": len(p.get("caption") or ""),
            "备注": note,
            "_sort": fmt_date(p.get("published_at")),
        })

    for p in th_posts:
        txt = p.get("text") or ""
        note = f"赞{p.get('like_count') or 0}/回复{p.get('reply_count') or 0}/转发{p.get('repost_count') or 0}"
        if p.get("hashtags"):
            note += f"｜#{p['hashtags'].replace(',', ' #')}"
        rows.append({
            "平台": "Threads",
            "采集通道": "Threads 搜索",
            "来源类型": SOURCE_TYPE_CN["threads"],
            "来源名称": p.get("user_username") or "",
            "域名": "threads.com",
            "标题 / 正文": txt,
            "发布日期": fmt_date(p.get("published_at")),
            "采集日期": COLLECTED,
            "链接": p.get("url", ""),
            "播放量": "",
            "点赞数": norm(p.get("like_count")),
            "评论数": norm(p.get("reply_count")),
            "时长(秒)": "",
            "检索关键词": p.get("query", ""),
            "标题命中": "是",
            "正文字数": len(txt),
            "备注": note,
            "_sort": fmt_date(p.get("published_at")),
        })

    rows.sort(key=lambda x: (x["_sort"], x["平台"]))
    return rows


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
    link_col = [n for n, _, _ in cols].index("链接") + 1 if "链接" in [n for n, _, _ in cols] else None

    for idx, r in enumerate(rows, start=1):
        vals = [idx] + [r.get(name, "") for name, _, _ in cols[1:]]
        for j, v in enumerate(vals, start=1):
            name, _, align = cols[j - 1]
            c = ws.cell(row=idx + 1, column=j, value=v)
            c.font = Font(size=10, name="Microsoft YaHei")
            c.alignment = Alignment(horizontal=align, vertical="center",
                                    wrap_text=name in ("标题 / 正文", "评论内容"))
            c.border = BORDER
            if name == "链接" and v:
                c.hyperlink = v
                c.font = Font(size=10, name="Microsoft YaHei", color="0563C1", underline="single")
            if idx % 2 == 0:
                c.fill = PatternFill("solid", fgColor="F2F7FB")
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{len(rows) + 1}"
    return ws


def main():
    rows = build_rows()
    comments = load_jsonl(os.path.join(IG, "comments.jsonl"))
    articles = load_jsonl(os.path.join(DATA, "articles.jsonl"))
    ytdesc = load_jsonl(os.path.join(DATA, "youtube_details.jsonl"))
    th_replies = load_jsonl(os.path.join(DATA, "threads", "replies.jsonl"))

    wb = Workbook()

    # ---------- 说明 ----------
    ws = wb.active
    ws.title = "说明"
    info = [
        ("香港「兩餸飯」跨平台传播研究 — 数据表", ""),
        ("", ""),
        ("采集时间范围", "2022-01-01 ~ 2026-10-31"),
        ("抓取日期", COLLECTED),
        ("记录总数", f"{len(rows)} 条内容 + {len(comments)} 条 Instagram 评论"),
        ("数据来源", "Google News 索引 ｜ YouTube 搜索 ｜ Instagram 标签/关键词搜索（3 个已登录账号轮换）"),
        ("", ""),
        ("字段说明", ""),
        ("平台", "内容所在平台：Instagram / YouTube / 电视台 / 报社·网媒 / 生活饮食媒体 / 新闻聚合 / 境外媒体"),
        ("采集通道", "Google News 索引 / YouTube 搜索 / IG 标签搜索 / IG 关键词搜索"),
        ("来源类型", "news / tv / lifestyle / youtube / youtube_video / ig_post / facebook / instagram / threads …"),
        ("来源名称", "报社、电视台、媒体名、YouTube 频道或 IG 账号"),
        ("域名", "链接所属站点域名"),
        ("标题 / 正文", "报道标题、视频标题或 IG 贴文正文（caption）"),
        ("发布日期", "内容发布时间 YYYY-MM-DD"),
        ("采集日期", "抓取日期，全部为 2026-11-05"),
        ("链接", "可点击的原始链接（Google News 链接已解码还原）"),
        ("播放量 / 点赞数 / 评论数", "IG 与 YouTube 有值；Google News 索引条目为空"),
        ("时长(秒)", "YouTube 视频时长"),
        ("检索关键词", "命中该条记录时使用的检索词 / 标签"),
        ("标题命中", "标题或正文是否直接含「兩餸飯」类关键词"),
        ("备注", "媒体形态、话题标签、数据状态提示"),
        ("", ""),
        ("正文采集", "报社/电视台/生活媒体报道抓正文全文（trafilatura 通用正文抽取）；YouTube 抓视频简介"),
        ("平台分布", ""),
    ]
    for i, (k, v) in enumerate(info, start=1):
        kc = ws.cell(row=i, column=1, value=k)
        kc.font = Font(bold=(i == 1 or k in [x[0] for x in info if x[0] and i > 7]),
                       size=14 if i == 1 else 10, name="Microsoft YaHei")
        ws.cell(row=i, column=2, value=v).font = Font(size=10, name="Microsoft YaHei")
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 95

    pc = Counter(r["平台"] for r in rows)
    start = len(info) + 2
    for i, (p, n) in enumerate(pc.most_common(), start=start):
        ws.cell(row=i, column=1, value=p).font = Font(size=10, name="Microsoft YaHei")
        ws.cell(row=i, column=2, value=f"{n} 条").font = Font(size=10, name="Microsoft YaHei")

    # ---------- 数据表 ----------
    write_sheet(wb.create_sheet("全部数据"), rows)
    write_sheet(wb.create_sheet("Instagram帖子"), [r for r in rows if r["平台"] == "Instagram"])

    crow = []
    for c in comments:
        crow.append({
            "平台": "Instagram",
            "帖子链接": c.get("post_url", ""),
            "帖子发布日期": c.get("post_published_at", ""),
            "层级": "一级" if c.get("level") == 1 else "回复",
            "父评论 ID": c.get("parent_pk", ""),
            "评论者": c.get("user_username", ""),
            "评论内容": c.get("text", ""),
            "评论日期": fmt_date(c.get("published_at")),
            "点赞数": norm(c.get("like_count")),
            "子回复数": norm(c.get("child_count")),
            "采集日期": COLLECTED,
        })
    cot = wb.create_sheet("Instagram评论")
    write_sheet(cot, crow, COMMENT_COLS)

    write_sheet(wb.create_sheet("YouTube视频"), [r for r in rows if r["采集通道"] == "YouTube 搜索"])
    write_sheet(wb.create_sheet("报刊网媒"), [
        r for r in rows if r["采集通道"] == "Google News"
        and r["平台"] in ("报社 / 网媒", "生活饮食媒体", "境外媒体", "其他网站")])
    write_sheet(wb.create_sheet("电视台"), [r for r in rows if r["平台"] == "电视台"])

    # ---------- 报道正文 / 视频简介 ----------
    body_rows = []
    for a in articles:
        if a.get("status") != "ok" or not a.get("text"):
            continue
        body_rows.append({
            "平台": PLATFORM.get(a.get("source_type"), "其他网站"),
            "正文类型": "报道正文",
            "来源名称": DOMAIN_NAME.get((a.get("domain") or "").lower(),
                                    (a.get("domain") or "").replace("www.", "")),
            "标题": a.get("title", ""),
            "发布日期": fmt_date(a.get("published_at")),
            "链接": a.get("url", ""),
            "字数": a.get("text_len", 0),
            "正文全文": (a.get("text") or "")[:30000],
        })
    for d in ytdesc:
        if not d.get("description"):
            continue
        body_rows.append({
            "平台": "YouTube",
            "正文类型": "视频简介",
            "来源名称": d.get("channel", ""),
            "标题": d.get("title", ""),
            "发布日期": fmt_date(d.get("published_at")),
            "链接": f"https://www.youtube.com/watch?v={d.get('video_id')}",
            "字数": d.get("desc_len", 0),
            "正文全文": (d.get("description") or "")[:30000],
        })
    body_rows.sort(key=lambda x: x["发布日期"])
    write_sheet(wb.create_sheet("报道正文"), body_rows, BODY_COLS)

    # ---------- Threads 回复 ----------
    tr = []
    for c in th_replies:
        tr.append({
            "平台": "Threads",
            "帖子链接": f"https://www.threads.com/post/{c.get('post_code')}",
            "帖子发布日期": c.get("post_published_at", ""),
            "层级": "回复",
            "父评论 ID": c.get("parent_pk", ""),
            "评论者": c.get("user_username", ""),
            "评论内容": c.get("text", ""),
            "评论日期": fmt_date(c.get("published_at")),
            "点赞数": norm(c.get("like_count")),
            "子回复数": norm(c.get("reply_count")),
            "采集日期": COLLECTED,
        })
    if tr:
        write_sheet(wb.create_sheet("Threads回复"), tr, COMMENT_COLS)

    # ---------- 平台统计 ----------
    ws = wb.create_sheet("平台统计")
    years = ["2022", "2023", "2024", "2025", "2026"]
    header = ["平台"] + years + ["合计"]
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

    wb.save(OUT)
    print(f"saved {OUT}")
    print("内容条数", len(rows), "| 评论", len(crow))
    for p, n in pc.most_common():
        print(f"  {p}: {n}")


if __name__ == "__main__":
    main()

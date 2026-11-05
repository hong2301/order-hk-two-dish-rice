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

    yt_ids = {r["video_id"] for r in yt}
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
        rows.append({
            "平台": PLATFORM.get(st, "其他网站"),
            "采集通道": "Google News",
            "来源类型": st,
            "来源名称": r.get("source_name", ""),
            "域名": r.get("source_domain", ""),
            "标题 / 正文": r.get("title", ""),
            "发布日期": fmt_date(r.get("published_at", "")),
            "采集日期": COLLECTED,
            "链接": url,
            "播放量": "",
            "点赞数": "",
            "评论数": "",
            "时长(秒)": "",
            "检索关键词": r.get("keyword", ""),
            "标题命中": "是" if r.get("title_hit") == "1" else "否",
            "备注": remark,
            "_sort": fmt_date(r.get("published_at", "")),
        })

    for r in yt:
        rows.append({
            "平台": "YouTube",
            "采集通道": "YouTube 搜索",
            "来源类型": "youtube_video",
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
            "来源类型": "ig_post",
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

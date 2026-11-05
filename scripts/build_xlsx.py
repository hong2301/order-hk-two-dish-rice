#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把采集结果整理成一份格式统一的 Excel（表头对齐、平台标注）。

输出：data/兩餸飯_跨平台传播_2022-2026.xlsx
sheet：说明 / 全部数据 / YouTube视频 / 报刊网媒 / 电视台 / 社交平台线索 / 平台统计
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
OUT = os.path.join(DATA, "兩餸飯_跨平台传播_2022-2026.xlsx")
COLLECTED = "2026-11-05"

COLS = [
    ("序号", 7, "center"),
    ("平台", 15, "center"),
    ("采集通道", 14, "center"),
    ("来源类型", 12, "center"),
    ("来源名称", 22, "left"),
    ("域名", 22, "left"),
    ("标题", 60, "left"),
    ("发布日期", 12, "center"),
    ("采集日期", 12, "center"),
    ("链接", 45, "left"),
    ("播放量", 11, "right"),
    ("点赞数", 10, "right"),
    ("时长(秒)", 9, "right"),
    ("检索关键词", 16, "left"),
    ("标题命中", 9, "center"),
    ("备注", 26, "left"),
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

THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fmt_date(s):
    if not s:
        return ""
    s = s.strip()
    try:
        if "T" in s:
            return s[:10]
        return date.fromisoformat(s[:10]).isoformat()
    except Exception:
        return s[:10]


def norm(v):
    if v is None:
        return ""
    try:
        return int(float(v))
    except Exception:
        return ""


def build_rows():
    news = load("google_news_2022-2026.csv")
    yt = load("youtube_2022-2026.csv")

    yt_ids = {r["video_id"] for r in yt}
    rows = []

    for r in news:
        st = r["source_type"]
        remark = ""
        url = r.get("url", "")
        vid = url.split("v=")[-1].split("&")[0] if "watch?v=" in url else ""
        if st == "youtube" and vid in yt_ids:
            remark = "Google News 索引的视频页；另有 YouTube 详细元数据"
        elif st == "youtube":
            remark = "Google News 索引的视频页"
        elif st in ("facebook", "instagram", "threads"):
            remark = "社交平台链接线索，正文/评论待采"
        rows.append({
            "平台": PLATFORM.get(st, "其他网站"),
            "采集通道": "Google News",
            "来源类型": st,
            "来源名称": r.get("source_name", ""),
            "域名": r.get("source_domain", ""),
            "标题": r.get("title", ""),
            "发布日期": fmt_date(r.get("published_at", "")),
            "采集日期": COLLECTED,
            "链接": url,
            "播放量": "",
            "点赞数": "",
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
            "标题": r.get("title", ""),
            "发布日期": fmt_date(r.get("published_at", "")),
            "采集日期": COLLECTED,
            "链接": r.get("url", ""),
            "播放量": norm(r.get("view_count")),
            "点赞数": norm(r.get("like_count")),
            "时长(秒)": norm(r.get("duration_sec")) or norm(r.get("duration")),
            "检索关键词": r.get("query", ""),
            "标题命中": "是" if r.get("title_hit") == "1" else "否",
            "备注": "精确日期" if r.get("date_source") == "watch_page" else "日期由相对时间估算",
            "_sort": fmt_date(r.get("published_at", "")),
        })

    rows.sort(key=lambda x: (x["_sort"], x["平台"]), reverse=False)
    return rows


def write_sheet(ws, rows, title_note=""):
    # 表头
    for i, (name, width, align) in enumerate(COLS, start=1):
        c = ws.cell(row=1, column=i, value=name)
        c.font = Font(bold=True, color="FFFFFF", size=11, name="Microsoft YaHei")
        c.fill = PatternFill("solid", fgColor="1F4E79")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=False)
        c.border = BORDER
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.row_dimensions[1].height = 24
    ws.freeze_panes = "A2"

    for idx, r in enumerate(rows, start=1):
        vals = [idx] + [r.get(name, "") for name, _, _ in COLS[1:]]
        for j, v in enumerate(vals, start=1):
            name, _, align = COLS[j - 1]
            c = ws.cell(row=idx + 1, column=j, value=v)
            c.font = Font(size=10, name="Microsoft YaHei")
            c.alignment = Alignment(horizontal=align, vertical="center",
                                    wrap_text=(name == "标题"))
            c.border = BORDER
            if name == "链接" and v:
                c.hyperlink = v
                c.font = Font(size=10, name="Microsoft YaHei", color="0563C1", underline="single")
            if idx % 2 == 0:
                c.fill = PatternFill("solid", fgColor="F2F7FB")
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLS))}{len(rows) + 1}"
    return ws


def main():
    rows = build_rows()

    wb = Workbook()

    # ---------- 说明 ----------
    ws = wb.active
    ws.title = "说明"
    info = [
        ("香港「兩餸飯」跨平台传播研究 — 数据表", ""),
        ("", ""),
        ("采集时间范围", "2022-01-01 ~ 2026-10-31"),
        ("抓取日期", COLLECTED),
        ("记录总数", f"{len(rows)} 条"),
        ("数据来源", "Google News 索引（报社/网媒/电视台/社交平台/YouTube）+ YouTube 搜索"),
        ("", ""),
        ("字段说明", ""),
        ("平台", "内容所在的平台，见下表"),
        ("采集通道", "Google News 索引 / YouTube 搜索"),
        ("来源类型", "机器分类：news / tv / lifestyle / youtube / facebook / instagram / threads / aggregator / intl_media"),
        ("来源名称", "报社、电视台、媒体名、YouTube 频道或社交账号"),
        ("域名", "链接所属站点域名"),
        ("标题", "报道标题 / 贴文标题 / 视频标题"),
        ("发布日期", "内容发布时间，YYYY-MM-DD"),
        ("采集日期", "抓取日期，全部为 2026-11-05"),
        ("链接", "可直接点击跳转的原始链接（Google News 链接已解码还原）"),
        ("播放量 / 点赞数", "仅 YouTube 视频有值；Google News 索引条目为空"),
        ("时长(秒)", "YouTube 视频时长"),
        ("检索关键词", "命中该条记录时使用的检索词"),
        ("标题命中", "标题是否直接含「兩餸飯」等关键词"),
        ("备注", "数据状态提示（社交线索待采 / 精确日期 / 相对时间估算）"),
        ("", ""),
        ("平台分布", ""),
        ("提示", "YouTube 共 626 条 = Google News 索引的视频页 307 条 + YouTube 搜索直采 319 条，用「采集通道」列区分"),
    ]
    r0 = 1
    for i, (k, v) in enumerate(info):
        ws.cell(row=r0 + i, column=1, value=k).font = Font(
            bold=(k in ("平台", "采集通道", "来源类型", "来源名称", "域名", "标题", "发布日期",
                        "采集日期", "链接", "播放量 / 点赞数", "时长(秒)", "检索关键词",
                        "标题命中", "备注", "平台分布") or i == 0),
            size=11 if i == 0 else 10, name="Microsoft YaHei")
        ws.cell(row=r0 + i, column=2, value=v).font = Font(size=10, name="Microsoft YaHei")
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 95
    ws.cell(row=1, column=1).font = Font(bold=True, size=14, name="Microsoft YaHei")

    pc = Counter(r["平台"] for r in rows)
    start = r0 + len(info)
    for i, (p, n) in enumerate(pc.most_common(), start=start):
        ws.cell(row=i, column=1, value=p).font = Font(size=10, name="Microsoft YaHei")
        ws.cell(row=i, column=2, value=f"{n} 条").font = Font(size=10, name="Microsoft YaHei")

    # ---------- 全部数据 ----------
    write_sheet(wb.create_sheet("全部数据"), rows)

    # ---------- 分表 ----------
    groups = {
        "YouTube视频": [r for r in rows if r["采集通道"] == "YouTube 搜索"],
        "报刊网媒": [r for r in rows if r["平台"] in ("报社 / 网媒", "生活饮食媒体", "境外媒体", "其他网站")
                     and r["采集通道"] == "Google News"],
        "电视台": [r for r in rows if r["平台"] == "电视台"],
        "社交平台线索": [r for r in rows if r["平台"] in ("Instagram", "Facebook", "Threads", "其他社交平台")],
    }
    for name, rs in groups.items():
        if rs:
            write_sheet(wb.create_sheet(name), rs)

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
        vals = [p] + counts + [len(sub)]
        for j, v in enumerate(vals, start=1):
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
    print("total", len(rows))
    for p, n in pc.most_common():
        print(f"  {p}: {n}")
    for name, rs in groups.items():
        print(f"  [sheet] {name}: {len(rs)}")


if __name__ == "__main__":
    main()

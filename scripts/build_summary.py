#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""对采集结果做后处理：加命中标记、生成描述性统计。

输入：data/google_news_2022-2026.csv, data/youtube_2022-2026.csv
输出：data/stats.json, data/summary.md（同时回写 CSV 的 title_hit 列）
"""
import csv
import json
import os
import re
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

KW = ["餸飯", "餸饭", "𩠌飯", "two-dish", "two dish", "this this rice", "dish rice"]


def hit(title):
    t = (title or "").lower()
    return int(any(k.lower() in t for k in KW))


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def save(name, rows, cols):
    with open(os.path.join(DATA, name), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    news = load("google_news_2022-2026.csv")
    yt = load("youtube_2022-2026.csv")

    for r in news:
        r["title_hit"] = hit(r["title"])
    for r in yt:
        r["title_hit"] = hit(r["title"])

    save("google_news_2022-2026.csv", news, list(news[0].keys()))
    save("youtube_2022-2026.csv", yt, list(yt[0].keys()))

    def by_year(rows):
        return dict(sorted(Counter(r["published_at"][:4] for r in rows).items()))

    def by_month(rows):
        c = Counter(r["published_at"][:7] for r in rows)
        return dict(sorted(c.items()))

    tv = [r for r in news if r["source_type"] == "tv"]
    yt_news = [r for r in news if r["source_type"] == "youtube"]

    stats = {
        "period": "2022-01-01 ~ 2026-10-31",
        "collected_at": "2026-11-05",
        "google_news": {
            "total": len(news),
            "title_hit": sum(r["title_hit"] for r in news),
            "by_type": dict(Counter(r["source_type"] for r in news).most_common()),
            "by_year": by_year(news),
            "by_month": by_month(news),
            "top_domains": dict(Counter(r["source_domain"] for r in news).most_common(20)),
            "tv_domains": dict(Counter(r["source_domain"] for r in tv).most_common()),
        },
        "youtube": {
            "total": len(yt),
            "title_hit": sum(r["title_hit"] for r in yt),
            "by_year": by_year(yt),
            "by_month": by_month(yt),
            "top_channels": dict(Counter(r["channel"] for r in yt).most_common(20)),
            "total_views": sum(int(r["view_count"]) for r in yt if r["view_count"]),
            "date_source": dict(Counter(r["date_source"] for r in yt)),
        },
    }

    with open(os.path.join(DATA, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    # ---- markdown 摘要 ----
    L = []
    A = L.append
    A("# 采集结果摘要\n")
    A(f"采集时间范围：**{stats['period']}**　｜　抓取日期：{stats['collected_at']}\n")
    g, y = stats["google_news"], stats["youtube"]
    A("## 一、Google 新闻 / 网媒（google_news_2022-2026.csv）\n")
    A(f"- 记录数：**{g['total']}** 条（标题直接命中关键词 {g['title_hit']} 条）")
    A(f"- 来源类型：{', '.join(f'{k} {v}' for k, v in g['by_type'].items())}")
    A(f"- 年度分布：{', '.join(f'{k} {v}' for k, v in g['by_year'].items())}\n")
    A("| 年份 | 条数 | 月均 |")
    A("| --- | --- | --- |")
    for yr, n in g["by_year"].items():
        months = len([m for m in g["by_month"] if m.startswith(yr)])
        A(f"| {yr} | {n} | {round(n / max(months, 1), 1)} |")
    A("\n**来源域名 Top 15**\n")
    A("| 域名 | 条数 |")
    A("| --- | --- |")
    for d, n in list(g["top_domains"].items())[:15]:
        A(f"| {d} | {n} |")
    if g["tv_domains"]:
        A("\n**电视台来源**\n")
        A("| 电视台域名 | 条数 |")
        A("| --- | --- |")
        for d, n in g["tv_domains"].items():
            A(f"| {d} | {n} |")

    A("\n## 二、YouTube（youtube_2022-2026.csv）\n")
    A(f"- 视频数：**{y['total']}** 条（标题直接命中 {y['title_hit']} 条）")
    A(f"- 累计播放量：{y['total_views']:,}")
    A(f"- 年度分布：{', '.join(f'{k} {v}' for k, v in y['by_year'].items())}")
    A(f"- 日期来源：{', '.join(f'{k} {v}' for k, v in y['date_source'].items())}\n")
    A("**频道 Top 15**\n")
    A("| 频道 | 视频数 |")
    A("| --- | --- |")
    for c, n in list(y["top_channels"].items())[:15]:
        A(f"| {c} | {n} |\n")

    with open(os.path.join(DATA, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))

    print(f"news {g['total']} | youtube {y['total']}")
    print("by_type", g["by_type"])
    print("news by_year", g["by_year"])
    print("yt by_year", y["by_year"])


if __name__ == "__main__":
    main()

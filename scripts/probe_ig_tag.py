# -*- coding: utf-8 -*-
"""探测 IG 标签页 / 关键词搜索的响应结构（不落盘，只打印）"""
import json
import sys
import time
import urllib.parse

from DrissionPage import Chromium

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9222
TAGS = ["兩餸飯", "two餸飯", "twodishrice", "兩餸飯關注組"]


def main():
    br = Chromium(PORT)
    tab = br.latest_tab
    tab.listen.start("graphql")
    for tag in TAGS:
        url = "https://www.instagram.com/explore/tags/" + urllib.parse.quote(tag) + "/"
        print("\n=== TAG:", tag, url)
        tab.get(url)
        time.sleep(8)
        for _ in range(6):
            try:
                body = tab.run_js("document.body.innerText", as_expr=True) or ""
            except Exception:
                body = ""
            print("  text[:200]:", body.replace("\n", " | ")[:200])
            break
        n = 0
        try:
            pkts = tab.listen.wait(count=1, timeout=6, fit_count=False)
        except Exception:
            pkts = []
        if pkts is None:
            pkts = []
        if not isinstance(pkts, list):
            pkts = [pkts]
        pkts = [p for p in pkts if p]
        for p in pkts:
            n += 1
            try:
                b = p.response.body
            except Exception:
                continue
            if not isinstance(b, dict):
                continue
            data = b.get("data") or {}
            keys = list(data.keys())
            if keys:
                print("  resp url:", str(getattr(p, "url", ""))[:110])
                print("  data keys:", keys)
                for k in keys:
                    v = data[k]
                    if isinstance(v, dict):
                        print("    ", k, "subkeys:", list(v.keys())[:10])
                        items = v.get("items") or v.get("edges")
                        if items:
                            print("     items:", len(items))
                            first = items[0]
                            node = first.get("node") if isinstance(first, dict) and "node" in first else first
                            if isinstance(node, dict):
                                print("     node keys:", list(node.keys())[:25])
        print("  packets:", n)
    tab.listen.stop()


if __name__ == "__main__":
    main()

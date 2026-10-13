#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""宽度预算自检（布局驱动版）。

上一版把常量写死在脚本里；现在窗口要嵌进成片，尺寸会变，
所以这里从 dense_window 的布局常量推算，跟着布局一起变。
"""
from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dense_scene
import dense_window as dw


def cols(s: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def budget(win_w: int = 354, sidebar: int = 120):
    main = win_w - sidebar
    avail = main - 12 * 2 - (9 * 2 + 2)     # scroll padding + card padding/border
    out = {}
    for key, px in (("code", 10.0), ("tool", 9.0), ("table", 9.5)):
        out[key] = int(avail / (px * 0.6))
    return main, avail, out


def main():
    win_w = int(sys.argv[1]) if len(sys.argv) > 1 else 354
    sidebar = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    mainpx, avail, cap = budget(win_w, sidebar)
    print(f"窗口 {win_w}px  侧栏 {sidebar}px  主区 {mainpx}px  卡片内 {avail}px")
    print(f"列数上限： code {cap['code']}  tool {cap['tool']}  table 每列 {cap['table']//2}\n")

    sc = dense_scene.load(HERE / "content" / "scene04.json")
    bad = []
    for ti, tn in enumerate(sc["turns"]):
        for key in ("code", "tool"):
            if key not in tn:
                continue
            limit = cap[key]
            for l in tn[key]["lines"]:
                n = cols(l)
                if n > limit:
                    bad.append((ti, key, n, limit, l))
    # 表格每列
    for ti, tn in enumerate(sc["turns"]):
        if "table" in tn:
            half = cap["table"] // 2
            for r in tn["table"]["rows"]:
                for c in r:
                    n = cols(c)
                    if n > half:
                        bad.append((ti, "table", n, half, c))

    if not bad:
        print("全部在预算内。")
        return
    print(f"超宽 {len(bad)} 处：")
    for ti, key, n, limit, l in bad:
        print(f"  块{ti} [{key}] {n} > {limit} 列   {l}")


if __name__ == "__main__":
    main()

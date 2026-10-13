#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""拍点对位：把画面动作的时刻咬到 130 BPM 网格上。

130 BPM -> 一拍 = 0.461538s，首拍在 0.1587s（这个网格是整首歌拟合出来的，
100 秒漂移 < 1ms，所以可以直接用，不是估算）。

做法：对每个动作时刻，二分求最近的拍点；再报出偏差，
偏差大的说明这个动作本来就"不在拍上"，需要挪。
"""
from __future__ import annotations

import bisect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(r"D:\大肥鱼（deepseek）\whale-pv2")))
import clock as C  # noqa: E402

# 现在的动作时刻（来自 expand.py 的 KEYS 与剧本里的内容事件）
LAYOUT = [
    (0.00, "开场：单窗居中"),
    (1.40, "停住，让观众看清窗口"),
    (1.85, "起步：窗口开始往左让"),
    (2.45, "右栏从左侧展开"),
    (3.10, "右栏接近满宽"),
    (3.70, "定型：双栏"),
    (22.10, "最后一条打完，停一拍"),
    (24.40, "右栏被吸回窗口"),
    (25.00, "顿一下"),
    (27.20, "消息褪完"),
    (28.40, "窗口滑回中央"),
    (30.40, "空窗留白开始"),
]

CONTENT = [
    (0.30, "用户打字：把这个仓库读完"),
    (0.80, "AI 出现"),
    (0.86, "思考开始"),
    (1.12, "正文开始"),
    (2.05, "工具输出开始"),
    (3.10, "第二条 AI"),
    (3.34, "正文开始"),
    (4.10, "代码块开始"),
    (8.20, "用户：它哪里出错了"),
    (9.00, "AI 出现"),
    (9.30, "正文开始"),
    (10.30, "工具输出开始"),
    (13.40, "第三条 AI"),
    (13.64, "正文开始"),
    (14.60, "表格出现"),
    (19.20, "用户：谢谢"),
    (20.00, "AI 出现"),
    (20.30, "正文开始"),
    (25.00, "开始褪去（_clear）"),
]

PHASES = [
    (5.20, "右栏 code 结束"),
    (8.20, "右栏 idle"),
    (10.60, "右栏 tool"),
    (13.40, "右栏 idle"),
    (14.60, "右栏 table"),
    (19.20, "右栏 idle"),
]


def nearest_beat(t: float):
    """最近的拍点，以及拍的序号。"""
    i = max(0, int(round((t - C.FIRST_BEAT) / C.BEAT)))
    best, bi = None, i
    for k in (i - 1, i, i + 1):
        if k < 0:
            continue
        bt = C.beat_t(k)
        if best is None or abs(bt - t) < abs(best - t):
            best, bi = bt, k
    return best, bi


def report(name: str, items):
    print(f"\n=== {name} ===")
    print(f"{'现在':>7} {'最近拍':>7} {'拍号':>5} {'偏差ms':>8}   说明")
    worst = []
    for t, lab in items:
        bt, bi = nearest_beat(t)
        d = (t - bt) * 1000
        flag = ""
        if abs(d) > 120:
            flag = "  ← 偏得多"
            worst.append((abs(d), t, lab))
        print(f"{t:7.2f} {bt:7.3f} {bi:5d} {d:+8.0f}{flag}   {lab}")
    if worst:
        print(f"  偏差 >120ms 的有 {len(worst)} 处，最大 {max(worst)[0]:.0f}ms")
    return worst


def main():
    print(f"130 BPM   一拍 {C.BEAT:.6f}s   首拍 {C.FIRST_BEAT}s")
    print(f"四分之一拍 {C.QUART:.6f}s（这是最小可用步长）")
    a = report("版式动作", LAYOUT)
    b = report("内容事件", CONTENT)
    c = report("右栏形态", PHASES)
    print(f"\n合计偏得多的：{len(a)+len(b)+len(c)} 处")


if __name__ == "__main__":
    main()

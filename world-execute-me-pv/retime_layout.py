#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 expand.py 的 KEYS 改成「用拍号构造」，不写十进制字面量。

上一版生成的是 t=3.389 这种三位小数，反推 beat 时会差 0.0005 拍，
对位检查报错（虽然是精度问题不是设计问题，但既然能精确就该精确）。
改成 C.beat_t(n)，值就是 FIRST_BEAT + n*BEAT，反推必然得到整数。
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PV2))
sys.path.insert(0, str(HERE))

import clock as C  # noqa: E402
import beat_table as BT  # noqa: E402

P = HERE / "expand.py"

# (拍号, 窗口x 进度, 右栏占比, 说明)
KEYS_BEAT = [
    (BT.BEATS["open_start"],  0.00, 0.00, "开场：只有一扇窗，居中"),
    (BT.BEATS["open_hold"],   0.00, 0.00, "停住，让观众看清这扇窗"),
    # beat 3 与 beat 4 之间完全不动 —— 之前放了 0.10 的预动，
    # 动作从 beat 3 就跑起来了，观众感知的「开始」提前半拍。
    (BT.BEATS["open_begin"],  0.00, 0.00, "停住：下一步才是起步（不许预动）"),
    # beat 4 → beat 8 是**一段**缓动，中间不插关键帧。
    # 插了的话缓动会重新起步，重音跑到插点上去（实测峰值落在 beat 6 而非 4）。
    (BT.BEATS["open_full"],   1.00, 1.00, "起步并定型：双栏（重音在 beat 4）"),

    # ---- 收回。同样一个动作一段缓动。
    #      展开是「内容装不下了」，收回是「内容没了」——
    #      所以先把右栏吸回窗口（同时淡出），消息再逐条褪，最后窗口才滑回中央。
    (BT.BEATS["close_hold"],  1.00, 1.00, "最后一条打完，停一拍让观众读完"),
    (BT.SPANS["retract"][1],  1.00, 0.00, "右栏被吸回窗口（重音在 beat 48）"),
    (BT.BEATS["close_pause"], 1.00, 0.00, "顿一下：她走了，只剩左边的窗"),
    (BT.SPANS["clear"][1],    1.00, 0.00, "消息逐条褪完"),
    (BT.SPANS["recenter"][1], 0.00, 0.00, "窗口滑回中央（重音在 beat 59）"),
    (BT.BEATS["close_end"],   0.00, 0.00, "空窗，留白"),
]


def main():
    body = "\n".join(
        f"    (C.beat_t({n:>2}), {kx:.2f}, {kr:.2f}),   # beat {n:>2}  {lab}"
        for n, kx, kr, lab in KEYS_BEAT)

    block = (
        "# (时刻, 窗口x 的插值进度 0=居中 1=贴左, 右栏占比)\n"
        "#\n"
        "# 用**拍号构造**，不写十进制字面量：写 t=3.389 反推 beat 会差 0.0005 拍，\n"
        "# 对位检查会报错。C.beat_t(n) 的值就是 FIRST_BEAT + n*BEAT，必然精确。\n"
        "# 拍号来自 beat_table.py —— 改节奏只改那张表。\n"
        "KEYS = [\n" + body + "\n]\n"
    )

    s = P.read_text(encoding="utf-8")
    i = s.index("# (时刻, 窗口x 的插值进度")
    j = s.index("\n\n", s.index("]", i))
    s = s[:i] + block + s[j:]
    P.write_text(s, encoding="utf-8")
    ast.parse(s)
    print("KEYS 已改为拍号构造，语法 OK")


if __name__ == "__main__":
    main()

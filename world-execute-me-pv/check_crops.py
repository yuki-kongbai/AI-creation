#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""量每个裁切「切掉了什么」。

裁切比例是手写的（bust = x 14%~86% 等），没量过内容边界，
所以可能把立绘里的道具切一半 —— 比如她左手那本笔记本。

这个脚本把「画布尺寸」和「内容 alpha 包围盒」对比，
并报出内容是否贴到（或越过）了裁切边缘。
"""
from __future__ import annotations

import sys
from pathlib import Path

PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
sys.path.insert(0, str(PV2))
import tk  # noqa: E402

FULL = tk.sprite_src("maid-right", "full")
FW, FH = FULL.size
print(f"原图 {FW}×{FH}")
print(f"CROPS = {tk.CROPS}\n")

for name, frac in tk.CROPS.items():
    if not frac:
        continue
    x0, y0, x1, y1 = frac
    px = (int(x0 * FW), int(y0 * FH), int(x1 * FW), int(y1 * FH))
    src = tk.sprite_src("maid-right", name)
    bb = src.getchannel("A").getbbox()
    print(f"[{name}]  裁切比例 {frac}")
    print(f"   像素区域 x[{px[0]},{px[2]}] y[{px[1]},{px[3]}]  ->  画布 {src.size}")
    print(f"   裁切内 alpha 包围盒 {bb}")
    if bb:
        # 内容是否贴到边缘（贴着 = 很可能被切了）
        edge = []
        if bb[0] <= 1:
            edge.append("左")
        if bb[1] <= 1:
            edge.append("上")
        if bb[2] >= src.width - 1:
            edge.append("右")
        if bb[3] >= src.height - 1:
            edge.append("下")
        if edge:
            print(f"   ⚠ 内容贴到{''.join(edge)}边缘 —— 很可能被切掉了一部分")
        else:
            print("   ✓ 内容四周都有留白，没有被切")
    print()


def main():
    pass


if __name__ == "__main__":
    main()

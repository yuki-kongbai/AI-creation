#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""量两件道具的准确包围盒 —— 用连通域，不再靠网格目测。

她左手一本笔记本、右手一支笔。这两件都必须完整，
否则就是「半个书」那种怪。所以先量准它们的位置。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
sys.path.insert(0, str(PV2))
import tk  # noqa: E402


def components(mask: np.ndarray, min_px: int = 400):
    """四连通域标记（纯 numpy，够用）。"""
    H, W = mask.shape
    lab = np.zeros((H, W), np.int32)
    cur = 0
    out = []
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys, xs):
        if lab[y0, x0]:
            continue
        cur += 1
        stack = [(y0, x0)]
        lab[y0, x0] = cur
        px = []
        while stack:
            y, x = stack.pop()
            px.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = cur
                    stack.append((ny, nx))
        if len(px) >= min_px:
            a = np.array(px)
            out.append((len(px), a[:, 1].min(), a[:, 0].min(),
                        a[:, 1].max(), a[:, 0].max()))
    out.sort(reverse=True)
    return out


def main():
    src = tk.sprite_src("maid-right", "full")
    W, H = src.size
    a = np.asarray(src.getchannel("A"), dtype=np.uint8)
    print(f"原图 {W}×{H}")

    # 笔记本：左侧区域（x < 34%），且 y 在 10%~40%
    nb = np.zeros_like(a, dtype=bool)
    nb[int(H * 0.08):int(H * 0.42), :int(W * 0.34)] = a[int(H * 0.08):int(H * 0.42), :int(W * 0.34)] > 30
    comps = components(nb, 2000)
    print("\n左侧候选连通域（按面积）：")
    for n, x0, y0, x1, y1 in comps[:5]:
        print(f"  {n:>7} px   x[{x0},{x1}] y[{y0},{y1}]   "
              f"占图 x{x0/W:.2f}-{x1/W:.2f}  y{y0/H:.2f}-{y1/H:.2f}")

    # 笔：右侧区域（x > 62%），y 15%~40%
    pn = np.zeros_like(a, dtype=bool)
    pn[int(H * 0.14):int(H * 0.44), int(W * 0.60):] = a[int(H * 0.14):int(H * 0.44), int(W * 0.60):] > 30
    comps2 = components(pn, 800)
    print("\n右侧候选连通域（按面积）：")
    for n, x0, y0, x1, y1 in comps2[:5]:
        print(f"  {n:>7} px   x[{x0},{x1}] y[{y0},{y1}]   "
              f"占图 x{x0/W:.2f}-{x1/W:.2f}  y{y0/H:.2f}-{y1/H:.2f}")


if __name__ == "__main__":
    main()

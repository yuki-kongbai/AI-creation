#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""右栏的她：两个干净方案，二选一。

先说清这个取舍（量过的）：
    她在这张立绘里横向占 x 6%~80%（笔记本 + 笔都在内侧），
    所以「包含所有道具」= 横向至少 0.74 宽。
    面板 866px 时，头就只有约 91px —— 比现在小 3 倍。
    四张立绘全是 1.8~1.9 的全身像，没有近景版本，所以这是硬约束。

方案 A「头肩」  纵向切在笔记本上方，根本不含书 —— 不是切一半，是不出现
方案 B「全身」  完整保留，但很小；靠面板做成竖向才不空
"""
from __future__ import annotations

import sys
from pathlib import Path

PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PV2))
sys.path.insert(0, str(HERE))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import audio  # noqa: E402
import tk  # noqa: E402

OUT = HERE / "out"
BW, BH = 866, 573
COLS = 240


def cells_of(img: Image.Image, cols: int = COLS, thresh: int = 118):
    rows = max(2, int(round(cols * img.height / img.width)))
    flat = Image.new("RGBA", img.size, tk.BG + (255,))
    flat.alpha_composite(img)
    a = img.resize((cols, rows), Image.LANCZOS).getchannel("A")
    l = flat.convert("L").resize((cols, rows), Image.LANCZOS)
    A, L = a.load(), l.load()
    out = []
    for r in range(rows):
        for q in range(cols):
            if A[q, r] >= thresh:
                out.append(((q + 0.5) / cols, (r + 0.5) / rows, L[q, r] / 255.0))
    return out, rows


def paint(cells_uv, box, label, scale_k, fill, cx, alpha, feat):
    w, h = box
    img = Image.new("RGB", (w, h), tk.BG)
    d = ImageDraw.Draw(img)
    # 底纹点阵
    for yy in range(0, h, 11):
        for xx in range(0, w, 11):
            band = feat.bands[min(6, int((1 - yy / h) * 7))]
            k = 1.0 if ((xx // 11) + (yy // 11)) % 2 == 0 else 0.4
            a = int((16 + 100 * band) * k * 0.6)
            if a > 8:
                d.rectangle([xx, yy, xx + 1, yy + 1],
                            fill=tk.rgba(tk.lerp(tk.ME_MID, tk.ME_HI, band), a))
    if cells_uv:
        us = [c[0] for c in cells_uv]
        vs = [c[1] for c in cells_uv]
        uw, vh = max(us) - min(us), max(vs) - min(vs)
        sc = min((w * scale_k) / max(1e-6, uw), (h * fill) / max(1e-6, vh))
        ox = w * cx - (min(us) + uw / 2) * sc
        oy = h / 2 - (min(vs) + vh / 2) * sc
        for (u, v, lum) in cells_uv:
            px, py = ox + u * sc, oy + v * sc
            d.rectangle([px - 1.15, py - 1.15, px + 1.15, py + 1.15],
                        fill=tk.rgba(tk.lerp(tk.ME_MID, tk.ME_HI, lum), alpha))
    d.rectangle([0, 0, w - 1, h - 1], outline=tk.rgba(tk.ui(0.26), 190), width=1)
    f = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 15)
    d.text((12, 9), label, font=f, fill=tk.ui(0.78))
    return img


def main():
    src = tk.sprite_src("maid-right", "full")
    W, H = src.size
    feat = audio.at(15.0)

    # A 头肩：纵向切在笔记本上方（y 0~27%）。横向全用，保证不切两臂。
    #    笔记本在 y 16~30%，所以切到 27% 会把它的下缘露出来一点 —— 再往上收。
    A = src.crop((int(W * 0.04), 0, int(W * 0.96), int(H * 0.245)))
    a_cells, a_rows = cells_of(A)
    imA = paint(a_cells, (BW, BH),
                f"A 头肩  {A.size[0]}×{A.size[1]}  高/宽={A.height/A.width:.2f}  不含笔记本",
                scale_k=0.62, fill=0.86, cx=0.5, alpha=205, feat=feat)

    # B 全身（完整）
    bb = src.getchannel("A").getbbox()
    B = src.crop(bb)
    b_cells, b_rows = cells_of(B)
    imB = paint(b_cells, (BW, BH),
                f"B 全身  {B.size[0]}×{B.size[1]}  高/宽={B.height/B.width:.2f}  完整但小",
                scale_k=0.40, fill=0.94, cx=0.5, alpha=205, feat=feat)

    sheet = Image.new("RGB", (BW + 12, (BH + 12) * 2 + 12), (8, 8, 10))
    sheet.paste(imA, (6, 6))
    sheet.paste(imB, (6, 6 + BH + 12))
    out = OUT / "panel_AB.png"
    sheet.resize((BW * 3 // 5, sheet.height * 3 // 5), Image.LANCZOS).save(out)
    print(f"A 头肩 裁框 x[.04,.96] y[0,.245] -> {A.size}")
    print(f"B 全身 内容包围盒 {bb} -> {B.size}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()

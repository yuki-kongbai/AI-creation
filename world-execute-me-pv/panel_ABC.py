#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""三方案并排：把「半个书」这件事彻底解决。

量出的道具范围（原图 1066×2036）：
    笔记本 x[83,361]  y[333,854]
    笔     x[639,856] y[285,894]
两件都完整需要裁框 ≥ 773×894（高/宽 1.16）。
放进 866×573 面板 -> 她宽 495，两侧各空 185。

方案：
  A 两件完整  按 773×894 裁，居中放进面板（两侧留空）
  B 笔在画外  裁框左移，让笔记本被边框切开但**只占很小一角**；
              或者干脆右移更多让它完全在外
  C 只用上半  裁到笔记本上缘以上（y<333），但她会缺手部动作
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


def cells_of(img: Image.Image, cols: int = 240, thresh: int = 118):
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
    return out


def paint(cells_uv, label, scale_k, fill, cx, alpha, feat, grid=True):
    w, h = BW, BH
    img = Image.new("RGB", (w, h), tk.BG)
    d = ImageDraw.Draw(img)
    if grid:
        for yy in range(0, h, 11):
            for xx in range(0, w, 11):
                band = feat.bands[min(6, int((1 - yy / h) * 7))]
                k = 1.0 if ((xx // 11) + (yy // 11)) % 2 == 0 else 0.4
                a = int((16 + 100 * band) * k * 0.55)
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
    d.text((12, 9), label, font=f, fill=tk.ui(0.80))
    return img


def main():
    src = tk.sprite_src("maid-right", "full")
    W, H = src.size
    feat = audio.at(15.0)
    tiles = []

    # A 两件完整：x[83,856] y[0,894]
    A = src.crop((83, 0, 856, 894))
    tiles.append(paint(cells_of(A),
                       f"A 两件完整 {A.size[0]}×{A.size[1]} 高/宽{A.height/A.width:.2f}",
                       scale_k=0.98, fill=0.92, cx=0.5, alpha=205, feat=feat))

    # B 笔被完全排除：裁框右边界在笔之前 —— 但笔在她右侧，排不掉。
    #    所以反过来：裁框左边界越过笔记本右缘（x 361），只留身体。
    B = src.crop((361, 0, int(W * 0.995), 894))
    tiles.append(paint(cells_of(B),
                       f"B 排掉笔记本 x>{361} {B.size[0]}×{B.size[1]} 高/宽{B.height/B.width:.2f}",
                       scale_k=0.98, fill=0.92, cx=0.5, alpha=205, feat=feat))

    # C 上半身：切在笔记本上缘之上（y<333）
    C = src.crop((83, 0, 856, 333))
    tiles.append(paint(cells_of(C),
                       f"C 上半身 y<333 {C.size[0]}×{C.size[1]} 高/宽{C.height/C.width:.2f}",
                       scale_k=0.98, fill=0.80, cx=0.5, alpha=205, feat=feat))

    sheet = Image.new("RGB", (BW + 12, (BH + 12) * len(tiles) + 12), (8, 8, 10))
    for i, im in enumerate(tiles):
        sheet.paste(im, (6, 6 + i * (BH + 12)))
    out = OUT / "panel_ABC.png"
    sheet.resize((BW * 3 // 5, sheet.height * 3 // 5), Image.LANCZOS).save(out)
    print(f"-> {out}")


if __name__ == "__main__":
    main()

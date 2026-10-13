#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""右栏的她：分辨率对比。

两件事分开看：
  1. 形状对不对（比例）—— 上一轮已修，art_cells 偏差 0.2–2%
  2. **认不认得出是她** —— 这才是在看的问题

现在用的是舞台网格（57×27 格），横向上她只占约 45 格。
脸大约 15 格宽 —— 表情不可能看出来，四个裁切看着都像"一坨"。

这个脚本把「舞台格」（低分辨率）与「面板分辨率」（高分辨率）
并排画出来，看差多少。
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
import stage as S  # noqa: E402
import tk  # noqa: E402

OUT = HERE / "out"
BW, BH = 866, 573


def _f(sz, bold=False):
    p = "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"
    return ImageFont.truetype(p, sz)


def fit_into(box, cells, fill):
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    sc = min((box[0] * 0.74) / max(1, w), (box[1] * fill) / max(1, h))
    ox = box[0] / 2 - (min(xs) + w / 2) * sc
    oy = box[1] / 2 - (min(ys) + h / 2) * sc
    return [(ox + x * sc, oy + y * sc, l) for (x, y, l) in cells], sc


def paint(cells, sc, feat, label, radius_k=3.0):
    img = Image.new("RGB", (BW, BH), tk.BG)
    d = ImageDraw.Draw(img)
    rr = max(0.6, radius_k * sc)
    for (px, py, lum) in cells:
        v = min(1.0, lum + 0.5 * feat.kick)
        d.rectangle([px - rr, py - rr, px + rr, py + rr],
                    fill=tk.rgba(tk.lerp(tk.ME_MID, tk.ME_HI, v), 228))
    d.rectangle([0, 0, BW - 1, BH - 1], outline=tk.rgba(tk.ui(0.26), 190), width=1)
    d.text((12, 9), label, font=_f(14, True), fill=tk.ui(0.7))
    return img


def panel_cells(crop: str, cols: int, thresh: int = 118, cx: float = 0.5,
                cy: float = 0.5, span: float = 0.52):
    """按**面板分辨率**从立绘取格。

    cols 是横向格数；行数由立绘宽高比决定，所以格子是方的、她不会变形。
    这和舞台网格无关 —— 右栏本来就该按面板自己的分辨率来画。
    """
    src = tk.sprite_src("maid-right", crop)
    bb = src.getchannel("A").getbbox()
    if bb:
        src = src.crop(bb)
    rows = max(2, int(round(cols * src.height / src.width)))
    flat = Image.new("RGBA", src.size, tk.BG + (255,))
    flat.alpha_composite(src)
    a = src.resize((cols, rows), Image.LANCZOS).getchannel("A")
    l = flat.convert("L").resize((cols, rows), Image.LANCZOS)
    A, L = a.load(), l.load()
    cells = []
    for r in range(rows):
        for q in range(cols):
            if A[q, r] >= thresh:
                cells.append(((q + 0.5) / cols, (r + 0.5) / rows, L[q, r] / 255.0))
    return cells, rows


def main():
    feat = audio.at(15.0)

    # 方案 1：舞台格（现状）
    stage_cells = S.art_cells("maid-right", "bust")
    c1, sc1 = fit_into((BW, BH), stage_cells, 0.92)
    im1 = paint(c1, sc1, feat, f"A  舞台网格 57×27（她只占约 45 格）")

    # 方案 2：面板分辨率，格子
    tiles = [im1]
    for crop, cols, lab in (("bust", 150, "B  bust 150 列（面板分辨率）"),
                            ("bust", 260, "C  bust 260 列")):
        pc, rows = panel_cells(crop, cols)
        # 归一化坐标 -> 面板像素
        sc = min(BW * 0.74, BH * 0.92 / 1.0)
        px = [(BW / 2 + (x - 0.5) * sc, BH / 2 + (y - 0.5) * sc, l)
              for (x, y, l) in pc]
        im = paint(px, max(0.35, 0.74 * BW / cols / 2), feat,
                   f"{lab}  共 {cols}×{rows} 格")
        tiles.append(im)

    W, H = BW, BH
    sheet = Image.new("RGB", (W + 12, (H + 12) * len(tiles) + 12), (8, 8, 10))
    for i, im in enumerate(tiles):
        sheet.paste(im, (6, 6 + i * (H + 12)))
    out = OUT / "res_compare.png"
    sheet.resize((W * 3 // 5, sheet.height * 3 // 5), Image.LANCZOS).save(out)
    print(f"-> {out}")


if __name__ == "__main__":
    main()

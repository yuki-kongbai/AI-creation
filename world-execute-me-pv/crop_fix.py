#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""裁切方案对比：手写比例 vs 内容包围盒。

手写比例（现在的 bust/upper/face）左边界落在内容上，把笔记本切了一半。
内容包围盒方案不会有这个问题 —— 让内容自己定义裁切框。

两种收尾方式：
  B 全包围盒      完整保留（含笔记本），但她在面板里会小一圈
  C 裁到躯干      笔记本切在框外，但框边**羽化**，读起来是"画外"而不是"切一半"
"""
from __future__ import annotations

import sys
from pathlib import Path

PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PV2))
sys.path.insert(0, str(HERE))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import tk  # noqa: E402

OUT = HERE / "out"
BW, BH = 866, 573
PANEL = (BW, BH)


def content_crop(pad_frac: float = 0.02):
    """整个立绘的内容包围盒 + 一点留白。"""
    src = tk.sprite_src("maid-right", "full")
    bb = src.getchannel("A").getbbox()
    pad = int(max(src.size) * pad_frac)
    x0 = max(0, bb[0] - pad)
    y0 = max(0, bb[1] - pad)
    x1 = min(src.width, bb[2] + pad)
    y1 = min(src.height, bb[3] + pad)
    return src.crop((x0, y0, x1, y1)), (x0, y0, x1, y1)


def torso_crop(center_frac=(0.56, 0.34), half=(0.30, 0.30)):
    """裁到躯干：左右按比例切，但**框边羽化**，读起来是画外不是切一半。"""
    src = tk.sprite_src("maid-right", "full")
    cx, cy = center_frac[0] * src.width, center_frac[1] * src.height
    hw, hh = half[0] * src.width, half[1] * src.height
    box = (int(max(0, cx - hw)), int(max(0, cy - hh)),
           int(min(src.width, cx + hw)), int(min(src.height, cy + hh)))
    return src.crop(box), box


def feather(img: Image.Image, k: int = 26) -> Image.Image:
    """四周羽化 alpha，让被裁的对象读起来像"延伸到画外"。"""
    from PIL import ImageFilter
    a = img.getchannel("A")
    inner = Image.new("L", img.size, 0)
    ImageDraw.Draw(inner).rectangle([k, k, img.width - k - 1, img.height - k - 1],
                                    fill=255)
    inner = inner.filter(ImageFilter.GaussianBlur(k * 0.6))
    out = img.copy()
    out.putalpha(Image.composite(a, Image.new("L", img.size, 0), inner))
    return out


def her_tiles(cols: int = 240, thresh: int = 118):
    def cells_of(img: Image.Image):
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
    return cells_of


def paint(cells_uv, box, label, scale_k=0.46, fill=0.78, cx=0.68, alpha=190):
    w, h = box
    img = Image.new("RGB", (w, h), tk.BG)
    d = ImageDraw.Draw(img)
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
    d.text((12, 9), label, font=f, fill=tk.ui(0.75))
    return img


def main():
    cof = her_tiles(240)
    tiles = []

    # A 现状
    a = tk.sprite_src("maid-right", "bust")
    ca, _ = cof(a)
    tiles.append(paint(ca, PANEL, "A  现状：手写比例 bust（笔记本切一半）"))

    # B 内容包围盒
    b, bx = content_crop()
    cb, _ = cof(b)
    tiles.append(paint(cb, PANEL, f"B  内容包围盒 {b.size[0]}×{b.size[1]}（完整）"))

    # C 躯干 + 羽化
    c, cx = torso_crop()
    cf = feather(c)
    cc, _ = cof(cf)
    tiles.append(paint(cc, PANEL, f"C  躯干 {c.size[0]}×{c.size[1]} + 框边羽化"))

    W, H = PANEL
    sheet = Image.new("RGB", (W + 12, (H + 12) * len(tiles) + 12), (8, 8, 10))
    for i, im in enumerate(tiles):
        sheet.paste(im, (6, 6 + i * (H + 12)))
    out = OUT / "crop_fix.png"
    sheet.resize((W * 3 // 5, sheet.height * 3 // 5), Image.LANCZOS).save(out)
    print(f"内容包围盒 = {bx}")
    print(f"躯干裁框   = {cx}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()

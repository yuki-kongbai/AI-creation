#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""放大看若干关键帧（每格接近原尺寸），用来判断界面细节。"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FRAMES = HERE / "out" / "frames"
OUT = HERE / "out" / "key.png"


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else "p"
    want = [float(x) for x in (sys.argv[2].split(",") if len(sys.argv) > 2
                               else ["1.5", "5.0", "8.8", "12.6", "16.0", "22.5"])]
    cols = 3
    TW = 420
    PAD, LBL = 6, 16
    th = int(TW * 680 / 420)
    rows = (len(want) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (TW + PAD) + PAD,
                              rows * (th + LBL + PAD) + PAD), (8, 8, 10))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 12)
    except OSError:
        f = ImageFont.load_default()

    for i, t in enumerate(want):
        n = int(round(t * 24))
        p = FRAMES / f"{prefix}{n:05d}.png"
        if not p.exists():
            print(f"  缺 {p.name}")
            continue
        im = Image.open(p).convert("RGB").resize((TW, th), Image.LANCZOS)
        c, r = i % cols, i // cols
        x = PAD + c * (TW + PAD)
        y = PAD + r * (th + LBL + PAD)
        sheet.paste(im, (x, y))
        d.text((x + 3, y + th + 2), f"t = {t:.2f}s", font=f, fill=(150, 180, 220))

    sheet.save(OUT)
    print(f"{len(want)} 帧 -> {OUT}  {sheet.size}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把预览帧拼成联系表，用来判断动画节奏。"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FRAMES = HERE / "out" / "frames"
OUT = HERE / "out" / "sheet.png"

COLS = 8
TW = 210
PAD = 4
LBL = 15


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else "p"
    files = sorted(FRAMES.glob(f"{prefix}*.png"))
    if not files:
        print("没有帧")
        return
    th = int(TW * 680 / 420)
    rows = (len(files) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * (TW + PAD) + PAD,
                             rows * (th + LBL + PAD) + PAD), (10, 10, 12))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 11)
    except OSError:
        f = ImageFont.load_default()

    for i, p in enumerate(files):
        im = Image.open(p).convert("RGB").resize((TW, th), Image.LANCZOS)
        c, r = i % COLS, i // COLS
        x = PAD + c * (TW + PAD)
        y = PAD + r * (th + LBL + PAD)
        sheet.paste(im, (x, y))
        n = int(p.stem[len(prefix):]) if p.stem[len(prefix):].isdigit() else i
        d.text((x + 2, y + th + 1), f"{n / 24:.2f}s", font=f, fill=(140, 170, 210))

    sheet.save(OUT)
    print(f"{len(files)} 帧 -> {OUT}  {sheet.size}")


if __name__ == "__main__":
    main()

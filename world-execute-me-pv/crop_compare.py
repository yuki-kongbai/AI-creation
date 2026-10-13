#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""右栏裁切实验（art_cells 修好之后重做）。

之前四张都是扁的，因为 art_cells 把立绘拉伸了 2.4 倍，看不出裁切本身的差别。
现在比例对了，才真正能比较。

关键认识：右栏面板 866×573（比例 1.51），
  · full  全身 1.91（高瘦）—— 竖着放进面板天然合适
  · bust  胸像 1.21（近方）—— 放进去要么很宽、要么上下留空
  · upper 头肩 0.89（扁） —— 横向铺满，高度只占一半
所以真正该选的是 full 或 upper，bust 在数学上就别扭。
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
import dense_scene as ds  # noqa: E402
import right_panel as rp  # noqa: E402
import stage as S  # noqa: E402
import tk  # noqa: E402

OUT = HERE / "out"
BOX = (0, 0, 866, 573)
CROPS = [("full", 0.86), ("bust", 0.92), ("upper", 0.92), ("face", 0.98)]


def draw_raw(crop: str, fill: float, feat, phase="idle"):
    """按格点原样画（不改 right_panel 的缩放），只检验形状。"""
    img = Image.new("RGB", (BOX[2], BOX[3]), tk.BG)
    d = ImageDraw.Draw(img)
    cells = S.art_cells("maid-right", crop)
    if not cells:
        return img
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    sc = min((BOX[2] * 0.72) / max(1, w), (BOX[3] * fill) / max(1, h))
    ox = BOX[2] / 2 - (min(xs) + w / 2) * sc
    oy = BOX[3] / 2 - (min(ys) + h / 2) * sc
    for (x, y, lum) in cells:
        px, py = ox + x * sc, oy + y * sc
        v = min(1.0, lum + 0.5 * feat.kick)
        rr = max(1.0, 3.2 * sc)
        d.rectangle([px - rr, py - rr, px + rr, py + rr],
                    fill=tk.rgba(tk.lerp(tk.ME_MID, tk.ME_HI, v), 226))
    d.rectangle([0, 0, BOX[2] - 1, BOX[3] - 1],
                outline=tk.rgba(tk.ui(0.28), 200), width=1)
    d.text((12, 8), f"crop={crop}  fill={fill}", font=_f(13), fill=tk.ui(0.6))
    return img


def _f(sz):
    return ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", sz)


def main():
    scene = ds.load(HERE / "content" / "scene08.json")
    feat = audio.at(15.0)
    tiles = [(c, draw_raw(c, fl, feat)) for c, fl in CROPS]
    W, H = BOX[2], BOX[3]
    sheet = Image.new("RGB", (W * 2 + 18, (H + 24) * 2 + 18), (8, 8, 10))
    for i, (lab, im) in enumerate(tiles):
        c, r = i % 2, i // 2
        x, y = 6 + c * (W + 6), 6 + r * (H + 24)
        sheet.paste(im, (x, y))
        lab2 = {"full": "全身 1.91", "bust": "胸像 1.21",
                "upper": "头肩 0.89", "face": "脸 0.79"}[lab]
        ImageDraw.Draw(sheet).text((x + 4, y + H + 4), f"{lab}  {lab2}",
                                   font=_f(16), fill=(150, 180, 220))
    out = OUT / "crop_compare.png"
    sheet.resize((sheet.width * 3 // 5, sheet.height * 3 // 5),
                 Image.LANCZOS).save(out)
    print(f"-> {out}")


if __name__ == "__main__":
    main()

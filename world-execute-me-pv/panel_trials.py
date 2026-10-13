#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""右栏布局实验：直接渲染几种方案，肉眼看哪个对。

不再推导公式 —— 已经推错三次了。直接把候选画出来。

关键发现：立绘源图有大片空白（画布 1066×2036 但人物没那么高），
所以「裁切尺寸」不等于「人物尺寸」。要用 **alpha 包围盒** 来算比例。
"""
from __future__ import annotations

import sys
from pathlib import Path

PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PV2))
sys.path.insert(0, str(HERE))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import dense_scene as ds  # noqa: E402
import right_panel as rp  # noqa: E402
import stage as S  # noqa: E402
import tk  # noqa: E402
import audio  # noqa: E402

OUT = HERE / "out"
BOX = (0, 0, 866, 573)


def alpha_bbox(kind: str, crop: str):
    src = tk.sprite_src(kind, crop)
    bb = src.getchannel("A").getbbox()
    return src, bb


def main():
    scene = ds.load(HERE / "content" / "scene08.json")
    feat = audio.at(15.0)

    print("立绘 alpha 包围盒（人物真实占用的范围）：")
    for crop in ("full", "bust", "upper", "face"):
        src, bb = alpha_bbox("maid-right", crop)
        if bb is None:
            print(f"  {crop}: 空")
            continue
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        print(f"  {crop:<6} 画布 {src.size[0]:>4}×{src.size[1]:<4} "
              f"人物 {w:>4}×{h:<4}  人物高/宽={h/w:.3f}  "
              f"占画布 {w/src.width*100:.0f}%×{h/src.height*100:.0f}%")

    # 四种方案，都用同一时刻，只看她
    trials = [
        ("A 现状（bust 硬映射）", dict(crop="bust", fill=1.00)),
        ("B bust 按人物比例 fit",  dict(crop="bust", fill=0.82)),
        ("C upper 按人物比例 fit", dict(crop="upper", fill=0.86)),
        ("D face 按人物比例 fit",  dict(crop="face", fill=0.92)),
    ]
    tiles = []
    for lab, cfg in trials:
        img = rp.draw(BOX, 15.0, feat, "idle",
                      S.art_cells("maid-right", cfg["crop"]), {})
        tiles.append((lab, img))

    W, H = BOX[2], BOX[3]
    sheet = Image.new("RGB", (W * 2 + 18, (H + 22) * 2 + 18), (8, 8, 10))
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 16)
    for i, (lab, im) in enumerate(tiles):
        c, r = i % 2, i // 2
        x, y = 6 + c * (W + 6), 6 + r * (H + 22)
        sheet.paste(im, (x, y))
        d.text((x + 4, y + H + 3), lab, font=f, fill=(150, 180, 220))
    out = OUT / "panel_trials.png"
    sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS).save(out)
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""think_panel.py —— 思考过程面板（重写版）。

用户这一轮的三条要求都落在这里：
  · **长一点**     每句展开成 4–6 个短句，逐行流出，写完停一拍
  · **贴合对话**   开头先复述"你"刚说的那句（think_text.think_lines 负责）
  · **字体为蓝色** 全部用 link 蓝 / brand 蓝，不用灰白
"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

import think_text as TT
import tk

from res import S

BLUE = getattr(tk, "LINK", None) or (0x7A, 0xAA, 0xFF)
BLUE2 = getattr(tk, "BRAND", None) or (0x56, 0x86, 0xFE)


def _mono(sz: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    import res
    p = "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"
    return ImageFont.truetype(p, res.px(sz))


def _cjk(sz: int):
    import res
    try:
        return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", res.px(sz))
    except OSError:
        return _mono(sz)


PER_LINE = 1.25          # 每行思考文本停留多久（秒）—— 比上一版慢，所以更长


def draw_think(img: Image.Image, t: float, feat, lyric: str, zh: str,
               ask: str = "", prev_ask: str = "", t0: float = 0.0,
               dur: float = 1.0) -> None:
    import res
    d = res.SDraw(ImageDraw.Draw(img))
    w, h = (img.size[0] / S, img.size[1] / S)   # 除回 1× 设计坐标
    lines = TT.think_lines(lyric, ask, zh, prev_ask)
    if not lines:
        return

    d.text((16, 14), "THINKING", font=_mono(12, True), fill=tk.rgba(BLUE2, 245))
    d.text((16, 32), "no image for this line · reasoning only",
           font=_mono(10), fill=tk.rgba(BLUE, 150))

    f = _cjk(13)
    # 在这一句的时长里把几行依次亮出来，**亮完就留着**（不循环）。
    # 上一版按固定 6.25s 循环，而每句歌词只有 1 秒左右，
    # 结果观众永远只看到第一行 —— 那就不叫"长一点"了。
    u = min(1.0, max(0.0, (t - t0) / max(0.45, dur * 0.85)))
    shown = 1 + int(u * (len(lines) - 1))
    shown = max(1, min(len(lines), shown))

    y0_top = 56
    step = 21
    maxrows = max(1, int((h - 78 - y0_top) // step))
    first = max(0, shown - maxrows)
    for i in range(first, shown):
        s_ = lines[i]
        y = y0_top + (i - first) * step
        if y > h - 72:
            break
        if i == shown - 1 and u < 1.0:
            # 最新一行逐字
            frac = (u * (len(lines) - 1)) % 1.0 if len(lines) > 1 else u
            n = max(1, int(len(s_) * min(1.0, frac / 0.5)))
            txt = s_[:n]
            d.text((16, y), txt, font=f, fill=tk.rgba(BLUE, 242))
            if int(t * 5) % 2 == 0:
                cx = 16 + d.textlength(txt, font=f)
                d.rectangle([cx + 1, y + 3, cx + 8, y + 17], fill=tk.rgba(BLUE, 242))
        else:
            age = (shown - 1 - i) / max(1, len(lines))
            d.text((16, y), s_, font=f,
                   fill=tk.rgba(BLUE, int(225 * (1 - age * 0.55))))

    # 检索痕迹
    d.line([16, h - 58, w - 16, h - 58], fill=tk.rgba(BLUE, 70))
    y2 = h - 50
    calls = [("recall(you)", f"{int(t*7)%97} hits"),
             ("match_shape", "none"),
             ("read(lyric)", (lyric[:20] if lyric else "-"))]
    for name, val in calls:
        d.text((16, y2), "·", font=_mono(11), fill=tk.rgba(BLUE2, 210))
        d.text((30, y2), name, font=_mono(11), fill=tk.rgba(BLUE, 185))
        d.text((152, y2), val, font=_mono(11), fill=tk.rgba(BLUE, 120))
        y2 += 16

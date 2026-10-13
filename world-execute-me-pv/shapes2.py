#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""shapes2.py —— 具象形状（要能认出来）。

用户说「左边用户说你是小猫吗，右边就出小猫图像」——
所以这些形状必须**一眼认得出**，不能只是抽象的几何。

做法：用参数方程画**轮廓线**（不是随手撒点），再沿轮廓均匀重采样。
这样点连线就是干净的线稿，形状可辨。

    猫  ：头 + 两只三角耳 + 身体 + 尾巴
    茄子：上窄下圆的长椭圆 + 蒂
    番茄：圆 + 顶部星形叶
    鸟  ：身体 + 喙 + 尾羽      （备用）
    花  ：五瓣 + 花心           （备用）
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

TAU = 6.283185307179586

sys.path.insert(0, r"D:\大肥鱼（deepseek）\whale-pv2")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import field


def _cat_outline() -> np.ndarray:
    """一只坐着的猫的轮廓（多段拼合，单位约 [0,1]²）。"""
    segs = []
    # 左耳（三角）
    segs.append(np.array([[0.30, 0.34], [0.34, 0.10], [0.47, 0.30]]))
    # 头顶到右耳
    t = np.linspace(0, 1, 40)
    segs.append(np.stack([0.34 + 0.36 * t, 0.26 - 0.06 * np.sin(t * np.pi)], axis=1))
    # 右耳
    segs.append(np.array([[0.55, 0.29], [0.68, 0.09], [0.72, 0.33]]))
    # 右脸颊到身体
    segs.append(np.array([[0.72, 0.33], [0.80, 0.48], [0.86, 0.62],
                          [0.88, 0.80], [0.86, 0.92]]))
    # 底边
    t = np.linspace(0, 1, 40)
    segs.append(np.stack([0.86 - 0.62 * t, 0.92 + 0.02 * np.sin(t * np.pi)], axis=1))
    # 左侧回上去
    segs.append(np.array([[0.24, 0.92], [0.22, 0.74], [0.26, 0.56],
                          [0.30, 0.44], [0.30, 0.34]]))
    # 尾巴（一段弧，接在右侧）
    t = np.linspace(0, 1, 40)
    tail = np.stack([0.88 + 0.14 * np.sin(t * np.pi * 0.9),
                     0.90 - 0.42 * t + 0.10 * np.sin(t * np.pi * 1.6)], axis=1)
    segs.append(tail)
    # 眼睛两点（单独的小段，不连进轮廓）
    return segs


def sh_cat(w, h) -> np.ndarray:
    """小猫 —— 轮廓 + 两只眼睛。"""
    segs = _cat_outline()
    allp = np.concatenate(segs, axis=0)
    mn, mx = allp.min(axis=0), allp.max(axis=0)
    span = np.maximum(mx - mn, 1e-9)
    n_seg = len(segs) + 1                      # 最后一段给眼睛
    per = max(4, field.NP // n_seg)
    out = []
    for s in segs:
        out.append(field._resample((s - mn) / span, per))
    # 眼睛：两个小圆，各占半段
    e = []
    for cx, cy in ((0.40, 0.40), (0.60, 0.40)):
        a = np.linspace(0, TAU, per // 2, endpoint=False)
        e.append(np.stack([cx + 0.022 * np.cos(a), cy + 0.022 * np.sin(a)], axis=1))
    out.append(np.concatenate(e, axis=0))
    p = np.concatenate(out, axis=0)
    p = (p - p.min(axis=0)) / np.maximum(p.max(axis=0) - p.min(axis=0), 1e-9)
    if len(p) < field.NP:
        p = np.concatenate([p, p[:field.NP - len(p)]], axis=0)
    p = p[:field.NP]
    # 轻微内缩，留边
    p = 0.05 + p * 0.90
    return field._norm(p, w, h, 0.06)


def sh_eggplant(w, h) -> np.ndarray:
    """茄子 —— 上窄下圆的**泪滴形**，带蒂。

    之前写成椭圆了：
 = 1 + 0.12*cos(2a) 只是轻微起伏，
    归一化之后就成一个蛋，认不出是茄子。改用真正的泪滴参数式：
    上端收成一个尖，下端鼓成球。
    """
    n = field.NP - 34
    a = np.linspace(0, TAU, n, endpoint=False)
    # 泪滴：把圆的 y 往上拉，越往上越窄
    wide = 0.30 * (1.0 - 0.55 * np.clip(np.sin(a), 0, 1))   # 上半收窄
    x = 0.5 + wide * np.cos(a)
    y = 0.60 - 0.40 * np.sin(a)
    body = np.stack([x, y], axis=1)
    # 蒂：一个向上收的小三角，接在顶端
    t = np.linspace(0, 1, 34)
    stem = np.stack([0.5 + 0.055 * np.sin(t * np.pi * 1.2),
                     0.21 - 0.10 * t], axis=1)
    p = np.concatenate([body, stem], axis=0)[:field.NP]
    p = (p - p.min(axis=0)) / np.maximum(p.max(axis=0) - p.min(axis=0), 1e-9)
    p = 0.05 + p * 0.90
    return field._norm(p, w, h, 0.06)


def sh_tomato(w, h) -> np.ndarray:
    """番茄 —— 圆 + 顶部一片**大而清楚的五角叶**。

    之前叶子太小（半径 0.13 的一小撮点），归一化后几乎看不见。
    现在叶子的尺寸和果实相当，形状能认出来。
    """
    n_body = field.NP - 90
    a = np.linspace(0, TAU, n_body, endpoint=False)
    # 略扁的圆，底部稍微收一点更像番茄
    body = np.stack([0.5 + 0.30 * np.cos(a),
                     0.60 + 0.27 * np.sin(a) * (1 - 0.10 * np.sin(a))], axis=1)
    # 五角叶：沿五角星的轮廓走一遍
    star = []
    for k in range(5):
        ang = -np.pi / 2 + k * TAU / 5
        # 每瓣：从花心出去，再收回来
        for u in np.linspace(0.15, 1.0, 9):
            rr = 0.22 * u
            star.append([0.5 + rr * np.cos(ang),
                         0.30 - rr * np.sin(ang) * 0.55])
        for u in np.linspace(1.0, 0.15, 9):
            rr = 0.22 * u
            ang2 = ang + TAU / 10
            star.append([0.5 + rr * np.cos(ang2) * 0.55,
                         0.30 - rr * np.sin(ang2) * 0.35])
    p = np.concatenate([body, np.array(star)], axis=0)[:field.NP]
    p = (p - p.min(axis=0)) / np.maximum(p.max(axis=0) - p.min(axis=0), 1e-9)
    p = 0.05 + p * 0.90
    return field._norm(p, w, h, 0.06)


def sh_bird(w, h) -> np.ndarray:
    """小鸟 —— 身体 + 喙 + 尾羽。"""
    a = np.linspace(0, TAU, field.NP - 60, endpoint=False)
    body = np.stack([0.52 + 0.26 * np.cos(a), 0.58 + 0.22 * np.sin(a)], axis=1)
    t = np.linspace(0, 1, 30)
    beak = np.stack([0.26 - 0.14 * t, 0.50 + 0.02 * np.sin(t * np.pi)], axis=1)
    t2 = np.linspace(0, 1, 30)
    tail = np.stack([0.76 + 0.18 * t2, 0.52 - 0.16 * t2 + 0.06 * np.sin(t2 * np.pi)],
                    axis=1)
    p = np.concatenate([body, beak, tail], axis=0)[:field.NP]
    p = (p - p.min(axis=0)) / np.maximum(p.max(axis=0) - p.min(axis=0), 1e-9)
    p = 0.05 + p * 0.90
    return field._norm(p, w, h, 0.06)


def sh_flower(w, h) -> np.ndarray:
    """花 —— 五瓣 + 花心。"""
    per = field.NP // 6
    out = []
    for k in range(5):
        ang = -np.pi / 2 + k * TAU / 5
        cx, cy = 0.5 + 0.19 * np.cos(ang), 0.5 + 0.19 * np.sin(ang)
        a = np.linspace(0, TAU, per, endpoint=False)
        out.append(np.stack([cx + 0.14 * np.cos(a), cy + 0.14 * np.sin(a)], axis=1))
    a = np.linspace(0, TAU, field.NP - 5 * per, endpoint=False)
    out.append(np.stack([0.5 + 0.07 * np.cos(a), 0.5 + 0.07 * np.sin(a)], axis=1))
    p = np.concatenate(out, axis=0)[:field.NP]
    return field._norm(p, w, h, 0.06)


EXTRA = {"cat": sh_cat, "eggplant": sh_eggplant, "tomato": sh_tomato,
         "bird": sh_bird, "flower": sh_flower}

if __name__ == "__main__":
    import sys
    from pathlib import Path
    HERE = Path(__file__).resolve().parent
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, r"D:\大肥鱼（deepseek）\whale-pv2")
    import audio
    import tk
    from PIL import Image, ImageDraw, ImageFont
    field.SHAPES.update(EXTRA)
    field.set_her(np.load(HERE / "cache" / "her_points.npy"))
    W, H = 866, 573
    fe = audio.at(80.0)
    names = list(EXTRA)
    TW, TH = 430, 285
    sheet = Image.new("RGB", (len(names) * (TW + 6) + 6, TH + 24), (8, 8, 10))
    f = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 13)
    for i, nm in enumerate(names):
        im = Image.new("RGB", (W, H), tk.BG)
        field.draw_cloud(im, field.shape_points(nm, W, H), 80.0, fe, shape=nm)
        sheet.paste(im.resize((TW, TH), Image.LANCZOS), (6 + i * (TW + 6), 6))
        ImageDraw.Draw(sheet).text((9 + i * (TW + 6), TH + 8), nm, font=f,
                                   fill=(150, 180, 220))
    out = HERE / "out" / "shapes2.png"
    sheet.save(out)
    print("->", out)

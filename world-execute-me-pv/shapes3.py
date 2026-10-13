#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""shapes3.py —— 重画茄子，加上 ♂♀ 与 S/M。

用户这一轮的三个要求：
  · 「茄子图像一点都不像」        -> 按真实茄子的剖面重画
  · 「男和女应该用符号 ♂♀ 表示」  -> gender 形状改成两个性别符号
  · 「s 和 m 也应该是图像 S 和 M」 -> role 形状改成字母 S 与 M

符号类形状统一走 `_text_points`（把字形栅格化后沿笔画边缘采样），
这样它和别的形状一样是"一团点"，可以逐点插值。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, r"D:\大肥鱼（deepseek）\whale-pv2")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import field  # noqa: E402

TAU = 6.283185307179586

# 带 ♂ ♀ 的字体。Consolas 没有这两个字形，得用符号字体。
SYM_FONTS = [
    "C:/Windows/Fonts/seguisym.ttf",
    "C:/Windows/Fonts/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def glyph_points(text: str, n: int, font_px: int = 190,
                 fonts: list[str] | None = None) -> np.ndarray:
    """把一段字形栅格化，沿**笔画边缘**采样 n 个点。

    和 field._text_points 同样的思路，但支持指定字体
    （♂ ♀ 在等宽字体里没有）。
    """
    for fp in (fonts or ["C:/Windows/Fonts/consolab.ttf"]):
        try:
            f = ImageFont.truetype(fp, font_px)
        except OSError:
            continue
        img = Image.new("L", (10, 10))
        d = ImageDraw.Draw(img)
        box = d.textbbox((0, 0), text, font=f)
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        W, H = box[2] - box[0] + 24, box[3] - box[1] + 24
        img = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(img)
        d.text((12 - box[0], 12 - box[1]), text, font=f, fill=255)
        a = np.asarray(img)
        m = a > 110
        if m.sum() < 40:
            continue
        e = m.copy()
        e[1:, :] &= m[:-1, :]
        e[:-1, :] &= m[1:, :]
        e[:, 1:] &= m[:, :-1]
        e[:, :-1] &= m[:, 1:]
        edge = m & ~e
        ys, xs = np.nonzero(edge if edge.sum() > n else m)
        rng = np.random.default_rng(11)
        idx = rng.choice(len(xs), size=n, replace=len(xs) < n)
        p = np.stack([xs[idx], ys[idx]], axis=1).astype(np.float64)
        return (p - p.min(axis=0)) / np.maximum(p.max(axis=0) - p.min(axis=0), 1e-9)
    return np.zeros((n, 2))


def _fit(p: np.ndarray, w: int, h: int, margin: float = 0.05) -> np.ndarray:
    """把形状放进 [0,1]²，**等比缩放**。

    不能两个轴各自归一化 —— 那会把窄高的茄子拉成宽扁的椭圆
    （实测茄子因此完全认不出）。等比 + 居中才对。
    """
    p = np.asarray(p, dtype=np.float64)
    p = p - p.min(axis=0)
    span = np.maximum(p.max(axis=0), 1e-9)
    k = 1.0 / float(max(span))
    p = p * k                                   # 等比
    p = p + (1.0 - span * k) / 2                # 居中
    p = 0.03 + p * 0.94
    return field._norm(p, w, h, margin)


# ------------------------------------------------------------------ 茄子
def sh_eggplant(w, h) -> np.ndarray:
    """茄子 —— 用**显式轮廓**画，不再用参数式。

    上一版想用参数方程描述剖面，结果退化成了两段弧（看不出是什么）。
    改成手写一圈控制点再按弧长重采样，形状是确定的、可验证的。

    真茄子的三个特征都写进轮廓里：
      1. 顶部窄、**下三分之一最粗** 2. 顶端一片萼（叶状帽）
      3. 中轴微微弯
    """
    # 一圈控制点（顺时针，从萼顶开始）
    ctrl = np.array([
        [0.500, 0.055],   # 萼顶 / 小柄
        [0.462, 0.095], [0.440, 0.140],         # 萼左侧
        [0.392, 0.185], [0.352, 0.250],         # 肩
        [0.318, 0.350], [0.300, 0.470],         # 上段（收窄）
        [0.296, 0.590], [0.312, 0.690],         # 最粗处（下三分之一）
        [0.348, 0.782], [0.402, 0.862],         # 收底
        [0.462, 0.918], [0.512, 0.940],         # 底
        [0.566, 0.918], [0.622, 0.862],
        [0.676, 0.782], [0.712, 0.690],
        [0.726, 0.590], [0.722, 0.470],
        [0.706, 0.350], [0.672, 0.250],
        [0.630, 0.185], [0.578, 0.140],
        [0.548, 0.095], [0.512, 0.055],
    ])
    # 平滑：三次样条太麻烦，用移动平均把折角磨圆
    for _ in range(2):
        ctrl = np.concatenate([ctrl[-1:], ctrl, ctrl[:1]], axis=0)
        ctrl = (ctrl[:-2] + 2 * ctrl[1:-1] + ctrl[2:]) / 4.0
    # 闭合成环并重采样
    ring = np.concatenate([ctrl, ctrl[:1]], axis=0)
    body = field._resample(ring, int(field.NP * 0.80))
    # 萼：顶端一片五瓣叶状帽，用小圆环表示
    n = field.NP - len(body)
    tt = np.linspace(0, TAU, n, endpoint=False)
    petal = 1.0 + 0.34 * np.cos(tt * 5)
    calyx = np.stack([0.500 + 0.115 * petal * np.cos(tt),
                      0.118 + 0.042 * petal * np.sin(tt)], axis=1)
    p = np.concatenate([body, calyx], axis=0)[:field.NP]
    return _fit(p, w, h, 0.05)


# ------------------------------------------------------------------ 性别 / 角色
def sh_gender(w, h) -> np.ndarray:
    """切换性别 —— ♀ 与 ♂ 两个符号并排。

    用户要求：「男和女应该用符号 ♂ ♀ 表示」。
    """
    half = field.NP // 2
    a = glyph_points("\u2640", half, 210, SYM_FONTS)   # ♀
    b = glyph_points("\u2642", field.NP - half, 210, SYM_FONTS)  # ♂
    # ♀ 放左、♂ 放右
    a = np.stack([a[:, 0] * 0.40, a[:, 1]], axis=1)
    b = np.stack([0.56 + b[:, 0] * 0.40, b[:, 1]], axis=1)
    p = np.concatenate([a, b], axis=0)
    return _fit(p, w, h, 0.06)


def sh_role(w, h) -> np.ndarray:
    """切换角色 —— 字母 S 与 M。

    用户要求：「s 和 m 也应该是图像 S 和 M」。
    """
    half = field.NP // 2
    a = glyph_points("S", half, 220, ["C:/Windows/Fonts/ariblk.ttf",
                                      "C:/Windows/Fonts/arialbd.ttf",
                                      "C:/Windows/Fonts/consolab.ttf"])
    b = glyph_points("M", field.NP - half, 220, ["C:/Windows/Fonts/ariblk.ttf",
                                                 "C:/Windows/Fonts/arialbd.ttf",
                                                 "C:/Windows/Fonts/consolab.ttf"])
    a = np.stack([a[:, 0] * 0.40, a[:, 1]], axis=1)
    b = np.stack([0.56 + b[:, 0] * 0.40, b[:, 1]], axis=1)
    p = np.concatenate([a, b], axis=0)
    return _fit(p, w, h, 0.06)


EXTRA3 = {"eggplant": sh_eggplant, "gender": sh_gender, "role": sh_role}


if __name__ == "__main__":
    import audio
    import tk
    from PIL import Image as I

    field.SHAPES.update(EXTRA3)
    field.set_her(np.load(Path(__file__).resolve().parent /
                          "cache" / "her_points.npy"))
    W, H = 866, 543
    fe = audio.at(75.0)
    names = ["eggplant", "gender", "role"]
    TW, TH = 620, 389
    sheet = I.new("RGB", (len(names) * (TW + 6) + 6, TH + 24), (8, 8, 10))
    f = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 14)
    for i, nm in enumerate(names):
        im = I.new("RGB", (W, H), tk.BG)
        field.draw_cloud(im, field.shape_points(nm, W, H), 75.0, fe, shape=nm)
        sheet.paste(im.resize((TW, TH), I.LANCZOS), (6 + i * (TW + 6), 6))
        ImageDraw.Draw(sheet).text((9 + i * (TW + 6), TH + 8), nm, font=f,
                                   fill=(150, 180, 220))
    out = Path(__file__).resolve().parent / "out" / "shapes3.png"
    sheet.save(out)
    print("->", out)

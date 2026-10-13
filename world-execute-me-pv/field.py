#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""field.py —— 点与线的场。取代代码栏。

核心想法：
    **她本身就是一团点。** 歌词唱什么形状，她的点就慢慢走成什么形状 ——
    "If I'm a circle" 她的点聚成同心圆；"If I'm a sine wave" 走成正弦波；
    "If I'm a set of points" 散成点阵；"EXECUTION" 排成字。

    所以「内容对上词」不是靠旁边配一张图，而是**她自己在变形**。

为什么这样做（而不是像上一版那样换图）：
    · 上一版是"代码栏 / 形态"硬切，观众看到的是两张图在换，不自然
    · 点云变形是**连续的** —— 每个点沿直线走到新位置，没有切换
    · 而且点线本身是极简的，不会和左边的对话窗口抢

所有形状都产出**固定 N 个点**，所以任意两个形状可以逐点插值。
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import tk

try:
    from res import S as _S
except Exception:
    _S = 1.0

TAU = 6.283185307179586

NP = 1400           # 点的个数。所有形状都用这个数，才能逐点插值。
                    # 720 时曲线有折角，1400 才够平滑（用户要求图像再精细一点）


# ------------------------------------------------------------------ 工具
def _norm(pts: np.ndarray, w: int, h: int, margin: float = 0.06,
          fit: bool = False) -> np.ndarray:
    """把「设计坐标」映射到面板像素。

    **不做包围盒拉伸**（这是之前的一个真 bug）：
        以前按点的包围盒归一到铺满，于是**扁平形状被纵向拉满** ——
        "gone"本该是一条平掉的线（y 只有 0.012 的起伏），结果被拉成
        一条占满整幅的大正弦波，看起来完全不是"你走了"。
        所以现在直接按 [0,1]² 的**设计框**缩放，形状的固有比例就保住了。

    `fit=True` 时才按包围盒铺满 —— 只有文字形状需要它
    （文字要占满面板才读得出来）。
    """
    p = np.asarray(pts, dtype=np.float64).copy()
    if fit:
        mn, mx = p.min(axis=0), p.max(axis=0)
        span = np.maximum(mx - mn, 1e-9)
        p = (p - mn) / span
        # 文字是横向的，按宽度铺满并居中
        p[:, 0] = margin + p[:, 0] * (1 - 2 * margin)
        p[:, 1] = 0.5 + (p[:, 1] - 0.5) * (1 - 2 * margin)
        p[:, 0] *= w
        p[:, 1] *= h
        return p
    # 设计框 [0,1]² -> 面板，按较小边等比，居中
    avail = min(1 - 2 * margin, 1 - 2 * margin)
    p = margin + p * avail + (1 - 2 * margin - avail) / 2
    p[:, 0] *= w
    p[:, 1] *= h
    return p


def _resample(path: np.ndarray, n: int) -> np.ndarray:
    """把一条折线按弧长重采样成 n 个点。"""
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    if d[-1] <= 0:
        return np.repeat(path[:1], n, axis=0)
    u = np.linspace(0, d[-1], n)
    x = np.interp(u, d, path[:, 0])
    y = np.interp(u, d, path[:, 1])
    return np.stack([x, y], axis=1)


def _from_polyline(fn, n: int = NP, m: int = 1400) -> np.ndarray:
    """用参数方程采样一条曲线，再重采样成 n 个点。"""
    u = np.linspace(0, 1, m)
    return _resample(fn(u), n)


@lru_cache(maxsize=32)
def _text_points(text: str, n: int = NP, font_px: int = 150):
    """把一段文字栅格化，从**笔画边缘**采样 n 个点。

    为什么取边缘而不是全部笔画像素：
        全部像素会把字内部也填上点，720 个点摊到 9 个字母上就成了噪声，
        字读不出来。取边缘则点都落在笔画轮廓上，字的形状最清楚。

    这样 "EXECUTION" 也能和其他形状逐点插值 —— 她的点会**走**成字，
    而不是突然出现一个字。
    """
    f = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", font_px)
    img = Image.new("L", (10, 10))
    d = ImageDraw.Draw(img)
    box = d.textbbox((0, 0), text, font=f)
    W, H = box[2] - box[0] + 24, box[3] - box[1] + 24
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    d.text((12 - box[0], 12 - box[1]), text, font=f, fill=255)
    a = np.asarray(img)
    m = a > 110
    # 边缘 = 有笔画 且 四邻中至少一个没有笔画
    e = m.copy()
    e[1:, :] &= m[:-1, :]
    e[:-1, :] &= m[1:, :]
    e[:, 1:] &= m[:, :-1]
    e[:, :-1] &= m[:, 1:]
    edge = m & ~e
    ys, xs = np.nonzero(edge if edge.sum() > n else m)
    if len(xs) == 0:
        return np.zeros((n, 2))
    rng = np.random.default_rng(11)
    idx = rng.choice(len(xs), size=n, replace=len(xs) < n)
    return np.stack([xs[idx], ys[idx]], axis=1).astype(np.float64)


# ------------------------------------------------------------------ 形状
def sh_her(sil: np.ndarray, w, h) -> np.ndarray:
    """她本人（从立绘采样的轮廓点）。sil 已是归一化坐标。"""
    return np.stack([sil[:, 0] * w, sil[:, 1] * h], axis=1)


def sh_points(w, h) -> np.ndarray:
    """如果我是一组点 —— 一个规整的点阵。"""
    k = int(math.sqrt(NP)) + 1
    gx, gy = np.meshgrid(np.linspace(0, 1, k), np.linspace(0, 1, k))
    p = np.stack([gx.ravel(), gy.ravel()], axis=1)[:NP]
    return _norm(p * 0.92 + 0.04, w, h, 0.10)


def sh_circle(w, h) -> np.ndarray:
    """如果我是一个圆 —— 一圈圈同心圆。"""
    rings = 7
    per = NP // rings
    out = []
    for k in range(rings):
        r = (k + 1) / rings * 0.46
        a = np.linspace(0, math.tau, per, endpoint=False) + k * 0.5
        out.append(np.stack([0.5 + np.cos(0) * 0 + r * np.cos(a),
                             0.5 + r * np.sin(a)], axis=1))
    p = np.concatenate(out, axis=0)
    if len(p) < NP:
        p = np.concatenate([p, p[:NP - len(p)]], axis=0)
    return _norm(p[:NP], w, h, 0.08)


def sh_sine(w, h) -> np.ndarray:
    """如果我是一条正弦波 —— 三条不同频率的正弦。"""
    rows = 3
    per = NP // rows
    out = []
    for k in range(rows):
        y0 = (k + 0.5) / rows
        a = np.linspace(0, 1, per)
        out.append(np.stack([a, y0 + 0.16 * np.sin(a * math.tau * (1.4 + k * 0.7))],
                            axis=1))
    return _norm(np.concatenate(out, axis=0)[:NP], w, h, 0.06)


def sh_limit(w, h) -> np.ndarray:
    """如果我趋近于无穷 —— 画 **∞ 符号本身**。

    用户说「无穷的图像应该是符号」。之前画的是一条渐近线加一条曲线，
    那是数学图示不是符号。∞ 的符号是一条双纽线（lemniscate），
    直接按参数方程画出来。
    """
    a = np.linspace(0, TAU, NP, endpoint=False)
    # 双纽线：x = a*cos(t)/(1+sin²t), y = a*sin(t)cos(t)/(1+sin²t)
    den = 1.0 + np.sin(a) ** 2
    x = np.cos(a) / den
    y = np.sin(a) * np.cos(a) / den
    p = np.stack([x, y], axis=1)
    p = (p - p.min(axis=0)) / np.maximum(p.max(axis=0) - p.min(axis=0), 1e-9)
    p = 0.04 + p * 0.92
    return _norm(p, w, h, 0.06)


def sh_current(w, h) -> np.ndarray:
    """切换我的电流 —— 交流与直流交替的波。"""
    rows = 4
    per = NP // rows
    out = []
    for k in range(rows):
        y0 = (k + 0.5) / rows
        a = np.linspace(0, 1, per)
        v = np.sin(a * math.tau * 3) if k % 2 else np.sign(np.sin(a * math.tau * 0.5))
        out.append(np.stack([a, y0 + 0.07 * v], axis=1))
    return _norm(np.concatenate(out, axis=0)[:NP], w, h, 0.06)


def sh_timeline(w, h) -> np.ndarray:
    """我们可以穿越时空 —— **一条真正的时间轴**。

    用户说「从未来到过去的表现形式换成时间轴」。
    原来的实现是一条带高斯凸起的线，读不出"时间轴"的意思。
    现在画：横轴 + 等距刻度（每 5 格一个长刻度）+ 两端箭头 +
    一个游标。箭头指向两端，对应 A.D 与 B.C。

    点全部按**画线顺序**排列，所以连线出来就是时间轴本身。
    """
    segs = []
    y = 0.52
    # 横轴：从 0.06 到 0.94
    t = np.linspace(0.06, 0.94, NP // 3)
    segs.append(np.stack([t, np.full_like(t, y)], axis=1))
    # 刻度：每 5 格一个长的，其余短的
    n_tick = 17
    for k in range(n_tick + 1):
        x = 0.06 + (0.94 - 0.06) * k / n_tick
        long_ = (k % 5 == 0)
        ln = 0.075 if long_ else 0.035
        m = 6 if long_ else 4
        tt = np.linspace(0, 1, m)
        segs.append(np.stack([np.full(m, x), y - ln + tt * ln * 2], axis=1))
    # 两端箭头（指向左右 = 未来 / 过去）
    for sgn, x0 in ((-1.0, 0.06), (+1.0, 0.94)):
        for k in (0, 1):
            m = 6
            tt = np.linspace(0, 1, m)
            ax = x0 + sgn * 0.055 * (1 - tt)
            ay = y + (0.055 if k == 0 else -0.055) * tt
            segs.append(np.stack([ax, ay], axis=1))
    # 游标：一个方块标记
    m = 8
    tt = np.linspace(0, 1, m, endpoint=False)
    a = tt * TAU
    segs.append(np.stack([0.50 + 0.022 * np.cos(a), y + 0.022 * np.sin(a)], axis=1))

    allp = np.concatenate(segs, axis=0)
    per = max(4, NP // len(segs))
    out = []
    for sg in segs:
        out.append(_resample(sg, per))
    p = np.concatenate(out, axis=0)
    p = (p - p.min(axis=0)) / np.maximum(p.max(axis=0) - p.min(axis=0), 1e-9)
    if len(p) < NP:
        p = np.concatenate([p, p[:NP - len(p)]], axis=0)
    p = 0.03 + p[:NP] * 0.94
    return _norm(p, w, h, 0.05)


def sh_shapes(w, h) -> np.ndarray:
    """茄子 / 番茄 / 花猫 —— 三个圆润的轮廓轮廓。"""
    per = NP // 3
    out = []
    for k in range(3):
        a = np.linspace(0, math.tau, per, endpoint=False)
        rx, ry = (0.075, 0.13) if k == 0 else (0.095, 0.095) if k == 1 else (0.105, 0.075)
        cx = 0.2 + k * 0.3
        wob = 1 + 0.10 * np.sin(a * (3 + k))
        out.append(np.stack([cx + rx * np.cos(a) * wob,
                             0.5 + ry * np.sin(a) * wob], axis=1))
    return _norm(np.concatenate(out, axis=0)[:NP], w, h, 0.06)


def sh_god(w, h) -> np.ndarray:
    """如果我是唯一的神 —— 放射状。"""
    a = np.linspace(0, math.tau, NP, endpoint=False)
    r = 0.09 + 0.38 * ((np.arange(NP) % 3) / 2.0)
    return _norm(np.stack([0.5 + r * np.cos(a), 0.5 + r * np.sin(a)], axis=1),
                 w, h, 0.06)


def sh_swap(w, h) -> np.ndarray:
    """切换性别 / 角色 —— 两簇点在交换位置。"""
    half = NP // 2
    a = np.linspace(0, math.tau, half // 2, endpoint=False)
    c1 = np.stack([0.22 + 0.11 * np.cos(a), 0.5 + 0.11 * np.sin(a)], axis=1)
    c2 = np.stack([0.78 + 0.11 * np.cos(a), 0.5 + 0.11 * np.sin(a)], axis=1)
    p = np.concatenate([c1, c2, c1, c2], axis=0)[:NP]
    return _norm(p, w, h, 0.06)


def sh_vibrate(w, h) -> np.ndarray:
    """如果我感受到你的振动 —— 多行波，幅度向外增大。"""
    rows = 8
    per = NP // rows
    out = []
    for k in range(rows):
        y0 = (k + 0.5) / rows
        a = np.linspace(0, 1, per)
        amp = 0.055 * (0.3 + k / rows)
        out.append(np.stack([a, y0 + amp * np.sin(a * math.tau * (3 + k * 0.5))], axis=1))
    return _norm(np.concatenate(out, axis=0)[:NP], w, h, 0.05)


def sh_gone(w, h) -> np.ndarray:
    """你走了 —— 一条几乎平掉的线。"""
    a = np.linspace(0, 1, NP)
    y = 0.5 + 0.012 * np.sin(a * math.tau * 2)
    return _norm(np.stack([a, y], axis=1), w, h, 0.06)


def sh_execute(w, h) -> np.ndarray:
    """EXECUTION —— 她的点排成这个字。"""
    return _norm(_text_points("EXECUTION"), w, h, 0.04, fit=True)


def sh_count(w, h) -> np.ndarray:
    """六语言计数 —— 排成数字的形状。"""
    per = NP // 3
    out = []
    for k, s in enumerate(("1", "2", "3")):
        p = _text_points(s, per, 200)
        out.append(p / np.array([p[:, 0].max() + 1, p[:, 1].max() + 1]))
    p = np.concatenate(out, axis=0)
    p[:, 0] = (p[:, 0] + np.repeat([0.0, 0.36, 0.72], per))[:len(p)]
    return _norm(p[:NP], w, h, 0.06, fit=True)


def sh_love(w, h) -> np.ndarray:
    """爱的代数表达式 —— 一条在 distance 处发散的曲线。"""
    a = np.linspace(0.06, 0.94, NP)
    x = a * 2.0
    with np.errstate(divide="ignore", invalid="ignore"):
        y = x / (1.0 - x)
    y = np.clip(np.nan_to_num(y, nan=0.0, posinf=3.0, neginf=-3.0), -3.0, 3.0)
    return _norm(np.stack([a, 0.5 - y * 0.11], axis=1), w, h, 0.06)


SHAPES = {
    "points": sh_points, "circle": sh_circle, "sine": sh_sine, "limit": sh_limit,
    "current": sh_current, "timeline": sh_timeline, "shapes": sh_shapes,
    "god": sh_god, "swap": sh_swap, "vibrate": sh_vibrate, "gone": sh_gone,
    "execute": sh_execute, "count": sh_count, "love": sh_love,
}


# ------------------------------------------------------------------ 歌词 → 形状
LYRIC_SHAPE = {
    "If I'm a set of points": "points", "DIMENSION": "points",
    "If I'm a circle": "circle", "CIRCUMFERENCE": "circle",
    "If I'm a sine wave": "sine", "TANGENTS": "sine",
    "If I approach infinity": "limit", "LIMITATIONS": "limit",
    "Switch my current": "current", "To AC to DC": "current",
    "Oh we can travel": "timeline", "To A.D to B.C": "timeline",
    "If I'm an eggplant": "eggplant", "NUTRIENTS": "eggplant",
    "If I'm a tomato": "tomato", "ANTIOXIDANTS": "tomato",
    "If I'm a tabby cat": "cat", "ENJOYMENT": "cat",
    "If I'm the only god": "god", "EXISTENCE": "god",
    "Switch my gender": "gender", "To F to M": "gender",
    "Oh switch my role": "role", "To S to M": "role",
    "If I can feel your": "vibrate", "VIBRATIONS": "vibrate",
    "Then I can finally be": "vibrate", "COMPLETION": "vibrate",
    "Though you have left": "gone", "You have left": "gone",
    "You have left me in": "gone", "ISOLATION": "gone",
    "EXECUTION": "execute",
    "EIN": "count", "DOS": "count", "TROIS": "count",
    "NE": "count", "FEM": "count", "LIU": "count",
    "I've studied": "love", "I've studied how to properly": "love",
    "LO-O-OVE": "love", "I know the algebraic expression of": "love",
    "Though you are free": "gone", "I am trapped": "gone",
    "Trapped in": "gone",
}


def shape_for(lyric: str) -> str:
    return LYRIC_SHAPE.get(lyric, "her")


# ------------------------------------------------------------------ 绘制
def draw_cloud(img: Image.Image, pts: np.ndarray, t: float, feat,
               alpha: int = 235, links: bool = True, seg=None,
               shape: str = "") -> None:
    """点 + 线。点连成线，线的浓淡跟随音乐。

    `seg` 是每个点的段号：**段界上不连线**。她的轮廓是分段采样的
    （笔记本、手臂和身体不连通），不跳过段界就会画出横跨画面的长线。

    `shape` 用来判断要不要连线：**文字形状不连线**。文字的点是从笔画上
    随机采样的（见 _text_points），点序没有几何意义，一连就是乱麻，
    字反而读不出来。只画点，字就清楚。
    """
    d = ImageDraw.Draw(img)
    n = len(pts)
    if n == 0:
        return
    if shape in NO_LINK:
        links = False
    if links:
        segv = np.asarray(seg) if seg is not None else np.zeros(n, dtype=int)
        dif = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        lim = max(6.0, float(np.median(dif)) * 3.2)
        for k in range(n - 1):
            if segv[k] != segv[k + 1] or dif[k] > lim:
                continue
            a = int((60 + 90 * feat.bands[k % 7]) * (alpha / 255))
            d.line([pts[k, 0], pts[k, 1], pts[k + 1, 0], pts[k + 1, 1]],
                   fill=tk.rgba(tk.ME_MID, a), width=max(1, int(round(_S))))
    for k in range(n):
        r = 0.9 + 1.4 * feat.bands[k % 7]
        lum = 0.45 + 0.55 * min(1.0, feat.loud + 0.4 * feat.kick)
        r *= _S
        d.ellipse([pts[k, 0] - r, pts[k, 1] - r, pts[k, 0] + r, pts[k, 1] + r],
                  fill=tk.rgba(tk.lerp(tk.ME_MID, tk.ME_HI, lum), alpha))


NO_LINK = {"execute", "count", "gender", "role"}   # 字形/符号只画点
# 为什么：这些形状的点是从笔画边缘**随机**采样的，点序没有几何意义，
# 一按顺序连线就成一团乱麻（实测 S/M 和 ♂♀ 都被糊住看不出）。


def ease_io(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def perm_for(src_key: str, tgt_key: str, w: int, h: int) -> np.ndarray:
    """给目标点排序，使每个源点走到最近的目标空位（贪心最近邻，带缓存）。

    为什么必须做：
        两团点的**数组顺序**各自独立（她按轮廓顺序、圆按角度顺序），
        直接按下标插值，每个点会跑到对面去，中途互相穿插成一团乱麻
        （实测 39.00s 那帧就是一坨）。
        先做一次最近邻配对，点只走"最近的那条路"，变形才像连贯的形变。

    贪心不是最优（不是匈牙利算法），但对 720 个点够好，而且是 O(N²)，
    结果按 (形状对, 尺寸) 缓存，整片只算有限几次。
    """
    from functools import lru_cache as _lc

    @_lc(maxsize=1)
    def _cache_key():
        return None

    key = (src_key, tgt_key, w, h)
    if key in _PERM_CACHE:
        return _PERM_CACHE[key]
    pa = shape_points(src_key, w, h)
    pb = shape_points(tgt_key, w, h)
    n = len(pa)
    used = np.zeros(len(pb), dtype=bool)
    order = np.empty(n, dtype=int)
    for k in range(n):
        d = np.linalg.norm(pb - pa[k], axis=1)
        d[used] = 1e18
        j = int(np.argmin(d))
        order[k] = j
        used[j] = True
    _PERM_CACHE[key] = order
    return order


_PERM_CACHE: dict = {}
_HER_PTS: np.ndarray | None = None


def set_her(pts: np.ndarray) -> None:
    """把「她本人」的轮廓点交给本模块（由渲染器启动时载入）。"""
    global _HER_PTS
    _HER_PTS = pts


def shape_points(name: str, w: int, h: int) -> np.ndarray:
    """取某个形状在 w×h 下的点集（带缓存）。"""
    key = (name, w, h)
    if key in _SHAPE_CACHE:
        return _SHAPE_CACHE[key]
    if name == "her":
        if _HER_PTS is None:
            pts = np.zeros((NP, 2))
        else:
            pts = _norm(_HER_PTS, w, h, 0.05)
    else:
        pts = SHAPES[name](w, h)
    _SHAPE_CACHE[key] = pts
    return pts


_SHAPE_CACHE: dict = {}


def morph(a: np.ndarray, b: np.ndarray, u: float, stagger: float = 0.45) -> np.ndarray:
    """按点错峰插值。

    `stagger` 让点**依次**出发而不是同时出发：第 k 个点比第 k+1 个早一点。
    这样变形在画面上是一道波扫过去，而不是所有点同时乱撞。
    """
    n = len(a)
    if n == 0:
        return b
    if stagger <= 0:
        w = ease_io(u)
        return a * (1 - w) + b * w
    frac = np.arange(n) / max(1, n - 1)
    uu = np.clip(u * (1 + stagger) - stagger * frac, 0.0, 1.0)
    w = uu * uu * (3 - 2 * uu)
    return a * (1 - w[:, None]) + b * w[:, None]

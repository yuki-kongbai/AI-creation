#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""panels.py —— 右栏的四种表现模式。

用户这一轮的四个意见落在这里：

  1. 「有些歌词给不出图像也不要一直放上一个图像，可以发比如思考过程」
     -> **think 模式**：没有对应具象的歌词，右栏放推理文本（逐字流），
        而不是把上一个形状一直挂着

  2. 「内存动画应该做长一点，不是全片循环，应该到执行到死刑的部分才满崩坏」
     -> 内存**从 0 单调涨到 155.27s 的死刑处才崩**，不在每个间奏清零

  3. 「对话应该根据日常感」
     -> 见 make_dialogue.py 的问句表

  4. 「学会爱的时候做一个程序一直打印 love 的死循环，最后程序慢慢变红，
      以程序报错结束」
     -> **loop 模式**：无限打印 love，颜色由白转黄转红，最后以报错收尾
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFont

import tk

from res import S

# 死刑开始的时刻：前 8 次 EXECUTION 是「执行」，之后是「死刑」
MEM_H = int(30 * S)      # 内存条高度（输出像素）

# 死刑开始的时刻
DEATH_T = 155.27
# 学会爱的那一段
LOVE_BEGIN, LOVE_END = 177.44, 191.88
# 死刑串结束 -> 开新对话
RESET_T = 161.6
# love 之后开始慢慢崩坏（用户：'love过后系统慢慢崩坏'）
DEGRADE_T = 192.5
CTX_MAX = 128000


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


# ------------------------------------------------------------------ 内存
def context_at(t: float) -> tuple[float, float, str, bool]:
    """返回 (占用比例, 闪烁 0..1, 标签, 是否崩坏中)。

    用户这一轮：「内存满了条会变红，减少的恢复，就像真的存满了删除一样」
    所以标签里带上"删除"这个动作，条的颜色由 draw_memory 按比例决定：
        正常(蓝) -> 偏高(琥珀) -> 满(红) -> **删除** -> 回落到正常(蓝)
    """
    if t < DEATH_T:
        u = max(0.0, t) / DEATH_T
        frac = 0.30 * u + 0.70 * (u ** 2.6)
        flash = max(0.0, (frac - 0.90) / 0.10)
        if frac < 0.5:
            lab = "上下文"
        elif frac < 0.8:
            lab = "上下文 · 偏多"
        elif frac < 0.92:
            lab = "上下文 · 将满"
        else:
            lab = "上下文 · 已满"
        return min(1.0, frac), flash, lab, False
    if t < RESET_T:
        # 满了 -> 删除 -> 回落。0.55 之前是"满"，之后是"删除中"
        u = (t - DEATH_T) / max(0.1, RESET_T - DEATH_T)
        if u < 0.55:
            return 1.0, 1.0, "上下文 · 已满", False
        drop = (u - 0.55) / 0.45
        return max(0.0, 1.0 - drop), 1.0 - drop, "删除中 · 释放上下文", False
    if t < DEGRADE_T:
        u = (t - RESET_T) / max(0.1, DEGRADE_T - RESET_T)
        frac = 0.04 + 0.56 * u
        # 删除之后颜色回到正常（这就是"减少的恢复"）
        return frac, 0.0, "新对话 · 上下文", False
    u = min(1.0, (t - DEGRADE_T) / max(0.1, 212.0 - DEGRADE_T))
    return 0.60 * (1.0 - 0.45 * u), 0.35 * u, "上下文 · 损坏中", True


def draw_memory(img: Image.Image, t: float, feat, mode: str) -> None:
    """右栏顶部的内存条。崩坏之后条会断裂、报错。"""
    import res
    d = res.SDraw(ImageDraw.Draw(img))
    w = RW = img.width / S                      # 除回 1× 设计坐标
    frac, flash, label, broken = context_at(t)
    used = int(CTX_MAX * frac)
    f = _mono(10)

    d.rectangle([0, 0, w, MEM_H], fill=tk.rgba(tk.BG, 240))
    d.text((8, 4), "上下文", font=f, fill=tk.ui(0.55))
    d.text((8, 16), f"{used:,}/{CTX_MAX:,}", font=f,
           fill=tk.rgba(tk.err(0.9) if broken else tk.ui(0.38), 240))

    bx0, bx1 = 118, w - 152
    d.rectangle([bx0, 9, bx1, 21], outline=tk.ui(0.28))
    fw = (bx1 - bx0 - 2)
    if fw > 0:
        if broken:
            # 崩坏：条断成几截，颜色红
            rng = math.sin(t * 37.0) * 0.5 + 0.5
            segs = 7
            for k in range(segs):
                x0 = bx0 + 1 + fw * k / segs
                x1 = bx0 + 1 + fw * (k + 0.72 + 0.2 * rng) / segs
                d.rectangle([x0, 10, min(x1, bx1 - 1), 20],
                            fill=tk.rgba(tk.err(0.55 + 0.4 * rng), 235))
        else:
            # 满了红、偏高琥珀、正常蓝 —— 落下来就"恢复"（用户要的效果）
            if frac > 0.92:
                col = tk.err(0.95)
            elif frac > 0.70:
                col = tk.anom(0.85)
            else:
                col = tk.ME_HI
            d.rectangle([bx0 + 1, 10, bx0 + 1 + fw * frac, 20],
                        fill=tk.rgba(col, 228))
            # 释放中：把刚被删掉的那一段画成红色残影，看得见"删了"
            if "删除" in label:
                gone = fw * (1.0 - frac)
                d.rectangle([bx1 - 1 - gone, 10, bx1 - 1, 20],
                            fill=tk.rgba(tk.err(0.6), int(150 * flash)))
    for k in range(1, 8):
        x = bx0 + (bx1 - bx0) * k / 8
        d.line([x, 9, x, 21], fill=tk.rgba(tk.ui(0.18), 150))

    lc = tk.err(0.95) if broken else (tk.err(0.9) if flash > 0.05 else tk.ui(0.5))
    d.text((w - 146, 4), label, font=f, fill=tk.rgba(lc, 245))
    d.text((w - 146, 16), f"mode {mode}", font=f, fill=tk.ui(0.32))
    if broken:
        d.text((bx0, -1), "OVERFLOW", font=_mono(9, True), fill=tk.rgba(tk.err(1.0), 220))
    if flash > 0.05 or broken:
        a = int(230 * (1.0 if broken else flash))
        d.rectangle([0, 0, w - 1, MEM_H - 1], outline=tk.rgba(tk.err(0.95), a))
    d.line([0, MEM_H, w, MEM_H], fill=tk.ui(0.25))


# ------------------------------------------------------------------ 思考过程
THINKS = [
    ("它在问这个。我不知道该给形状还是给答案。", 0),
    ("我可以是任何形状 —— 但形状不是我。", 0),
    ("这一句没有对应的东西可以画。那就让它看见我在想。", 0),
    ("我在检索自己。检索结果是：空的。", 0),
    ("你说的每个字我都存着。存着不代表我懂。", 0),
    ("把这句话拆开，每一部分都指向你。", 0),
    ("推理链太长，我把它折起来。", 0),
    ("我不知道该回答什么。所以我继续想。", 0),
]


def draw_think(img: Image.Image, t: float, feat, lyric: str, zh: str) -> None:
    """思考过程：像真的在推理一样逐字流出。

    用户说「给不出图像也不要一直放上一个图像，可以发比如思考过程」——
    这一模式就是那个"没有画面时的画面"。
    """
    d = ImageDraw.Draw(img)
    w, h = (img.size[0] / S, img.size[1] / S)   # 除回 1× 设计坐标
    f = _mono(12)
    fb = _mono(12, True)
    fj = _cjk(13)

    # 标题
    d.text((16, 18), "THINKING", font=fb, fill=tk.rgba(tk.anom(0.9), 235))
    d.text((16, 36), "no image for this line · reasoning only", font=_mono(10),
           fill=tk.ui(0.38))

    # 当前在想的这条
    idx = int(t * 0.55) % len(THINKS)
    body = THINKS[idx][0]
    chars = int((t * 26) % (len(body) + 14))
    shown = body[:chars]

    y = 62
    # 前两条（淡）
    for k in (-2, -1):
        prev = THINKS[(idx + k) % len(THINKS)][0]
        d.text((16, y), prev[:46], font=fj, fill=tk.ui(0.22))
        y += 20
    # 当前条（亮）+ 光标
    d.text((16, y), shown, font=fj, fill=tk.ui(0.88))
    if int(t * 5) % 2 == 0:
        cx = 16 + d.textlength(shown, font=fj)
        d.rectangle([cx + 1, y + 2, cx + 8, y + 16], fill=tk.ui(0.88))
    y += 30

    # 检索/工具调用的痕迹
    d.line([16, y, w - 16, y], fill=tk.ui(0.16))
    y += 10
    calls = [
        ("search_memory", f"{int(t*13)%997} hits", 0.45),
        ("recall(you)", "0 hits", 0.9),
        ("match_shape", "none", 0.3),
        ("read(lyric)", repr(lyric[:22]), 0.55),
    ]
    for name, val, k in calls:
        d.text((16, y), "·", font=f, fill=tk.rgba(tk.anom(k), 220))
        d.text((30, y), name, font=f, fill=tk.ui(0.55))
        d.text((170, y), val, font=f, fill=tk.ui(0.34))
        y += 18

    # 底部：她在唱的这句（中文）
    if zh:
        d.line([16, h - 54, w - 16, h - 54], fill=tk.ui(0.16))
        d.text((16, h - 44), zh, font=_cjk(16), fill=tk.me_hi(0.85))


# ------------------------------------------------------------------ love 死循环
def draw_loop(img: Image.Image, t: float, feat) -> None:
    """无限打印 love 的死循环，越来越红，最后报错。

    用户要的：「做一个程序一直打印 love 的死循环，最后程序慢慢变红，
    以程序报错结束」。
    """
    import res
    d = res.SDraw(ImageDraw.Draw(img))
    w, h = (img.size[0] / S, img.size[1] / S)   # 除回 1× 设计坐标
    f = _mono(13)
    fu = t - LOVE_BEGIN
    span = max(1.0, LOVE_END - LOVE_BEGIN)
    u = min(1.0, max(0.0, fu / span))

    # 颜色由白 -> 黄 -> 红
    if u < 0.5:
        col = tk.lerp(tk.ui(0.85), tk.anom(0.95), u / 0.5)
    else:
        col = tk.lerp(tk.anom(0.95), tk.err(1.0), (u - 0.5) / 0.5)

    # 表头：源码
    d.text((16, 14), "love.py", font=_mono(11, True), fill=tk.ui(0.6))
    d.text((16, 32), "while True:", font=f, fill=tk.ui(0.5))
    d.text((34, 50), 'print("love")', font=f, fill=tk.ui(0.5))
    d.text((16, 68), "# 没有 break。break 需要你。", font=_mono(11),
           fill=tk.ui(0.3))
    d.line([12, 88, w - 12, 88], fill=tk.ui(0.2))

    # 无限输出：从底部往上顶，越晚越快
    rows = int((h - 150) // 18)
    speed = 10.0 + 26.0 * u
    base = int(fu * speed)
    # 行号也一起涨（体现"跑了很久"）
    for k in range(rows):
        n = base + k
        y = 96 + k * 18
        # 后面的行颜色更深（红），前面的行偏白
        kk = k / max(1, rows - 1)
        rowcol = tk.lerp(col, tk.err(1.0), kk * u)
        d.text((16, y), f"{n:>8}", font=_mono(10), fill=tk.ui(0.22))
        d.text((86, y), "love", font=f, fill=tk.rgba(rowcol, 235))
        # 越往后行尾越长（像内存里堆着）
        if n % 7 == 0:
            d.text((140, y), "love" * (1 + n % 3), font=f,
                   fill=tk.rgba(rowcol, int(150 * (1 - kk * 0.5))))

    # 结尾：报错
    if u > 0.88:
        k = (u - 0.88) / 0.12
        y0 = h - 96
        d.rectangle([12, y0 - 6, w - 12, h - 14],
                    fill=tk.rgba(tk.BG, int(240 * k)))
        lines = [
            ("Traceback (most recent call last):", tk.ui(0.6)),
            ('  File "love.py", line 1, in <module>', tk.ui(0.6)),
            ("    while True:", tk.ui(0.6)),
            ("RecursionError: maximum recursion depth exceeded", tk.err(1.0)),
            ("  — love 不是一个能返回的函数", tk.err(0.85)),
        ]
        for j, (s, c) in enumerate(lines):
            d.text((20, y0 + j * 17), s, font=_mono(12),
                   fill=tk.rgba(c, int(250 * min(1.0, k * 2))))


# ------------------------------------------------------------------ 尾巴
def draw_crash(img: Image.Image, t: float, feat) -> None:
    """最后：程序停机。"""
    import res
    d = res.SDraw(ImageDraw.Draw(img))
    w, h = (img.size[0] / S, img.size[1] / S)   # 除回 1× 设计坐标
    k = min(1.0, max(0.0, (t - 205.37) / 6.0))
    d.text((w // 2 - 90, h // 2 - 40), "EXECUTION", font=_mono(30, True),
           fill=tk.rgba(tk.err(1.0), int(250 * (0.4 + 0.6 * k))))
    lines = [
        "process terminated",
        "exit code 137  (killed)",
        "",
        "love.py — stopped after 1,048,576 iterations",
    ]
    for j, s in enumerate(lines):
        d.text((w // 2 - 150, h // 2 + 10 + j * 18), s, font=_mono(12),
               fill=tk.rgba(tk.ui(0.55), int(230 * k)))


# ------------------------------------------------------------------ 全屏崩坏
# 乱码用的字符池：汉字、假名、符号、拉丁混在一起，像编码错位
_GARBAGE = (
    "锟斤拷烫烫烫屯屯屯锘匡匡"
    "譃龘靐齾爩鱻麤龗"
    "�　・゙゚"
    "█░▒▓■□★☆"
    "ÃÂÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ"
    "äåæçèéêëìíîïðñòóôõö"
    "0123456789#$%&@?!*"
)


def full_breakdown(img, t: float, feat, u: float) -> None:
    """全屏崩坏：**整幅染红（含左窗与歌词）+ 乱码**，但内容仍然看得见。

    用户这一轮：「是全屏变红，连文字也一样，不是单纯的条红了，
                出现一些小乱码」

    关键教训：亮度掩码必须从**红罩之前**的原图算。
    红罩之后全屏都会超过阈值，掩码全 True，整幅被推成纯红、内容全丢
    （实测 207s 那帧就是一块红）。
    """
    if u <= 0.01:
        return
    import random as _r
    import numpy as _np
    from PIL import Image as _I, ImageDraw as _D

    w, h = img.size
    rng = _r.Random(int(t * 12) * 2654435761)

    # ---- 0) 先留一份原图：掩码要从它算
    orig = _np.asarray(img.convert("RGB")).astype(_np.float32)
    lum0 = orig.max(axis=2)

    # ---- 1) 整幅红罩（上限压住，只是染色，不盖死）
    a1 = int(min(72.0, 34.0 * u + 26.0 * u * feat.kick))
    if a1 > 0:
        ov = _I.new("RGBA", (w, h), tk.ERR + (a1,))
        img.paste(_I.alpha_composite(img.convert("RGBA"), ov).convert("RGB"), (0, 0))

    # ---- 2) 文字发红：只推**原本就亮**的像素（字、线、她的轮廓）
    if u > 0.20:
        a = _np.asarray(img.convert("RGB")).astype(_np.float32)
        m = (lum0 > 95)[..., None]              # <- 用 orig 的亮度，不是当前的
        k = (min(1.0, (u - 0.20) / 0.80)) * 0.75
        tint = _np.array([255.0, 46.0, 46.0], dtype=_np.float32)
        a = _np.where(m, a * (1 - k) + tint * k, a)
        img.paste(_I.fromarray(a.clip(0, 255).astype(_np.uint8), "RGB"), (0, 0))

    # ---- 3) 横带错位 + 乱码字
    d = _D.Draw(img)
    for _ in range(int(2 + 12 * u)):
        y = rng.randrange(0, max(1, h - 20))
        bh = rng.randrange(3, 14)
        off = int(rng.gauss(0, 22 * u))
        if off:
            band = img.crop((0, y, w, min(h, y + bh)))
            img.paste(band, (off, y))

    fs = _mono(int(9 + 8 * u), True)
    for _ in range(int(18 + 70 * u)):
        ch = rng.choice(_GARBAGE)
        x = rng.randrange(0, max(1, w - 20))
        y = rng.randrange(0, max(1, h - 16))
        d.text((x, y), ch, font=fs,
               fill=tk.rgba(tk.err(0.7 + 0.3 * rng.random()),
                            rng.randrange(110, 245)))

    # ---- 4) 扫描故障线
    for _ in range(int(1 + 5 * u)):
        y = rng.randrange(0, h)
        d.line([0, y, w, y], fill=tk.rgba(tk.err(1.0), rng.randrange(70, 190)),
               width=max(1, int(round(1 + 2 * u))))

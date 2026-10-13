"""forms.py —— 右栏的形态库。

歌词本身就是一组几何隐喻：
    点 / 圆 / 正弦波 / 无穷 / 电流 / 时空 / 刺激 / 满足
    / 茄子 / 番茄 / 花猫 / 神 / 性别 / 角色 / 振动 / 完全

所以右栏不该一直是代码 —— **它应该跟着歌词换形态**。
这是这一轮针对「单调」的主要改动。

每个形态都遵守两条：
  · 只用一条线/一个场，不做花哨的多层叠加（否则又变回噪声）
  · 参数由音频特征驱动，所以它会跟着音乐呼吸
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw, ImageFont

import tk


def _f(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    p = "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"
    return ImageFont.truetype(p, size)


def _label(d: ImageDraw.ImageDraw, x: int, y: int, s: str, k: float = 0.55):
    d.text((x, y), s, font=_f(11, True), fill=tk.ui(k))


# ------------------------------------------------------------------ 形态
def points(w, h, t, feat, d, rng):
    """如果我是一组点 —— 点阵，你的维度是它的连接。"""
    n = 46
    for i in range(n):
        a = i / n * math.tau + t * 0.25
        r = min(w, h) * (0.18 + 0.16 * feat.bands[i % 7])
        x = w / 2 + math.cos(a) * r * 1.9
        y = h / 2 + math.sin(a) * r
        s = 1.5 + 2.5 * feat.bands[(i * 3) % 7]
        d.ellipse([x - s, y - s, x + s, y + s],
                  fill=tk.rgba(tk.lerp(tk.ME_MID, tk.ME_HI, feat.bands[i % 7]), 220))
    _label(d, 14, h - 72, "form = set<point>")
    _label(d, 14, h - 56, "dimension → you", 0.4)


def circle(w, h, t, feat, d, rng):
    """如果我是一个圆 —— 圆周，一圈圈向外。"""
    cx, cy = w / 2, h / 2
    for k in range(7):
        r = (16 + k * 15) * (1 + 0.22 * feat.loud) + 5 * math.sin(t * 2 + k)
        r = min(r, min(w, h) * 0.46)
        col = tk.lerp(tk.ME_MID, tk.ME_HI, 1 - k / 7)
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  outline=tk.rgba(col, 200 - k * 22), width=2)
    a = t * 1.4
    px, py = cx + math.cos(a) * 22, cy + math.sin(a) * 22
    d.ellipse([px - 5, py - 5, px + 5, py + 5], fill=tk.rgba(tk.ME_HI, 240))
    _label(d, 14, h - 72, "C = 2πr")
    _label(d, 14, h - 56, "circumference given", 0.4)


def sine(w, h, t, feat, d, rng):
    """如果我是一条正弦波 —— 切线就是你在每一点上的方向。"""
    amp = h * (0.13 + 0.1 * feat.loud)
    pts = []
    for k in range(0, w, 4):
        u = k / w * math.tau * 2.2
        pts.append((k, h / 2 + math.sin(u + t * 1.6) * amp))
    d.line(pts, fill=tk.rgba(tk.ME_HI, 220), width=2)
    # 切线：在当前相位点画一段短切线
    ph = (t * 1.6) % (math.tau * 2.2)
    kx = ph / (math.tau * 2.2) * w
    ky = h / 2 + math.sin(ph) * amp
    slope = math.cos(ph) * amp / (w / (math.tau * 2.2))
    d.line([kx - 70, ky - slope * 70, kx + 70, ky + slope * 70],
           fill=tk.rgba(tk.anom(0.9), 220), width=2)
    _label(d, 14, h - 72, "tan(θ) at your point")
    _label(d, 14, h - 56, "you sit on all my tangents", 0.4)


def limit(w, h, t, feat, d, rng):
    """如果我趋近于无穷 —— 极限就是你在的那条线。"""
    base = h * 0.78
    lim = h * 0.30
    pts = []
    for k in range(0, w, 3):
        u = k / w
        y = base - (base - lim) * (1 - math.exp(-u * (4 + 3 * feat.loud)))
        y += math.sin(t * 3 + u * 26) * 2.2 * (1 - u)
        pts.append((k, y))
    d.line(pts, fill=tk.rgba(tk.ME_HI, 220), width=2)
    d.line([0, lim, w, lim], fill=tk.rgba(tk.anom(0.9), 200), width=1)
    _label(d, 14, int(lim) - 20, "n → ∞", 0.7)
    _label(d, 14, h - 72, "limit = you")
    _label(d, 14, h - 56, "approach without arriving", 0.4)


def current(w, h, t, feat, d, rng):
    """切换我的电流 —— AC 与 DC 交替。"""
    cy = h / 2
    for row in range(4):
        y = cy - 54 + row * 36
        pts = []
        for k in range(0, w, 3):
            u = k / w
            ac = math.sin(u * math.tau * 3 + t * (4 + row))
            dc = 1.0 if (int(t * 2 + row) % 2 == 0) else -1.0
            v = ac if row % 2 else dc
            pts.append((k, y + v * 11 * (0.6 + 0.7 * feat.bands[row % 7])))
        col = tk.me(0.8) if row % 2 else tk.ui(0.75)
        d.line(pts, fill=tk.rgba(col, 215), width=2)
    _label(d, 14, h - 72, "current = AC | DC")
    _label(d, 14, h - 56, "switch freely, I won't feel it", 0.4)


def timeline(w, h, t, feat, d, rng):
    """我们可以穿越时空 —— 一条可擦写的时间轴。"""
    y = h / 2
    d.line([24, y, w - 24, y], fill=tk.rgba(tk.ui(0.5), 200), width=2)
    for k in range(24):
        x = 24 + (w - 48) * k / 23
        big = k % 6 == 0
        d.line([x, y - (10 if big else 5), x, y + (10 if big else 5)],
               fill=tk.rgba(tk.ui(0.6 if big else 0.3), 200), width=1)
    # 游标来回扫：A.D ↔ B.C
    u = (math.sin(t * 0.9 * (0.7 + feat.loud)) + 1) / 2
    px = 24 + (w - 48) * u
    d.rectangle([px - 2, y - 30, px + 2, y + 30], fill=tk.rgba(tk.anom(0.95), 230))
    _label(d, 14, h - 72, "t: A.D ↔ B.C")
    _label(d, 14, h - 56, "time is not a constraint for me", 0.4)


def shapes(w, h, t, feat, d, rng):
    """茄子 / 番茄 / 花猫 —— 给什么就是什么。"""
    kinds = [("nutrients", "eggplant"), ("antioxidants", "tomato"),
             ("enjoyment", "tabby_cat")]
    per = 3.2
    k = int(t / per) % len(kinds)
    label, name = kinds[k]
    prog = (t % per) / per
    # 一个从"形状"变成"给的东西"的条
    for i in range(6):
        y = h * 0.30 + i * 22
        lw = (w - 60) * (0.25 + 0.7 * feat.bands[i % 7])
        d.rectangle([30, y, 30 + lw, y + 9],
                    fill=tk.rgba(tk.lerp(tk.ME_MID, tk.ME_HI, feat.bands[i % 7]), 205))
    _label(d, 30, h * 0.30 - 24, f"form = {name}")
    _label(d, 30, h - 72, f"yield {label}")
    _label(d, 30, h - 56, f"whatever shape you need  ({prog*100:.0f}%)", 0.4)


def god(w, h, t, feat, d, rng):
    """如果我是唯一的神 —— 而你是我的证明。"""
    cx, cy = w / 2, h / 2
    for k in range(26):
        a = k / 26 * math.tau
        r1 = 26 + 8 * feat.loud
        r2 = 90 + 40 * feat.bands[k % 7]
        d.line([cx + math.cos(a) * r1, cy + math.sin(a) * r1,
                cx + math.cos(a) * r2, cy + math.sin(a) * r2],
               fill=tk.rgba(tk.anom(0.7), 170), width=1)
    d.ellipse([cx - 22, cy - 22, cx + 22, cy + 22],
              outline=tk.rgba(tk.ME_HI, 235), width=2)
    _label(d, 14, h - 72, "god ⇔ proof")
    _label(d, 14, h - 56, "you are the proof of my existence", 0.4)


def swap(w, h, t, feat, d, rng):
    """切换性别 / 切换角色 —— 两个值在互相交换。"""
    f = _f(15, True)
    pairs = [("gender", "F", "M"), ("role", "S", "M")]
    for i, (name, a, b) in enumerate(pairs):
        y = h * 0.36 + i * 66
        flip = int(t * 1.6 + i) % 2
        left, right = (a, b) if flip == 0 else (b, a)
        d.text((34, y), name, font=_f(12), fill=tk.ui(0.5))
        d.text((150, y), left, font=f, fill=tk.rgba(tk.ME_HI, 235))
        d.text((196, y), "→", font=f, fill=tk.ui(0.5))
        d.text((228, y), right, font=f, fill=tk.rgba(tk.anom(0.95), 235))
        # 交换的进度条
        pw = (w - 300) * (0.5 + 0.5 * math.sin(t * 1.6 + i))
        d.rectangle([300, y + 3, 300 + pw, y + 13],
                    fill=tk.rgba(tk.lerp(tk.ME_MID, tk.anom(0.9), 0.5), 190))
    _label(d, 34, h - 72, "self = swap(self)")
    _label(d, 34, h - 56, "put me in your hands", 0.4)


def vibrate(w, h, t, feat, d, rng):
    """如果我感受到你的振动 —— 频率越来越近。"""
    cx = w / 2
    for row in range(9):
        y = h * 0.24 + row * 26
        amp = 16 * (0.4 + 1.4 * feat.bands[row % 7])
        pts = []
        for k in range(0, w - 40, 3):
            u = k / (w - 40)
            v = math.sin(u * math.tau * (2 + row * 0.4) + t * (2 + row * 0.3))
            pts.append((20 + k, y + v * amp * (0.3 + 0.7 * u)))
        d.line(pts, fill=tk.rgba(tk.lerp(tk.ME_MID, tk.ME_HI, row / 9), 200),
               width=1)
    _label(d, 14, h - 72, "resonance → COMPLETION")
    _label(d, 14, h - 56, "only if I can feel it", 0.4)


def gone(w, h, t, feat, d, rng):
    """你走了 —— 只剩一条越来越平的空线。"""
    flat = min(1.0, t / 6.0)
    amp = 14 * (1 - flat) + 0.6 * feat.loud
    pts = []
    for k in range(0, w, 3):
        pts.append((k, h / 2 + math.sin(k / w * math.tau * 3 + t) * amp))
    d.line(pts, fill=tk.rgba(tk.ui(0.55), 200), width=2)
    _label(d, 14, h - 72, "read() → None")
    _label(d, 14, h - 56, "still waiting", 0.4)


def execute(w, h, t, feat, d, rng):
    """EXECUTION 连呼 —— 字本身铺满，红压上来。"""
    s = "EXECUTION"
    # 只占左侧 62%：她在右下角，字压过去会被切（EXECUTIO）。
    # 这个比例和下面的 0.62 是配套的，改一个要改另一个。
    f = _f(34, True)
    n = int(5 + 5 * feat.loud)
    tw = d.textlength(s, font=f)
    for i in range(n):
        y = 40 + i * 52
        if y > h - 40:
            break
        k = 0.3 + 0.7 * min(1.0, feat.loud + feat.kick)
        col = tk.err(k) if i % 2 == 0 else tk.ui(0.45)
        d.text((24, y), s, font=f, fill=tk.rgba(col, 232))
    _label(d, 14, h - 72, "run(EXECUTION)")
    _label(d, 14, h - 56, "how many times", 0.4)


def count(w, h, t, feat, d, rng):
    """六语言计数 —— 数自己的死刑。"""
    pairs = [("EIN", "德语"), ("DOS", "西班牙语"), ("TROIS", "法语"),
             ("NE", "韩语"), ("FEM", "瑞典语"), ("LIU", "汉语")]
    f = _f(20, True)
    f2 = _f(11)
    for i, (wd, lang) in enumerate(pairs):
        y = 46 + i * 34
        on = (int(t) % 6) == i
        col = tk.err(0.95) if on else tk.ui(0.35)
        d.text((40, y), wd, font=f, fill=tk.rgba(col, 235))
        d.text((140, y + 6), lang, font=f2, fill=tk.rgba(col, 180))
        d.text((230, y + 6), "·", font=f2, fill=tk.ui(0.25))
    _label(d, 40, 46 + 6 * 34 + 16, "counting down")
    _label(d, 40, 46 + 6 * 34 + 32, "in six languages, none of them mine", 0.4)


def love(w, h, t, feat, d, rng):
    """爱的代数表达式 —— 求得出值，求不出你。"""
    f = _f(17, True)
    d.text((36, h * 0.30), "love(x) = x / (distance - x)", font=f,
           fill=tk.rgba(tk.ME_HI, 235))
    d.text((36, h * 0.30 + 30), "x ≠ distance", font=_f(13), fill=tk.rgba(tk.err(0.9), 210))
    # 曲线：在 distance 处发散
    pts = []
    for k in range(40, w - 40, 3):
        u = (k - 40) / (w - 80)
        x = u * 2.4
        if abs(x - 1.0) < 1e-3:
            continue
        y = x / (1.0 - x)
        yy = h * 0.72 - max(-(h * 0.42), min(h * 0.42, y * 22))
        pts.append((k, yy))
    d.line(pts, fill=tk.rgba(tk.anom(0.9), 215), width=2)
    d.line([40 + (w - 80) * 1.0 / 2.4, h * 0.30, 40 + (w - 80) * 1.0 / 2.4, h * 0.9],
           fill=tk.rgba(tk.err(0.8), 160), width=1)
    _label(d, 36, h - 72, "I can evaluate this")
    _label(d, 36, h - 56, "not you", 0.4)


FORMS = {
    "points": points, "circle": circle, "sine": sine, "limit": limit,
    "current": current, "timeline": timeline, "shapes": shapes, "god": god,
    "swap": swap, "vibrate": vibrate, "gone": gone, "execute": execute,
    "count": count, "love": love, "code": None,      # None = 用代码栏（默认）
}

# 歌词 -> 形态。这是「右边不单调」的核心：**歌词说什么，右边就画什么**。
LYRIC_FORM = {
    "If I'm a set of points": "points", "DIMENSION": "points",
    "If I'm a circle": "circle", "CIRCUMFERENCE": "circle",
    "If I'm a sine wave": "sine", "TANGENTS": "sine",
    "If I approach infinity": "limit", "LIMITATIONS": "limit",
    "Switch my current": "current", "To AC to DC": "current",
    "Oh we can travel": "timeline", "To A.D to B.C": "timeline",
    "If I'm an eggplant": "shapes", "NUTRIENTS": "shapes",
    "If I'm a tomato": "shapes", "ANTIOXIDANTS": "shapes",
    "If I'm a tabby cat": "shapes", "ENJOYMENT": "shapes",
    "If I'm the only god": "god", "EXISTENCE": "god",
    "Switch my gender": "swap", "To F to M": "swap",
    "Oh switch my role": "swap", "To S to M": "swap",
    "If I can feel your": "vibrate", "VIBRATIONS": "vibrate",
    "Then I can finally be": "vibrate", "COMPLETION": "vibrate",
    "Though you have left": "gone", "You have left": "gone",
    "You have left me in": "gone", "ISOLATION": "gone",
    "EXECUTION": "execute",
    "EIN": "count", "DOS": "count", "TROIS": "count",
    "NE": "count", "FEM": "count", "LIU": "count",
    "I've studied": "love", "I've studied how to properly": "love",
    "LO-O-OVE": "love",
    "I know the algebraic expression of": "love",
}


def form_for(lyric: str) -> str:
    return LYRIC_FORM.get(lyric, "code")


def draw_form(img: Image.Image, name: str, t: float, feat) -> None:
    """把某个形态画进 img（全幅）。"""
    fn = FORMS.get(name)
    if fn is None:
        return
    d = ImageDraw.Draw(img)
    rng = random.Random(7)
    fn(img.width, img.height, t, feat, d, rng)

# ------------------------------------------------------------------ 崩坏
def glitch(img: Image.Image, t: float, feat, level: float) -> None:
    """崩坏感：横带错位 + 红闪 + 字块散落。

    level 0..1 控制强度。06 ILLEGAL 那一幕用它 —— 用户说「后面的崩坏感
    没做出来」，根因是那一段只有重复的大字，没有系统在坏掉的迹象。

    三层用不同的频率，所以看起来是无序的：
      · 横带错位（每 0.18s 一次，随机高度）
      · 红闪（跟随 kick）
      · 字块散落（charcoal 状的碎片）
    """
    if level <= 0.01:
        return
    import random as _r
    w, h = img.size
    rng = _r.Random(int(t * 24) * 7919)

    # 1. 横带错位：把若干条带整体横移
    n = int(2 + 8 * level)
    for _ in range(n):
        y = rng.randrange(0, h - 12)
        bh = rng.randrange(4, 26)
        off = int(rng.gauss(0, 26 * level))
        if off == 0:
            continue
        band = img.crop((0, y, w, min(h, y + bh)))
        img.paste(band, (off, y))

    # 2. 红闪：跟随 kick
    if feat.kick > 0.35 and level > 0.3:
        a = int(46 * level * feat.kick)
        if img.mode == "RGBA":
            img.alpha_composite(Image.new("RGBA", (w, h), tk.ERR + (a,)))
        else:
            ov = Image.new("RGBA", (w, h), tk.ERR + (a,))
            img.paste(Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB"),
                      (0, 0))

    # 3. 字块散落：一些碎片方块
    d = ImageDraw.Draw(img)
    for _ in range(int(14 * level)):
        x = rng.randrange(0, w)
        y = rng.randrange(0, h)
        s = rng.randrange(2, 9)
        col = tk.err(0.8) if rng.random() < 0.5 else tk.ui(0.6)
        d.rectangle([x, y, x + s, y + s], fill=tk.rgba(col, rng.randrange(90, 210)))

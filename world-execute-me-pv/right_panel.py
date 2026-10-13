"""right_panel.py —— 「她的内部」。

它不是"另一个面板"，而是**窗口里正在发生的事的内侧**。
窗口里在跑什么，这里就显示那个东西的内部形态。

版式是**纵向三段式**，每段占自己的带，不互相压：
    ┌ 上带 · 操作 ── 当前在跑什么 + 关键读数
    ├ 中带 · 主体 ── 该阶段的形态（轨道 / 折向量 / 权重条）
    └ 下带 · 她 ──── 她的轮廓 + token 流
她的位置固定在下带中央 —— 她是这个系统的常数，不随阶段变形态。

踩过的坑：
  · 白条透明度给太高（215）会糊住她；主体元素的 alpha 不超过 200
  · 条形别一次画满长度，要有"正在长出来"的过程
  · 点阵要够密（11px）且隔一格一亮，否则像噪点
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFont

import tk

GRID = 11
TOP_HDR = 34          # 上带高度（操作行）
BOT_H = 176           # 下带高度（她 + token 流）


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    p = "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"
    return ImageFont.truetype(p, size)


def _cjk(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", size)
    except OSError:
        return _font(size)


def _grid(d: ImageDraw.ImageDraw, w: int, h: int, feat, alpha: float = 1.0):
    """底纹点阵：够密够暗。隔一格亮一点，避免规则网格看起来像噪点。"""
    cols, rows = max(1, w // GRID), max(1, h // GRID)
    for r in range(rows):
        for c in range(cols):
            px = (c + 0.5) * w / cols
            py = (r + 0.5) * h / rows
            band = feat.bands[min(6, int((1 - r / max(1, rows - 1)) * 7))]
            k = 1.0 if (r + c) % 2 == 0 else 0.4
            a = int((16 + 108 * band) * k * alpha)
            if a < 9:
                continue
            d.rectangle([px, py, px + 1, py + 1],
                        fill=tk.rgba(tk.lerp(tk.ME_MID, tk.ME_HI, band), a))


# 她在原图里两件道具的完整包围盒（用连通域量出来的，不是目测）：
#     笔记本 x[83,361]  y[333,854]
#     笔     x[639,856] y[285,894]
# 裁框必须盖住这两件，否则会出现「半个笔记本」—— 那比完全不出现更怪。
# 所以横向 83–856、纵向 0–894（顶上留着她的呆毛，底下到她手）。
HER_BOX_FULL = (83, 0, 856, 894)


def panel_cells(kind: str, crop: str, cols: int, thresh: int = 118,
                box: tuple | None = None):
    """按**面板分辨率**从立绘取格。

    为什么不用 stage.art_cells：
        那是舞台网格（57×27 格），横向上她只占约 45 格，脸只有 15 格宽 ——
        **表情不可能存在**。四种裁切渲染出来都是一坨，分不出差别。
        右栏有 866px 宽，本来就该按面板自己的分辨率画她。

    `box` 是原图上的裁框像素坐标；不给就用 HER_BOX_FULL。

    返回归一化坐标 (u, v, lum)，u/v ∈ [0,1]，由调用方映射到面板像素。
    行数由裁框宽高比决定，所以格子是方的，她不会变形。
    """
    src = tk.sprite_src(kind, crop)
    bb = box or HER_BOX_FULL
    bb = (max(0, bb[0]), max(0, bb[1]),
          min(src.width, bb[2]), min(src.height, bb[3]))
    src = src.crop(bb)
    rows = max(2, int(round(cols * src.height / src.width)))
    flat = Image.new("RGBA", src.size, tk.BG + (255,))
    flat.alpha_composite(src)
    a = src.resize((cols, rows), Image.LANCZOS).getchannel("A")
    l = flat.convert("L").resize((cols, rows), Image.LANCZOS)
    A, L = a.load(), l.load()
    out = []
    for r in range(rows):
        for q in range(cols):
            if A[q, r] >= thresh:
                out.append(((q + 0.5) / cols, (r + 0.5) / rows, L[q, r] / 255.0))
    return out, rows


def _her(d: ImageDraw.ImageDraw, box, cells_uv, feat, fill: float = 0.90,
         scale_k: float = 0.62, cx: float = 0.5, alpha: int = 224):
    """她在面板里。用归一化格点，格子是方的 —— 不变形。

    `cx` 是横向位置（0=贴左 1=贴右）。默认居中；右栏要留左侧给读数时给 0.62。
    `alpha` 控制她压不压得住底下的数据 —— 她太亮会把可视化吃掉。
    """
    w, h = box
    if not cells_uv:
        return
    us = [c[0] for c in cells_uv]
    vs = [c[1] for c in cells_uv]
    uw, vh = max(us) - min(us), max(vs) - min(vs)
    sw = (w * scale_k) / max(1e-6, uw)
    sh = (h * fill) / max(1e-6, vh)
    sc = min(sw, sh)
    ox = w * cx - (min(us) + uw / 2) * sc
    oy = h / 2 - (min(vs) + vh / 2) * sc
    r = 1.15
    for (u, v, lum) in cells_uv:
        px, py = ox + u * sc, oy + v * sc
        val = min(1.0, lum + 0.45 * feat.kick)
        d.rectangle([px - r, py - r, px + r, py + r],
                    fill=tk.rgba(tk.lerp(tk.ME_MID, tk.ME_HI, val), alpha))


def _header(d: ImageDraw.ImageDraw, w: int, phase: str, t: float, feat):
    d.text((12, 9), PHASE_LABEL.get(phase, "idle"), font=_font(11),
           fill=tk.ui(0.62))
    # 右上：三个关键读数，实时变
    items = [("loud", feat.loud), ("flux", feat.flux), ("cent", feat.cent)]
    x = w - 12
    for nm, v in reversed(items):
        s = f"{nm} {v:.2f}"
        x -= d.textlength(s, font=_font(10))
        d.text((x, 10), s, font=_font(10), fill=tk.ui(0.42))
        x -= 12
    d.line([10, 26, w - 10, 26], fill=tk.rgba(tk.ui(0.20), 170))


def _tracks(d: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int,
            t: float, feat, n: int = 9):
    """工具 I/O：数据在轨道上流动。"""
    span = max(1, x1 - x0 - 24)
    for i in range(n):
        ty = y0 + 16 + i * max(18, (y1 - y0 - 24) // max(1, n))
        if ty > y1 - 8:
            break
        d.line([x0 + 12, ty, x1 - 12, ty], fill=tk.rgba(tk.ui(0.13), 140))
        for k in range(int(2 + 6 * feat.bands[i % 7])):
            ph = (t * 250 * (0.45 + feat.flux) + k * 67 + i * 41) % span
            px = x0 + 12 + ph
            hot = (k + i) % 5 == 0
            col = tk.anom(0.90) if hot else tk.ui(0.46)
            d.rectangle([px, ty - 2, px + 8, ty + 2], fill=tk.rgba(col, 200))


def _fold(d: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int,
          t: float, feat, lines: list[str]):
    """代码折向量。

    要让人**看出这个变换本身**，而不是看一堆柱子：
    每行源码缩排显示，正下方紧贴一条真正的「向量热力带」（32 格），
    带的颜色与高度随行内容与频段变 —— 一行源码对应一个向量，这是可读的。
    """
    w = x1 - x0
    d.text((x0 + 12, y0 + 7), "source  →  embedding[128]", font=_font(10),
           fill=tk.ui(0.72))
    top = y0 + 26
    n = max(1, len(lines))
    unit = max(24, min(34, (y1 - top - 10) // n))
    cells = 32
    cw = (w - 190) / cells
    for i, ln in enumerate(lines):
        by = top + i * unit
        if by + unit > y1 - 6:
            break
        prog = min(1.0, max(0.0, t * 1.9 - i * 0.28))
        if prog <= 0:
            continue
        # 源码（缩排 + 小一号，暗示"被压进去"）
        src = ln.replace("\t", "    ")
        d.text((x0 + 12, by + 1), src[:20], font=_font(9), fill=tk.ui(0.30))
        # 向量热力带：一格一个维度
        shown = max(1, int(cells * prog))
        for c in range(shown):
            v = (0.5 + 0.5 * math.sin(i * 1.7 + c * 0.42 + t * 0.6)) * feat.bands[(c + i) % 7]
            v = min(1.0, v * 1.5)
            col = tk.anom(0.85) if v > 0.62 else tk.lerp(tk.ME_MID, tk.ME_HI, v)
            px = x0 + 178 + c * cw
            d.rectangle([px, by + 2, px + max(1, cw - 1.5), by + 11],
                        fill=tk.rgba(col, int(40 + 190 * v)))
        if prog < 1.0:                      # 正在折的那一行
            px = x0 + 178 + shown * cw
            d.rectangle([px, by + 2, px + 3, by + 11], fill=tk.rgba(tk.ui(0.9), 210))


def _bars(d: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int,
          feat, rows: list[tuple[str, float]]):
    """表格因子：权重对比条。

    用系统琥珀色而不是蓝色 —— 蓝色是"代码向量"的语言，
    两种形态用同一套颜色就分不出来了。
    """
    bw = (x1 - x0) - 236
    step = max(26, min(38, (y1 - y0 - 30) // max(1, len(rows))))
    for i, (nm, v) in enumerate(rows):
        by = y0 + 22 + i * step
        d.text((x0 + 12, by + 2), nm, font=_cjk(12), fill=tk.ui(0.62))
        d.rectangle([x0 + 118, by + 4, x0 + 118 + bw, by + 15],
                    fill=tk.rgba(tk.ui(0.12), 160))
        d.rectangle([x0 + 118, by + 4, x0 + 118 + bw * v, by + 15],
                    fill=tk.rgba(tk.ui(0.45 + 0.45 * v), 205))
        d.text((x1 - 106, by + 2), f"{v:.3f}", font=_font(12), fill=tk.ui(0.85))


def _tokens(d: ImageDraw.ImageDraw, x0: int, y: int, x1: int, t: float, feat):
    text = "她在说话这件事在内部是一串数字每一次张嘴都是一次前向传播每一个回复都要先算一笔账"
    d.text((x0 + 12, y - 15), "token stream · 48 rows/s", font=_font(10),
           fill=tk.ui(0.68))
    for i in range(2):
        off = int(t * 24 + i * 27) % max(1, len(text) - 46)
        d.text((x0 + 12, y + i * 19), text[off:off + 46], font=_cjk(13),
               fill=tk.me(0.24 + 0.32 * feat.loud))


PHASE_LABEL = {
    "tool": "tool I/O · streaming to stdout",
    "code": "attention · folding source into vectors",
    "table": "logits · comparing four factors",
    "think": "thinking · no output yet",
    "idle": "idle · waiting for input",
}


def _glow(img: Image.Image, cx: float, cy: float, r: float, feat):
    """她背后的径向辉光。加深度 —— 没有它，画面是平的。"""
    from PIL import ImageFilter
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    steps = 10
    for i in range(steps, 0, -1):
        k = i / steps
        a = int(46 * (1 - k) ** 1.6 * (0.5 + 0.9 * feat.loud))
        if a < 3:
            continue
        rr = r * k
        d.ellipse([cx - rr, cy - rr * 0.82, cx + rr, cy + rr * 0.82],
                  fill=tk.rgba(tk.ME_MID, a))
    img.paste(Image.alpha_composite(
        img.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(10))).convert("RGB"),
        (0, 0))


def _ghost(d: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int,
           t: float, feat, lines: list[str]):
    """底纹：上一段代码的残影 + 硬件读数。是纹理，不是内容 —— 压得很暗。

    有它，右栏才有"这里面一直在跑东西"的感觉；
    没它，中带之外就是大片空黑。
    """
    gh = lines or ["LAYERS = (base, carriers, her, chrome, post)",
                   "def composite(t, frame):", "    return frame"]
    for i in range(14):
        y = y0 + 30 + i * 30
        if y > y1 - 8:
            break
        s = gh[i % len(gh)]
        d.text((x0 + 10, y), s[:44], font=_font(9), fill=tk.ui(0.085))
    # 右侧竖排硬件读数
    x = x1 - 22
    for i, (k, v) in enumerate((("gpu", 0.86), ("vram", 0.61), ("seq", 0.94),
                                ("temp", 0.42))):
        y = y0 + 30 + i * 52
        d.text((x, y), k, font=_font(9), fill=tk.ui(0.20))
        d.rectangle([x, y + 12, x + 8, y + 12 + int(34 * v)],
                    fill=tk.rgba(tk.lerp(tk.ME_MID, tk.ME_HI, v), 110))


def draw(size, t: float, feat, phase: str, cells, extra: dict) -> Image.Image:
    """size 是 (宽, 高)。右栏按面板分辨率画，所以只需要尺寸，不需要舞台坐标。"""
    w, h = size
    img = Image.new("RGB", (w, h), tk.BG)
    d = ImageDraw.Draw(img)

    _grid(d, w, h, feat, alpha=0.5 if phase == "think" else 1.0)
    _ghost(d, 0, TOP_HDR, w, h - BOT_H, t, feat, extra.get("code_lines", []))
    _header(d, w, phase, t, feat)

    # 三段的分界：上 34 / 下 168（她 + token 流）
    TOP = TOP_HDR
    BOT = BOT_H
    mid0, mid1 = TOP, h - BOT
    her_cx, her_cy = w * 0.62, h - BOT + BOT * 0.46
    _glow(img, her_cx, her_cy, BOT * 1.05, feat)

    # 中带：该阶段的形态
    if phase == "tool":
        _tracks(d, 0, TOP, w, mid1, t, feat)
    elif phase == "code":
        _fold(d, 0, TOP, w, mid1, t, feat, extra.get("code_lines", []))
    elif phase == "table":
        _bars(d, 0, TOP + 4, w, mid1, feat, extra.get("bars", []))
    else:
        d.text((12, TOP + 12), "— no output —", font=_font(11), fill=tk.ui(0.30))

    # 下带：她 + token 流。她在下带中央，token 流让在左侧
    d.line([10, mid1 + 6, w - 10, mid1 + 6], fill=tk.rgba(tk.ui(0.16), 150))
    # 她占右半边：左半留给读数与可视化，两者不抢地方。
    # alpha 压到 190 —— 给满亮度的话可视化会被她吃掉。
    _her(d, (w, h), cells, feat, fill=0.78, scale_k=0.46,
         cx=0.68, alpha=190)
    _tokens(d, 0, h - 52, w * 0.42, t, feat)

    d.rectangle([0, 0, w - 1, h - 1], outline=tk.rgba(tk.ui(0.28), 200), width=1)
    return img

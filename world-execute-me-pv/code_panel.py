"""code_panel.py —— 右栏：她的内部，以**代码**为主要表现手段。

之前只有 3 处文字，所以"代码感"很弱。代码感不来自装饰，来自**结构**：

    行号列      左沿竖排数字 —— 代码的第一视觉特征，有它才像代码
    代码正文    真正的源码行（用本项目的源文件），带语法着色与滚动
    类型签名    `def composite(t: float, frame: Frame) -> Frame` 这类，等宽
    地址列      右侧窄列，内存地址 / 十六进制 —— 数据感
    状态行      底部：buffer / batching / dtype / step
    光标        当前行末尾的方块，随机闪烁

代码文本取自本项目自身的源码（compose.py / right_panel.py / expand.py），
所以画面里滚动的每一行都是**真的跑过**的代码。
"""
from __future__ import annotations

import math
import random
import re
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import tk

from res import S

GRID = 11
TOP_HDR = 34
BOT_H = 118
SRC = Path(__file__).resolve().parent

# ------------------------------------------------------------------ 字体
def _mono(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    import res
    p = "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"
    return ImageFont.truetype(p, res.px(size))


def _cjk(size: int) -> ImageFont.FreeTypeFont:
    import res
    try:
        return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", res.px(size))
    except OSError:
        return _mono(size)


# ------------------------------------------------------------------ 代码素材
@lru_cache(maxsize=1)
def code_pool() -> tuple[str, ...]:
    """从本项目源码里取可读的代码行。

    为什么用自己的源码：画面里滚动的每一行都应该是真的跑过的代码，
    而不是编出来的示例 —— 这对"代码感"的可信度影响很大。

    过滤规则（都是为了"像代码"而不是"像散文"）：
      · 去掉三引号文档行 —— 整行中文长句，看着像散文
      · 行首剥掉缩进，留最多 4 格：面板只有 62% 宽，缩进多了就撞到地址列
      · 截到 58 列，并且优先保留**含代码**的行
    """
    code_lines: list[str] = []
    comment_lines: list[str] = []
    for name in ("compose.py", "right_panel.py", "expand.py", "dense_window.py",
                 "beat_table.py"):
        p = SRC / name
        if not p.exists():
            continue
        in_doc = False
        for ln in p.read_text(encoding="utf-8").splitlines():
            s = ln.rstrip().replace("\t", "    ")
            st = s.strip()
            # 必须**跟踪文档字符串的状态**。只过滤以三引号开头的行是不够的 ——
            # 文档字符串内部的正文（"结构（定型）：" 这种）会漏进来，
            # 画面上就成一片中文散文，完全没有代码感。
            if not in_doc and (st.startswith('"""') or st.startswith("'''")):
                q = st[:3]
                if not (len(st) > 3 and st.endswith(q)):
                    in_doc = True
                continue
            if in_doc:
                if st.endswith('"""') or st.endswith("'''"):
                    in_doc = False
                continue
            if not st or set(st) <= set("#-="):
                continue
            # 分隔线注释（# ------ 这种）过滤掉 —— 画面上看就是一条噪声
            if st.startswith("#") and set(st[1:].strip()) <= set("-=#~ "):
                continue
            # 中文占比高的行不要 —— 那是散文，不是代码
            if sum(1 for c in st if "\u4e00" <= c <= "\u9fff") > 2:
                continue
            stripped = s.lstrip()
            indent = min(len(s) - len(stripped), 4)
            body = " " * indent + stripped
            if len(body) < 6:
                continue
            (comment_lines if st.startswith("#") else code_lines).append(body)

    # 代码行占多数，掺一点注释 —— 全是代码会显得死板，全是注释又没有代码感
    out: list[str] = []
    ci = 0
    for i, cl in enumerate(code_lines):
        out.append(cl)
        if i % 7 == 6 and ci < len(comment_lines):
            out.append(comment_lines[ci])
            ci += 1
    return tuple(out)


def line_window(t: float, n: int, cps: float = 5.0) -> list[tuple[int, str]]:
    """滚动的代码行（行号，文本）。滚动速度由 cps 控制，行号是真实序号。"""
    pool = code_pool()
    if not pool:
        return []
    start = int(t * cps)
    return [((start + i) % len(pool) + 1, pool[(start + i) % len(pool)])
            for i in range(n)]


# ------------------------------------------------------------------ 高亮
KW_PY = re.compile(
    r"\b(def|return|import|from|for|in|if|elif|else|while|with|as|class|"
    r"lambda|and|or|not|None|True|False|try|except|raise|yield|global)\b")


def hl(line: str, cut: int = 62) -> list[tuple[str, str]]:
    """切成 [(文本, 颜色键)]。单遍扫描，注释/字符串整段吃掉。

    颜色键：c 注释 / s 字符串 / k 关键字 / n 数字 / p 标点 / t 正文
    """
    line = line[:cut]
    out: list[tuple[str, str]] = []
    i, n = 0, len(line)
    while i < n:
        if line[i] == "#":
            out.append((line[i:], "c"))
            break
        ch = line[i]
        if ch in "\"'":
            j = i + 1
            while j < n and line[j] != ch:
                if line[j] == "\\":
                    j += 1
                j += 1
            j = min(j + 1, n)
            out.append((line[i:j], "s"))
            i = j
            continue
        m = KW_PY.match(line, i)
        if m:
            out.append((m.group(0), "k"))
            i = m.end()
            continue
        m = re.compile(r"\d[\d_,]*\.?\d*").match(line, i)
        if m:
            out.append((m.group(0), "n"))
            i = m.end()
            continue
        if ch in "()[]{},:=+-*/<>.":
            out.append((ch, "p"))
            i += 1
            continue
        j = i
        while j < n and not (line[j] in "\"'#" or KW_PY.match(line, j)
                             or line[j] in "()[]{},:=+-*/<>."
                             or line[j].isdigit()):
            j += 1
        out.append((line[i:j], "t"))
        i = max(j, i + 1)
    return out or [("", "t")]


# 和聊天窗口同一套配色，这样左右两栏的代码看起来是同一个世界
COL = {
    "c": (0x8A, 0x96, 0xA4),      # 注释
    "s": (0xE0, 0xA0, 0x84),      # 字符串
    "k": (0xD2, 0x92, 0xCC),      # 关键字
    "n": (0xC4, 0xDC, 0xB6),      # 数字
    "p": (0xB4, 0xC0, 0xD2),      # 标点
    "t": (0xD0, 0xDA, 0xE8),      # 正文
}


def _alpha(c, k: float) -> tuple:
    return tuple(c) + (max(0, min(255, int(255 * k))),)


# ------------------------------------------------------------------ 各层
def _dim_code_area(img, w: int, h: int, x0: float) -> None:
    """在代码区盖一层与背景同色的半透明底色。

    为什么不再直接改点阵的 alpha：
        点阵和代码字叠在一起时，点是**画在字下面**的，但点本身很亮，
        从笔画缝隙里透出来就把字读花了（实测 2K 下尤其明显）。
        盖一层底比逐点调 alpha 干净，也不会误伤右边的她。
    """
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    S_ = img.size[0] / max(1e-6, w)
    d.rectangle([x0 * S_, 0, img.size[0], img.size[1]],
                fill=tk.BG + (170,))
    img.paste(Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB"), (0, 0))


def _grid(d: ImageDraw.ImageDraw, w: int, h: int, feat, alpha: float = 1.0):
    """背景点阵。"""
    cols, rows = max(1, int(w // GRID)), max(1, int(h // GRID))
    for r in range(rows):
        for c in range(cols):
            px = (c + 0.5) * w / cols
            py = (r + 0.5) * h / rows
            band = feat.bands[min(6, int((1 - r / max(1, rows - 1)) * 7))]
            k = 1.0 if (r + c) % 2 == 0 else 0.4
            a = int((14 + 92 * band) * k * alpha)
            if a < 8:
                continue
            d.rectangle([px, py, px + 1, py + 1],
                        fill=tk.rgba(tk.lerp(tk.ME_MID, tk.ME_HI, band), a))


def _gutter(d: ImageDraw.ImageDraw, y0: int, y1: int, lw: int, right: bool,
            t: float, lh: int):
    """行号列。代码的第一视觉特征 —— 有它才像代码。"""
    f = _mono(10)
    n = max(0, int((y1 - y0) // lh))
    base = int(t * 5.0)
    for i in range(n):
        num = base + i + 1
        y = y0 + i * lh
        if y > y1 - lh:
            break
        s = f"{num:4d}"
        x = (lw - 18) if right else 6
        hot = (num % 25 == 0)
        d.text((x, y), s, font=f, fill=tk.ui(0.42 if hot else 0.20))


def _code(d: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int,
          t: float, lh: int = 16, alpha: float = 1.0, cur: int = -1):
    """代码正文。逐行画，行内按 token 上色。"""
    f = _mono(11)
    n = max(1, int((y1 - y0) // lh))
    # 每列宽度约 6.6px（等宽 11px）。按可用宽度算能放多少列，
    # 超出就截断并加省略号 —— 直接切掉会看着像"排不下"，像坏了。
    max_cols = max(16, int((x1 - x0 - 14) / 6.6))
    for i, (num, line) in enumerate(line_window(t, n)):
        y = y0 + i * lh
        if y > y1 - lh:
            break
        cut = line[:max_cols]
        if len(line) > max_cols:
            cut = line[:max_cols - 1] + "\u2026"
        x = x0
        for txt, kind in hl(cut, cut=max_cols):
            d.text((x, y), txt, font=f, fill=_alpha(COL[kind], alpha))
            x += f.getlength(txt) / S
            if x > x1 - 8:
                break
        if i == cur:                       # 当前行的光标
            d.rectangle([min(x + 1, x1 - 6), y + 2, min(x + 6, x1 - 1), y + lh - 4],
                        fill=(0xF9, 0xFA, 0xFB, int(220 * alpha)))


def _addr(d: ImageDraw.ImageDraw, x: int, y0: int, y1: int, t: float,
          lh: int = 16):
    """右侧地址 / 十六进制列 —— 数据感。"""
    f = _mono(9)
    base = int(t * 5.0)
    for i in range(max(0, int((y1 - y0) // lh))):
        y = y0 + i * lh
        if y > y1 - lh:
            break
        addr = 0x7F00_0000 + (base + i) * 0x40
        v = (base * 7 + i * 13) & 0xFFFF
        d.text((x, y), f"{addr:08X}"[-8:], font=f, fill=tk.ui(0.13))
        d.text((x + 62, y), f"{v:04X}", font=f, fill=tk.me(0.16))


def _sig(d: ImageDraw.ImageDraw, x: int, y: int, w: int, t: float, feat):
    """类型签名 —— 等宽、精炼，最能出代码味。"""
    sigs = [
        "def composite(t: float, frame: Frame) -> Frame",
        "LAYERS: tuple[Callable, ...] = (base, carriers, her)",
        "class Cut(Protocol): story: str; pre: float; post: float",
        "def at(t: float) -> dict[str, float]",
        "CELL_X: int; CELL_Y: float",
    ]
    f = _mono(10)
    i = int(t * 0.6) % len(sigs)
    for k in range(2):
        s = sigs[(i + k) % len(sigs)][: int(w // 5.6)]
        d.text((x, y + k * 15), s, font=f,
               fill=tk.ui(0.34 if k == 0 else 0.18))


def _status(d: ImageDraw.ImageDraw, x: int, y: int, w: int, t: float, feat,
            phase: str):
    """底部状态行。像真程序那样把运行时状态摊开。"""
    f = _mono(9)
    items = [
        ("step", f"{int(t*48):06d}"),
        ("buf", f"{int(4096 + 2048*feat.loud)}/8192"),
        ("batch", "8"),
        ("dtype", "f16"),
        ("layers", "5"),
        ("phase", phase),
    ]
    xx = x
    for k, v in items:
        s = f"{k} "
        d.text((xx, y), s, font=f, fill=tk.ui(0.22))
        xx += f.getlength(s) / S
        d.text((xx, y), v, font=f, fill=tk.ui(0.46))
        xx += f.getlength(v) / S + 14
        if xx > x + w - 40:
            break


PHASE_LABEL = {
    "tool": "tool I/O · streaming to stdout",
    "code": "attention · folding source into vectors",
    "table": "logits · comparing four factors",
    "think": "thinking · no output yet",
    "idle": "idle · waiting for input",
}


def _header(d: ImageDraw.ImageDraw, w: int, phase: str, t: float, feat):
    d.text((12, 9), PHASE_LABEL.get(phase, "idle"), font=_mono(11),
           fill=tk.ui(0.64))
    x = w - 12
    for nm, v in (("cent", feat.cent), ("flux", feat.flux), ("loud", feat.loud)):
        s = f"{nm} {v:.2f}"
        x -= d.textlength(s, font=_mono(10))
        d.text((x, 10), s, font=_mono(10), fill=tk.ui(0.42))
        x -= 12
    d.line([10, 26, w - 10, 26], fill=tk.rgba(tk.ui(0.20), 170))


# ------------------------------------------------------------------ 她
def _glow(img: Image.Image, cx: float, cy: float, r: float, feat):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(9, 0, -1):
        k = i / 9
        a = int(40 * (1 - k) ** 1.6 * (0.5 + 0.9 * feat.loud))
        if a < 3:
            continue
        rr = r * k
        d.ellipse([cx - rr, cy - rr * 0.8, cx + rr, cy + rr * 0.8],
                  fill=tk.rgba(tk.ME_MID, a))
    img.paste(Image.alpha_composite(
        img.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(9))).convert("RGB"), (0, 0))


def _her(d: ImageDraw.ImageDraw, w: int, h: int, cells_uv, feat,
         fill: float = 0.46, scale_k: float = 0.265, cx: float = 0.795,
         cy: float = 0.735, alpha: int = 205):
    """她在**右下角**。

    放角上而不是右侧居中，有两个好处：
      · 左上到中部整块让给代码，代码不再被她的轮廓切碎
      · 角落是视觉的「重力点」，她落在那儿比浮在中间更稳

    cy 是垂直位置（0=顶 1=底）。0.81 让她的下沿接近面板底部但不触边 ——
    留一点余地，否则又成了「被切一半」。
    """
    if not cells_uv:
        return
    us = [c[0] for c in cells_uv]
    vs = [c[1] for c in cells_uv]
    uw, vh = max(us) - min(us), max(vs) - min(vs)
    sc = min((w * scale_k) / max(1e-6, uw), (h * fill) / max(1e-6, vh))
    ox = w * cx - (min(us) + uw / 2) * sc
    oy = h * cy - (min(vs) + vh / 2) * sc
    for (u, v, lum) in cells_uv:
        px, py = ox + u * sc, oy + v * sc
        val = min(1.0, lum + 0.4 * feat.kick)
        d.rectangle([px - 1.1, py - 1.1, px + 1.1, py + 1.1],
                    fill=tk.rgba(tk.lerp(tk.ME_MID, tk.ME_HI, val), alpha))


# ------------------------------------------------------------------ 主入口
def panel_cells(kind: str, crop: str, cols: int, thresh: int = 118,
                box: tuple | None = None):
    """按面板分辨率从立绘取格（保持宽高比）。

    box 是原图上的裁框；默认 HER_BOX_FULL —— 已包含笔记本与笔的完整范围
    （量出来的：笔记本 x[83,361] y[333,854]，笔 x[639,856] y[285,894]）。
    """
    src = tk.sprite_src(kind, crop)
    bb = box or HER_BOX_FULL
    bb = (max(0, bb[0]), max(0, bb[1]), min(src.width, bb[2]), min(src.height, bb[3]))
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


HER_BOX_FULL = (83, 0, 856, 894)


def overlay_her(img: Image.Image, t: float, feat, cells) -> None:
    """只画她（右下角）。形态层复用它 —— 她是这个系统的常数，不该消失。"""
    w, h = img.width / S, img.height / S
    _glow(img, w * 0.795, h * 0.665, 150, feat)
    d = res.SDraw(ImageDraw.Draw(img))
    _her(d, w, h, cells, feat)


def overlay_frame(img: Image.Image, t: float, feat, label: str = "") -> None:
    """只有边框与状态行。形态层没有代码，但仍需要面板的边界感。"""
    d = ImageDraw.Draw(img)
    w, h = (img.size[0] / S, img.size[1] / S)   # 除回 1× 设计坐标
    _status(d, 14, h - 22, w - 28, t, feat, label or "form")
    d.rectangle([0, 0, w - 1, h - 1], outline=tk.rgba(tk.ui(0.26), 190), width=1)
    d.text((12, 9), f"form · {label}", font=_mono(11), fill=tk.ui(0.64))


def draw(size, t: float, feat, phase: str, cells, extra: dict) -> Image.Image:
    # size 是输出像素 -> 画布用它；SDraw 按 1× 设计坐标工作，所以坐标除回。
    # 两者混用会出两个 bug：坐标被缩放两次 / Image.new 收到 float。
    import res
    img = Image.new("RGB", (int(size[0]), int(size[1])), tk.BG)
    w, h = size[0] / S, size[1] / S
    d = res.SDraw(ImageDraw.Draw(img))

    _grid(d, w, h, feat, alpha=0.5 if phase == "think" else 1.0)

    # 代码占据左侧 2/3，她在右端
    code_x0, code_x1 = 12, int(w * 0.545)
    # 点阵压到代码底下 —— 必须放在 code_x0 定义之后
    _dim_code_area(img, w, h, code_x0)
    d = res.SDraw(ImageDraw.Draw(img))
    gutter_x = code_x0
    body_x0 = code_x0 + 34
    y0, y1 = TOP_HDR + 8, h - BOT_H

    _header(d, w, phase, t, feat)
    _glow(img, w * 0.795, h * 0.735, BOT_H * 0.95, feat)   # 跟随她到右下角

    _gutter(d, y0, y1, body_x0, right=False, t=t, lh=16)
    _code(d, body_x0, y0, code_x1, y1, t, lh=16,
          alpha=0.55 if phase == "think" else 1.0,
          cur=(int(t * 5) % 9) if phase in ("code", "tool") else -1)
    _addr(d, code_x1 + 6, y0, y1, t, lh=16)

    _her(d, w, h, cells, feat)
    _sig(d, 14, h - BOT_H + 42, int(w * 0.62), t, feat)
    d.line([10, h - BOT_H + 34, w - 10, h - BOT_H + 34],
           fill=tk.rgba(tk.ui(0.16), 150))
    _status(d, 14, h - 22, w - 28, t, feat, phase)

    d.rectangle([0, 0, w - 1, h - 1], outline=tk.rgba(tk.ui(0.26), 190), width=1)
    return img

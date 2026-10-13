#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""通用 act 渲染器：任何剧本 JSON -> 一段 mp4。

已做好的 30.6 秒不走这里（它是三段 open/mid/close 拼的，保持不动）。
这里用于补完部分：每个 act 一份剧本，渲染时布局仍是既定的
「左栏窗口 354 + 右栏她的内部 866」，与已做好的部分视觉连续。

用法：
    python render_act.py content/act02_offer.json --t0 34.31 --t1 82.31
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
sys.path.insert(0, str(PV2))
sys.path.insert(0, str(HERE))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import audio  # noqa: E402
import clock as C  # noqa: E402
import code_panel as rp  # noqa: E402
import compose as CP  # noqa: E402
import dense_scene as ds  # noqa: E402
import forms  # noqa: E402
import tk  # noqa: E402

OUT = HERE / "out"
SONG = Path(r"D:\kuakewangpan\工具\bupan\Mili-world.execute(me);.mp3")
FPS = 24

WIN_W, WIN_H = 354, 573
WIN_X, WIN_Y = 24, 76
GAP = 12
RIGHT = (WIN_X + WIN_W + GAP, WIN_Y, 1280 - 24, WIN_Y + WIN_H)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    p = "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"
    return ImageFont.truetype(p, size)


def cjk(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", size)
    except OSError:
        return font(size)


# ------------------------------------------------------------------ 排版层
def chrome(t: float, feat, act: str) -> Image.Image:
    """顶栏 / 底栏。与已做好的部分保持同一套。"""
    img = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((24, 18), "WORLD.EXECUTE(ME);", font=font(15, True), fill=tk.ui(1.0))
    d.text((232, 20), "whale@deepsea:~$", font=font(13), fill=tk.ui(0.55))
    mid = f"step {int(t*48):08d}   loss {0.52+0.2*feat.loud:.4f}"
    d.text((416, 20), mid, font=font(13), fill=tk.ui(0.7))
    mm, ss = divmod(t, 60)
    right = f"{act}   {int(mm):02d}:{ss:04.1f} / 03:32   RUNNING"
    d.text((1280 - 24 - d.textlength(right, font=font(13)), 20), right,
           font=font(13), fill=tk.ui(0.85))
    d.line([24, 44, 1256, 44], fill=tk.ui(0.35))

    fs = font(11)
    n = 52
    k = int(n * min(1.0, t / 212.0))
    d.text((24, 696), "[" + "|" * k + ":" * (n - k) + "]", font=fs, fill=tk.ui(0.40))
    credit = ("角色 溟月 © 上善无形 / 女仆版 ZipZipPipe / 立绘 dsh-deep-whale "
              "(CC BY-NC-SA 4.0)    Music: Mili - world.execute(me);   非官方同人")
    d.text((1280 - 24 - d.textlength(credit, font=fs), 696), credit,
           font=fs, fill=tk.ui(0.38))
    return img


# ------------------------------------------------------------------ 歌词条
def current_lyric(t: float, lines: list[dict]):
    """t 时刻正在唱的那句（含下一句的时刻，用于算进度）。"""
    for i, r in enumerate(lines):
        nxt = lines[i + 1]["t"] if i + 1 < len(lines) else 212.0
        if r["t"] <= t < nxt:
            return r, nxt
    return None, None


def lyric_band(img: Image.Image, t: float, lines: list[dict]) -> None:
    """底部双语歌词条。这是补完部分新增的 —— 因为这一段必须让观众看懂词。

    已做好的 30.6 秒没有歌词条（那是"生成世界"阶段，还没有词要唱）。
    从 02 OFFER 起，歌词是主角，所以给它一条专用带。
    """
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 24, 614, 1256, 688
    d.rectangle([x0, y0, x1, y1], outline=tk.ui(0.30), width=1)
    cur = None
    for i, r in enumerate(lines):
        nxt = lines[i + 1]["t"] if i + 1 < len(lines) else 212.0
        if r["t"] <= t < nxt:
            cur = (r, nxt)
            break
    if not cur:
        return
    r, nxt = cur
    span = max(0.05, nxt - r["t"])
    u = min(1.0, (t - r["t"]) / span)
    # 英文行：逐字点亮
    f = font(15, True)
    s = r["en"]
    n = int(len(s) * min(1.0, u / 0.55))
    tw = d.textlength(s, font=f)
    d.text((x0 + (x1 - x0 - tw) / 2, y0 + 10), s[:n], font=f, fill=tk.ui(0.9))
    if n < len(s) and int(t * 4) % 2 == 0:
        cx = x0 + (x1 - x0 - tw) / 2 + d.textlength(s[:n], font=f)
        d.rectangle([cx + 1, y0 + 12, cx + 7, y0 + 26], fill=tk.ui(0.9))
    # 中文行
    zh = r.get("zh")
    if zh:
        f2 = cjk(20)
        tw2 = d.textlength(zh, font=f2)
        d.text((x0 + (x1 - x0 - tw2) / 2, y0 + 32), zh, font=f2,
               fill=tk.me_hi(0.92) if hasattr(tk, "me_hi") else tk.me(0.92))
        d.line([x0 + (x1 - x0 - tw2) / 2, y0 + 58,
                x0 + (x1 - x0 - tw2) / 2 + tw2 * u, y0 + 58],
               fill=tk.rgba(tk.me(0.7), 180))


# ------------------------------------------------------------------ 主流程
def glitch_level(t: float, spec: str) -> float:
    """崩坏强度随时间上升。

    `spec` 形如 "0.0,0.35,1.2" —— 三段折线（起始强度, 中间, 结束），
    按幕的起止线性插值。空字符串表示不崩。

    为什么用折线而不是常量：
        06 ILLEGAL 那一幕是"系统在逐渐坏掉"，从非法参数到连呼到计数
        应该越来越乱；给常量的话从头到尾一样乱，反而没有崩坏感。
    """
    if not spec:
        return 0.0
    try:
        a, b, c = [float(x) for x in spec.split(",")]
    except ValueError:
        return 0.0
    u = min(1.0, max(0.0, (t - T_LO) / max(1e-6, T_HI - T_LO)))
    return a + (b - a) * min(1.0, u * 2) if u < 0.5 else b + (c - b) * (u - 0.5) * 2


T_LO, T_HI = 0.0, 1.0        # 由 main() 设置


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--t0", type=float, required=True)
    ap.add_argument("--t1", type=float, required=True)
    ap.add_argument("--act", default="02 / OFFER")
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--glitch", default="",
                    help="崩坏强度折线，形如 0.0,0.35,1.2；空则不崩")
    a = ap.parse_args()

    global T_LO, T_HI
    T_LO, T_HI = a.t0, a.t1
    scene = ds.load(HERE / a.scene)
    lyrics = json.loads((HERE / "cache" / "lyrics_timed.json")
                        .read_text(encoding="utf-8"))
    # 中文大意从原始对照表取
    zh_map = {}
    zp = HERE / "cache" / "lyrics_zh.json"
    if zp.exists():
        zh_map = json.loads(zp.read_text(encoding="utf-8"))
    for r in lyrics:
        if r["en"] in zh_map:
            r["zh"] = zh_map[r["en"]]

    idx = list(range(int(a.t0 * FPS), int(a.t1 * FPS), a.every))
    print(f"[{a.act}] {a.t0:.2f} – {a.t1:.2f}s  {len(idx)} 帧  {a.scene}")

    frames = OUT / f"frames_{Path(a.scene).stem}"
    frames.mkdir(parents=True, exist_ok=True)
    for p in frames.glob("*.png"):
        p.unlink()

    times = [i / FPS for i in idx]
    t0c = time.time()
    raws = CP.shoot_window_batch(scene, times, WIN_W, WIN_H,
                                 OUT / f"_win_{Path(a.scene).stem}")
    print(f"  窗口 {len(raws)} 帧  {len(raws)/(time.time()-t0c):.1f} 帧/秒")

    cells, _ = rp.panel_cells("maid-right", "full", 260)
    feat = audio.at((a.t0 + a.t1) / 2)
    t0c = time.time()
    for n, (i, raw) in enumerate(zip(idx, raws), 1):
        t = i / FPS
        win = Image.open(raw).convert("RGB").resize((WIN_W, WIN_H), Image.LANCZOS)

        canvas = Image.new("RGB", (1280, 720), tk.BG)
        canvas.paste(win, (WIN_X, WIN_Y))
        fe = audio.at(max(0.0, min(211.0, t)))

        # 右栏：**跟着歌词换形态**。
        # 歌词本身就是一组几何隐喻（点/圆/正弦波/无穷/电流/时空/神/振动…），
        # 所以它不该一直是代码 —— 这是针对「右边单调」的主要改动。
        #
        # 形态出现时**取代**代码，不是叠上去：叠着会变成两层噪声，
        # 哪一层都看不清。她保留在最上层（她是这个系统的常数）。
        rw, rh = RIGHT[2] - RIGHT[0], RIGHT[3] - RIGHT[1]
        cur, _nxt = current_lyric(t, lyrics)
        fname = forms.form_for(cur["en"]) if cur else "code"
        if fname == "code":
            panel = rp.draw((rw, rh), t, fe, "code", cells, {})
        else:
            panel = Image.new("RGB", (rw, rh), tk.BG)
            forms.draw_form(panel, fname, t, fe)
            rp.overlay_her(panel, t, fe, cells)
            rp.overlay_frame(panel, t, fe, fname)
        canvas.paste(panel, (RIGHT[0], RIGHT[1]))
        canvas = Image.alpha_composite(canvas.convert("RGBA"),
                                       chrome(t, fe, a.act)).convert("RGB")
        # 崩坏层画在 chrome 之上、歌词条之下 —— 歌词不能跟着乱，
        # 否则观众读不了词，崩坏就变成"画面坏了"而不是"她在坏掉"。
        gl = glitch_level(t, a.glitch)
        if gl > 0.01:
            forms.glitch(canvas, t, fe, gl)
        lyric_band(canvas, t, lyrics)
        tk.post(canvas, None, trail=0.0, bloom=0.30).save(frames / f"f{i:05d}.png")
        if n % 48 == 0 or n == len(idx):
            el = time.time() - t0c
            print(f"  {n}/{len(idx)}  {n/el:.1f} 帧/秒  剩余 {max(0,len(idx)-n)/max(0.1,n/el):.0f}s")

    print(f"  合成完成 {time.time()-t0c:.1f}s -> {frames}")

    if a.no_video or a.every > 1:
        return
    ff = audio.find_ffmpeg()
    silent = OUT / f"{Path(a.scene).stem}_silent.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-framerate", str(FPS),
                    "-start_number", str(idx[0]), "-i", str(frames / "f%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17",
                    str(silent)], check=True)
    final = OUT / f"{Path(a.scene).stem}.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-i", str(silent),
                    "-ss", f"{a.t0:.3f}", "-t", f"{a.t1-a.t0:.3f}", "-i", str(SONG),
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", str(final)],
                   check=True)
    print(f"  -> {final}")


if __name__ == "__main__":
    main()

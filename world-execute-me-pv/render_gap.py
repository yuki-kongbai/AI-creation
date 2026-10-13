#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""补 30.62–34.31s 的缺口 —— 兼作**两段之间的过桥**。

上一版的问题：这个缺口只是"版式不动、歌词条亮起"，结果第一段和
02 OFFER 之间像两截接起来的。根因：
    第一段结束时右栏是定型后的代码栏，而 OFFER 一开始也是代码栏，
    中间没有任何"事情发生过"的信号，观众感觉不到换段。

所以这里加三件过渡动作（都不改左边窗口的内容）：
    1. 右栏边框闪一下（咬在 71 拍）—— 像一段程序结束、下一段开始
    2. `world.execute(me);` 这句（33.01s）用大字打在右栏中央
    3. 歌词条从"无"到"有"的淡入，与大字同步

三件都咬在拍上，所以换段听起来也是"到了"。
"""
from __future__ import annotations

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
import render_act as RA  # noqa: E402
import tk  # noqa: E402

OUT = HERE / "out"
FPS = 24
T0, T1 = 30.62, 34.31            # 缺口
T_TITLE = 33.01                  # world.execute(me); 在骨架里的时刻
RING_T = C.beat_t(71)            # 71 拍：换段的「铃声」


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    p = "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"
    return ImageFont.truetype(p, size)


def title_card(panel: Image.Image, t: float) -> None:
    """`world.execute(me);` 打在右栏中央，前后各淡入淡出一拍。

    这是这一段的**唯一事件** —— 上一版什么都没有，所以像断了一截。
    """
    d = ImageDraw.Draw(panel)
    w, h = panel.size
    k = 1.0
    if t < T_TITLE:
        k = min(1.0, (t - (T_TITLE - C.BEAT)) / C.BEAT)
    elif t > T_TITLE + C.BEAT * 2:
        k = max(0.0, 1.0 - (t - (T_TITLE + C.BEAT * 2)) / C.BEAT)
    if k <= 0.02:
        return
    f = _font(40, True)
    s = "world.execute(me);"
    tw = d.textlength(s, font=f)
    x, y = (w - tw) / 2, h * 0.40
    d.text((x + 2, y + 2), s, font=f, fill=(0, 0, 0, int(200 * k)))
    d.text((x, y), s, font=f, fill=tk.rgba(tk.ui(0.96), int(255 * k)))
    fs = _font(15)
    sub = "换气 · 世界开始运行"
    tw2 = d.textlength(sub, font=fs)
    d.text(((w - tw2) / 2, y + 52), sub, font=fs,
           fill=tk.rgba(tk.ui(0.5), int(210 * k)))
    for yy in (y - 18, y + 84):
        d.line([w * 0.18, yy, w * 0.82, yy],
               fill=tk.rgba(tk.ui(0.35), int(200 * k)))


def ring(panel: Image.Image, t: float) -> None:
    """换段的「铃声」：边框闪一下。咬在 71 拍上。"""
    dt = t - RING_T
    if not (0 <= dt < C.BEAT):
        return
    k = 1.0 - dt / C.BEAT
    d = ImageDraw.Draw(panel)
    w, h = panel.size
    for i, inset in enumerate((0, 3, 7)):
        a = int(200 * k * (1 - i * 0.3))
        if a <= 4:
            continue
        d.rectangle([inset, inset, w - 1 - inset, h - 1 - inset],
                    outline=tk.rgba(tk.ui(0.9), a), width=1)


def main():
    lyrics = json.loads((HERE / "cache" / "lyrics_timed.json")
                        .read_text(encoding="utf-8"))
    zh = {}
    zp = HERE / "cache" / "lyrics_zh.json"
    if zp.exists():
        zh = json.loads(zp.read_text(encoding="utf-8"))
    for r in lyrics:
        if r["en"] in zh:
            r["zh"] = zh[r["en"]]

    import compose as CP
    import dense_scene as ds
    scene = ds.load(HERE / "content" / "scene08.json")

    frames = OUT / "frames_act01_gap"
    frames.mkdir(parents=True, exist_ok=True)
    for p in frames.glob("*.png"):
        p.unlink()

    idx = list(range(int(T0 * FPS), int(T1 * FPS)))
    times = [i / FPS for i in idx]
    raws = CP.shoot_window_batch(scene, times, RA.WIN_W, RA.WIN_H, OUT / "_win_gap")
    cells, _ = rp.panel_cells("maid-right", "full", 260)

    t0c = time.time()
    for i, raw in zip(idx, raws):
        t = i / FPS
        fe = audio.at(max(0.0, min(211.0, t)))
        win = Image.open(raw).convert("RGB").resize((RA.WIN_W, RA.WIN_H),
                                                    Image.LANCZOS)
        canvas = Image.new("RGB", (1280, 720), tk.BG)
        canvas.paste(win, (RA.WIN_X, RA.WIN_Y))

        # 右栏暂时保持代码（这句是间奏句，还没有隐喻可用），
        # 但加上换段的两件动作。
        rw, rh = RA.RIGHT[2] - RA.RIGHT[0], RA.RIGHT[3] - RA.RIGHT[1]
        panel = rp.draw((rw, rh), t, fe, "code", cells, {})
        ring(panel, t)
        title_card(panel, t)
        canvas.paste(panel, (RA.RIGHT[0], RA.RIGHT[1]))

        canvas = Image.alpha_composite(
            canvas.convert("RGBA"), RA.chrome(t, fe, "01 / WORLD")).convert("RGB")
        RA.lyric_band(canvas, t, lyrics)
        tk.post(canvas, None, trail=0.0, bloom=0.30).save(frames / f"f{i:05d}.png")

    ff = audio.find_ffmpeg()
    silent = OUT / "act01_gap_silent.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-framerate", str(FPS),
                    "-start_number", str(idx[0]), "-i", str(frames / "f%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17",
                    str(silent)], check=True)
    final = OUT / "act01_gap.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-i", str(silent),
                    "-ss", f"{T0:.3f}", "-t", f"{T1-T0:.3f}",
                    "-i", str(RA.SONG), "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", str(final)], check=True)
    print(f"{len(idx)} 帧，{time.time()-t0c:.1f}s -> {final}")


if __name__ == "__main__":
    main()

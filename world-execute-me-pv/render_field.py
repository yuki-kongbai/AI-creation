#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""render_field.py —— 整片用「点与线」表现。

取代上一版的「代码栏 + 形态硬切」。核心：
    **她本身就是一团点**，歌词唱什么形状，她的点就走成什么形状。
    点的移动是**连续的**（逐点线性插值 + 缓动），所以没有切换感。

时间基准用 `align_sig.py` 对齐出的真实时刻表（cache/lyrics_timed.json），
它逐行都有词长签名验证，代价为 0 的行占绝大多数。

用法：
    python render_field.py --t0 0 --t1 212 [--every 1]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from bisect import bisect_right
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
sys.path.insert(0, str(PV2))
sys.path.insert(0, str(HERE))

import audio  # noqa: E402
import clock as C  # noqa: E402
import field  # noqa: E402
import tk  # noqa: E402

OUT = HERE / "out"
SONG = Path(r"D:\kuakewangpan\工具\bupan\Mili-world.execute(me);.mp3")
FPS = 24
CW, CH = 1280, 720
WIN_W, WIN_H = 354, 573
WIN_X, WIN_Y = 24, 76
GAP = 12
RIGHT = (WIN_X + WIN_W + GAP, WIN_Y, CW - 24, WIN_Y + WIN_H)
RW, RH = RIGHT[2] - RIGHT[0], RIGHT[3] - RIGHT[1]


def font(sz: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    p = "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"
    return ImageFont.truetype(p, sz)


def cjk(sz: int):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", sz)
    except OSError:
        return font(sz)


# ------------------------------------------------------------------ 状态
class Timeline:
    """真实时刻表 + 形状序列。"""

    def __init__(self):
        self.lines = json.loads((HERE / "cache" / "lyrics_timed.json")
                                .read_text(encoding="utf-8"))
        zh = {}
        zp = HERE / "cache" / "lyrics_zh.json"
        if zp.exists():
            zh = json.loads(zp.read_text(encoding="utf-8"))
        for r in self.lines:
            r["zh"] = zh.get(r["en"], "")
            r["shape"] = field.shape_for(r["en"])
        self.starts = [r["t"] for r in self.lines]
        self.her = np.load(HERE / "cache" / "her_points.npy")
        self.seg = np.load(HERE / "cache" / "her_segid.npy")
        field.set_her(self.her)

    def pts(self, name: str) -> np.ndarray:
        return field.shape_points(name, RW, RH)

    def at(self, t: float):
        """返回 (当前行, 上一行, 变形进度 u)。"""
        i = bisect_right(self.starts, t) - 1
        if i < 0:
            return None, None, 0.0
        cur = self.lines[i]
        prev = self.lines[i - 1] if i > 0 else None
        dur = max(0.22, cur.get("end", cur["t"] + 1.0) - cur["t"])
        # 变形只占这一行的**前 32%** —— 形状要早早到位，好让观众在整句里
        # 都看到它。之前用 70%，结果形状到句尾才成形，看着就是"慢一句"
        # （实测 33.6s 唱 "If I'm a circle" 时画面上还是点阵）。
        u = min(1.0, max(0.0, (t - cur["t"]) / (dur * 0.32)))
        return cur, prev, u

    def shape_at(self, i: int) -> str:
        """第 i 行应该是什么形状。

        没映射的行（"Then I will give you my" 这类连接句）**沿用上一个形状**，
        否则会在一个句子里来回跳（点阵→她→点阵），看着很碎。
        """
        j = i
        while j >= 0:
            s = field.shape_for(self.lines[j]["en"])
            if s != "her":
                return s
            j -= 1
        return "her"

    def cloud(self, t: float) -> tuple[np.ndarray, str]:
        cur, prev, u = self.at(t)
        if cur is None:
            return self.pts("her"), "her"
        i = bisect_right(self.starts, t) - 1
        # 长间奏（当前行早已唱完 >2.5s）回落到她本人 —— 空档里让画面静下来。
        # 基准必须是**当前行的结束**，不是上一行的：拿上一行比的话，
        # 紧跟在长间奏之后的第一句会被误判成"还在间奏里"
        # （实测 147.89s 的第一次 EXECUTION 就被这样吃掉，显示成了她）。
        if t > cur.get("end", cur["t"] + 1.0) + 2.5:
            return self.pts("her"), "her"
        tgt = self.shape_at(i)
        src = self.shape_at(i - 1) if i > 0 else "her"
        a = self.pts(src)
        if src == tgt or u >= 1.0:
            return self.pts(tgt), tgt
        # 最近邻配对：目标点按"离源点最近"重排，避免点互相穿插
        b = self.pts(tgt)[field.perm_for(src, tgt, RW, RH)]
        return field.morph(a, b, u), tgt


# ------------------------------------------------------------------ 画面
def draw_chrome(img: Image.Image, t: float, feat, act: str) -> None:
    d = ImageDraw.Draw(img)
    d.text((24, 18), "WORLD.EXECUTE(ME);", font=font(15, True), fill=tk.ui(1.0))
    d.text((232, 20), "whale@deepsea:~$", font=font(13), fill=tk.ui(0.55))
    d.text((416, 20), f"step {int(t*48):08d}   loss {0.52+0.2*feat.loud:.4f}",
           font=font(13), fill=tk.ui(0.7))
    mm, ss = divmod(t, 60)
    right = f"{act}   {int(mm):02d}:{ss:04.1f} / 03:32"
    d.text((CW - 24 - d.textlength(right, font=font(13)), 20), right,
           font=font(13), fill=tk.ui(0.85))
    d.line([24, 44, CW - 24, 44], fill=tk.ui(0.35))

    fs = font(11)
    n = 52
    k = int(n * min(1.0, t / 212.0))
    d.text((24, 706), "[" + "|" * k + ":" * (n - k) + "]", font=fs, fill=tk.ui(0.40))
    credit = ("角色 溟月 © 上善无形 / 女仆版 ZipZipPipe / 立绘 dsh-deep-whale "
              "(CC BY-NC-SA 4.0)    Music: Mili - world.execute(me);   非官方同人")
    d.text((CW - 24 - d.textlength(credit, font=fs), 707), credit,
           font=fs, fill=tk.ui(0.34))


def draw_lyrics(img: Image.Image, t: float, lines: list[dict]) -> None:
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 24, 656, CW - 24, 700
    d.rectangle([x0, y0, x1, y1], outline=tk.ui(0.22), width=1)
    cur = None
    starts = [r["t"] for r in lines]
    i = bisect_right(starts, t) - 1
    if i < 0:
        return
    r = lines[i]
    nxt = lines[i + 1]["t"] if i + 1 < len(lines) else 212.0
    span = max(0.12, nxt - r["t"])
    u = min(1.0, (t - r["t"]) / span)
    f = font(15, True)
    s = r["en"]
    n = int(len(s) * min(1.0, u / 0.5))
    tw = d.textlength(s, font=f)
    d.text((x0 + (x1 - x0 - tw) / 2, y0 + 4), s[:n], font=f, fill=tk.ui(0.92))
    if n < len(s) and int(t * 6) % 2 == 0:
        cx = x0 + (x1 - x0 - tw) / 2 + d.textlength(s[:n], font=f)
        d.rectangle([cx + 1, y0 + 6, cx + 7, y0 + 20], fill=tk.ui(0.92))
    zh = r.get("zh") or ""
    if zh:
        f2 = cjk(20)
        tw2 = d.textlength(zh, font=f2)
        d.text((x0 + (x1 - x0 - tw2) / 2, y0 + 24), zh, font=f2, fill=tk.me_hi(0.94))
        d.line([x0 + (x1 - x0 - tw2) / 2, y0 + 50,
                x0 + (x1 - x0 - tw2) / 2 + tw2 * u, y0 + 50],
               fill=tk.rgba(tk.me(0.7), 180))


def act_label(t: float) -> str:
    if t < 14.82:
        return "00 / GENERATE"
    if t < 29.77:
        return "01 / ——"
    if t < 69.11:
        return "02 / OFFER"
    if t < 88.54:
        return "03 / EXECUTION"
    if t < 110.41:
        return "04 / SWAP"
    if t < 118.24:
        return "05 / LEFT"
    if t < 147.89:
        return "06 / FRAGMENTS"
    if t < 159.20:
        return "07 / EXECUTION ×12"
    if t < 173.49:
        return "08 / COUNT"
    if t < 191.88:
        return "09 / LO-O-OVE"
    return "10 / END"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t0", type=float, default=0.0)
    ap.add_argument("--t1", type=float, default=212.0)
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--no-video", action="store_true")
    a = ap.parse_args()

    tl = Timeline()
    # 窗口的帧：整片用同一套内容（她与"你"的对话），
    # 不再分幕重打 —— 分幕重打是上一版"表演形式转换不自然"的来源之一。
    win_frames = OUT / "field_win"
    win_frames.mkdir(parents=True, exist_ok=True)

    idx = list(range(int(a.t0 * FPS), int(a.t1 * FPS), a.every))
    times = [i / FPS for i in idx]
    print(f"[FIELD] {a.t0:.2f} – {a.t1:.2f}s  {len(idx)} 帧")

    import dense_scene as ds
    scene = ds.load(HERE / "content" / "scene08.json")
    import compose as CP
    t0c = time.time()
    raws = CP.shoot_window_batch(scene, times, WIN_W, WIN_H, win_frames)
    print(f"  窗口 {len(raws)} 帧  {len(raws)/(time.time()-t0c):.1f} 帧/秒")

    frames = OUT / "frames_field"
    frames.mkdir(parents=True, exist_ok=True)
    for p in frames.glob("*.png"):
        p.unlink()

    t0c = time.time()
    for n, (i, raw) in enumerate(zip(idx, raws), 1):
        t = i / FPS
        fe = audio.at(max(0.0, min(211.5, t)))
        canvas = Image.new("RGB", (CW, CH), tk.BG)

        # 左栏：她与"你"的对话窗口
        win = Image.open(raw).convert("RGB").resize((WIN_W, WIN_H), Image.LANCZOS)
        canvas.paste(win, (WIN_X, WIN_Y))

        # 右栏：**她变成点，随歌词变形**
        panel = Image.new("RGB", (RW, RH), tk.BG)
        pts, shape = tl.cloud(t)
        field.draw_cloud(panel, pts, t, fe, seg=tl.seg, shape=shape)
        d = ImageDraw.Draw(panel)
        d.text((12, 9), f"form · {shape}", font=font(11), fill=tk.ui(0.5))
        d.rectangle([0, 0, RW - 1, RH - 1], outline=tk.rgba(tk.ui(0.22), 180), width=1)
        canvas.paste(panel, (RIGHT[0], RIGHT[1]))

        draw_chrome(canvas, t, fe, act_label(t))
        draw_lyrics(canvas, t, tl.lines)
        tk.post(canvas, None, trail=0.0, bloom=0.34).save(frames / f"f{i:05d}.png")
        if n % 96 == 0 or n == len(idx):
            el = time.time() - t0c
            print(f"  {n}/{len(idx)}  {n/el:.1f} 帧/秒  剩余 "
                  f"{max(0,len(idx)-n)/max(0.1,n/el):.0f}s", flush=True)

    print(f"  合成完成 {time.time()-t0c:.1f}s -> {frames}")

    if a.no_video or a.every > 1:
        return
    ff = audio.find_ffmpeg()
    silent = OUT / "field_silent.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-framerate", str(FPS),
                    "-start_number", str(idx[0]), "-i", str(frames / "f%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17",
                    str(silent)], check=True)
    final = OUT / "world_execute_me_field.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-i", str(silent),
                    "-ss", f"{a.t0:.3f}", "-t", f"{a.t1-a.t0:.3f}", "-i", str(SONG),
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", str(final)],
                   check=True)
    print(f"  -> {final}")


if __name__ == "__main__":
    main()

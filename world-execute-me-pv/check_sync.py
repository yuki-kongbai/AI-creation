#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查字幕与声音到底对不对得上。

两条独立的检查：
  1. 我的每行歌词时刻 vs 音频的**起音峰**（onset peak）
     对不上就说明时刻表错了
  2. 仓库骨架自己给的行时刻 vs 音频起音峰
     如果骨架也对不上，说明对齐方法有问题；如果骨架对得上，
     那就是我重建时刻表时引入的误差
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PV2))
sys.path.insert(0, str(HERE))

import audio  # noqa: E402

REPO = Path(r"D:\大肥鱼（deepseek）\.repo\world-execute-me-dsh-pv-main")


def onsets(t0: float, t1: float, n: int = 400):
    """在 [t0,t1] 里找 flux 的局部极大（起音）。"""
    rate = 48.039
    i0, i1 = int(t0 * rate), int(t1 * rate)
    xs, ys = [], []
    step = max(1, (i1 - i0) // n)
    prev = None
    for i in range(i0, i1, step):
        t = i / rate
        f = audio.at(t)
        v = f.flux
        if prev is not None and v > prev[1] and v > 0.10:
            xs.append(t)
            ys.append(v)
        prev = (t, v)
    return np.array(xs), np.array(ys)


def sec(tag: str) -> float:
    mm, rest = tag[1:].split(":")
    return int(mm) * 60 + float(rest[:-1])


def nearest(arr, t):
    if len(arr) == 0:
        return None, None
    i = int(np.argmin(np.abs(arr - t)))
    return arr[i], arr[i] - t


def main():
    skel = json.loads((REPO / "data" / "timing" / "lyrics_synced_notext.json")
                      .read_text(encoding="utf-8"))["lines"]
    mine = json.loads((HERE / "cache" / "lyrics_timed.json")
                      .read_text(encoding="utf-8"))

    # 用整首歌的起音峰做参照
    on, ov = onsets(0.0, 211.0)
    print(f"音频起音峰 {len(on)} 个（0–211s）\n")

    print("=== 1. 我的时刻表 vs 起音峰 ===")
    devs = []
    for r in mine:
        if r["src"] != "anchor":
            continue
        t = r["t"]
        if not (0 < t < 211):
            continue
        ot, d = nearest(on, t)
        devs.append(abs(d))
    if devs:
        a = np.array(devs)
        print(f"  锚点行 {len(a)} 行：平均偏差 {a.mean()*1000:.0f}ms  "
              f"中位 {np.median(a)*1000:.0f}ms  最大 {a.max()*1000:.0f}ms")
        print(f"  偏差 <120ms 的占 {(a<0.12).mean()*100:.0f}%")

    print("\n=== 2. 仓库骨架 vs 起音峰（对照组）===")
    devs2 = []
    for l in skel:
        t = sec(l["tag"])
        if not (0 < t < 211):
            continue
        ot, d = nearest(on, t)
        devs2.append(abs(d))
    if devs2:
        a2 = np.array(devs2)
        print(f"  骨架 {len(a2)} 行：平均偏差 {a2.mean()*1000:.0f}ms  "
              f"中位 {np.median(a2)*1000:.0f}ms  最大 {a2.max()*1000:.0f}ms")
        print(f"  偏差 <120ms 的占 {(a2<0.12).mean()*100:.0f}%")

    print("\n=== 3. 我的插值行（误差可能更大）===")
    devs3 = []
    for r in mine:
        if r["src"] not in ("interp", "tail", "count"):
            continue
        ot, d = nearest(on, r["t"])
        devs3.append(abs(d))
    if devs3:
        a3 = np.array(devs3)
        print(f"  非锚点行 {len(a3)} 行：平均偏差 {a3.mean()*1000:.0f}ms  "
              f"中位 {np.median(a3)*1000:.0f}ms  最大 {a3.max()*1000:.0f}ms")
        print(f"  偏差 <120ms 的占 {(a3<0.12).mean()*100:.0f}%")

    print("\n=== 4. 逐行抽查（偏差最大的 15 行）===")
    rows = []
    for r in mine:
        if not (0 < r["t"] < 211):
            continue
        ot, d = nearest(on, r["t"])
        rows.append((abs(d), r["t"], ot, r["en"], r["src"]))
    rows.sort(reverse=True)
    print(f"  {'我的时刻':>9} {'最近起音':>9} {'偏差ms':>8}  {'来源':<7} 行")
    for ad, t, ot, en, srcc in rows[:15]:
        print(f"  {t:>9.2f} {ot:>9.2f} {ad*1000:>+8.0f}  {srcc:<7} {en[:38]}")


if __name__ == "__main__":
    main()

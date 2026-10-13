#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""判定两个时刻文件哪个是对的。

两个文件对同一句歌词给出的时刻差 4–37 秒，不可能都对：
    lyrics_synced_notext.json   102 行，If I'm a set of points @ 34.54s
    word_timeline_notext.json    98 行，If I'm a set of points @ 29.77s

判据（不需要歌词文字，只需要音频）：
    正确的时刻表，其「每行起唱时刻」应当落在**人声能量较高**的位置。
    所以比较两版在这些时刻处的人声包络均值，与随机时刻的基线比。
    胜出的那一版，其起唱点能量应显著高于基线；错的那版会接近基线。

对照组必查：如果两版都接近基线，说明这个判据本身无效，不能下结论。
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
import measure_offset as MO  # noqa: E402

REPO = Path(r"D:\大肥鱼（deepseek）\.repo\world-execute-me-dsh-pv-main")


def main():
    x = MO.decode_mono(MO.MP3)
    t, e = MO.vocal_env(x)
    print(f"人声包络 {len(e)} 帧，覆盖 {t[-1]:.1f}s，均值 {e.mean():.4f}\n")

    def at(ts):
        idx = np.searchsorted(t, ts)
        idx = np.clip(idx, 0, len(e) - 1)
        return e[idx]

    # 载入两个时刻文件
    ws = json.loads((REPO / "data" / "timing" / "word_timeline_notext.json")
                    .read_text(encoding="utf-8"))["skeleton"]
    ls = json.loads((REPO / "data" / "timing" / "lyrics_synced_notext.json")
                    .read_text(encoding="utf-8"))["lines"]
    mm, rr = (lambda s: (int(s[1:].split(":")[0]) * 60 + float(s[1:].split(":")[1][:-1]),
                         None))(None) if False else (None, None)

    def sec(tag):
        a, b = tag[1:].split(":")
        return int(a) * 60 + float(b[:-1])

    w_t = np.array([l["start"] for l in ws["lines"]])
    w_t = w_t[(w_t > 0) & (w_t < t[-1])]
    l_t = np.array([sec(l["tag"]) for l in ls])
    l_t = l_t[(l_t > 0) & (l_t < t[-1])]

    # 随机基线
    rng = np.random.default_rng(7)
    base = np.array([e[rng.integers(0, len(e))] for _ in range(4000)])

    print(f"{'来源':<34} {'点数':>5} {'起唱点均值':>10} {'随机基线':>9} {'提升':>7}")
    print(f"{'随机基线':<34} {len(base):>5} {base.mean():>10.4f} "
          f"{base.mean():>9.4f} {'1.00×':>7}")
    for name, arr in (("word_timeline（逐词强制对齐）", w_t),
                      ("lyrics_synced（我一直在用的）", l_t)):
        v = at(arr)
        print(f"{name:<34} {len(arr):>5} {v.mean():>10.4f} "
              f"{base.mean():>9.4f} {v.mean()/base.mean():>6.2f}×")

    # 更严格的检验：只看每行的**前 0.4s**（起唱处能量应最高）
    print(f"\n更严格：每行前 0.4s 的人声能量")
    for name, arr in (("word_timeline", w_t), ("lyrics_synced", l_t)):
        vals = []
        for a in arr:
            sel = (t >= a) & (t < a + 0.4)
            if sel.sum() > 2:
                vals.append(e[sel].mean())
        vals = np.array(vals)
        # 随机对照：同样窗口长度，随机位置
        rnd = []
        for _ in range(len(vals)):
            a = rng.uniform(0, t[-1] - 0.4)
            sel = (t >= a) & (t < a + 0.4)
            rnd.append(e[sel].mean())
        rnd = np.array(rnd)
        win = (vals > rnd.mean()).mean()
        print(f"  {name:<20} 均值 {vals.mean():.4f}   随机 {rnd.mean():.4f}   "
              f"提升 {vals.mean()/rnd.mean():.2f}×   高于随机基线的比例 {win*100:.0f}%")

    # 直接看两版分歧最大处，用音频裁决
    print(f"\n=== 逐点裁决（两版差 >10s 的位置）===")
    print(f"{'word_timeline':>14} {'lyrics_synced':>14}   {'前者能量':>9} {'后者能量':>9}  胜")
    for i in range(0, min(len(w_t), len(l_t)), max(1, len(w_t) // 12)):
        a, b = w_t[i], l_t[i]
        if abs(a - b) < 10:
            continue
        ea, eb = at([a])[0], at([b])[0]
        win = "word" if ea > eb else "sync"
        print(f"{a:>14.2f} {b:>14.2f}   {ea:>9.4f} {eb:>9.4f}  {win}")


if __name__ == "__main__":
    main()

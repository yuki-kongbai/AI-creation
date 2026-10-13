#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""对位验证（设计值版）。

之前那版从**已渲染的帧**里反推版式位移，结果被窗口内部的打字/代码动画
污染（每帧 1 像素的边缘抖动全成了假阳性），怎么调阈值都不对。

改成直接算**设计值**：`expand.at(t)` 给出的窗口 x 与右栏右边 x。
这是版式的真值，没有任何噪声。判据：

    `一段缓动 = 一个重音` —— 每个动作段里，位移峰值必须出现在段的**起点**
    （缓动是 ease-out：起步最快）。若峰值落在段中，说明中间插了关键帧，
    重音被劈成了两个。
"""
from __future__ import annotations

import sys
from pathlib import Path

PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PV2))
sys.path.insert(0, str(HERE))

import clock as C  # noqa: E402
import expand  # noqa: E402

STEP = 1 / 240.0          # 采样步长：比一帧细，才看得出峰值位置
THR = 1.5                 # px/帧，低于此视为静止


def scan(t0: float, t1: float):
    prev = None
    segs, cur = [], None
    t = t0
    while t <= t1:
        a = expand.at(t)
        x, r = a["win_x"], a["right_x"] + a["right_w"]
        if prev is not None:
            d = (abs(x - prev[0]) + abs(r - prev[1])) / STEP / 24.0
            if d > THR:
                if cur is None:
                    cur = [t, t, d, t]
                else:
                    cur[1] = t
                    if d > cur[2]:
                        cur[2], cur[3] = d, t
            elif cur is not None:
                segs.append(cur)
                cur = None
        prev = (x, r)
        t += STEP
    if cur:
        segs.append(cur)
    return segs


def main():
    segs = scan(0.0, expand.duration())
    print(f"采样步长 {STEP*1000:.1f}ms   阈值 {THR} px/帧")
    print(f"\n{'段起':>8} {'段止':>8} {'起拍':>6} {'峰值':>8} {'峰值拍':>7} "
          f"{'峰在段头':>9}  判定")
    bad = 0
    for a, b, d, pk in segs:
        ba, bp = (a - C.FIRST_BEAT) / C.BEAT, (pk - C.FIRST_BEAT) / C.BEAT
        # 峰值应落在段起始的 1/3 之内（ease-out 的特征）
        head = (pk - a) / max(1e-6, b - a)
        ok = head <= 0.34
        if not ok:
            bad += 1
        print(f"{a:8.3f} {b:8.3f} {ba:6.1f} {d:8.1f} {bp:7.2f} "
              f"{head*100:8.0f}%  {'✓ 单重音' if ok else '✗ 重音被劈开'}")

    print(f"\n动作段 {len(segs)} 个，重音不在段头的 {bad} 个")
    print("\n拍点落位：")
    for a, b, d, pk in segs:
        k = round((a - C.FIRST_BEAT) / C.BEAT)
        bt = C.beat_t(k)
        dv = (a - bt) * 1000
        print(f"  段起 {a:7.3f}  最近拍 beat {k:>2} = {bt:7.3f}  偏差 {dv:+6.1f}ms")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

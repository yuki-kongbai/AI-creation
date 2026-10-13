#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""拍点对位检查。

三件事：
  1. 所有事件都落在**半拍网格**上（整拍或半拍，不是随手写的小数）
  2. 动作之间不撞车：她说完 → 右栏收 → 消息褪 → 窗口回中央，顺序不能乱
  3. 版式关键帧落在**整拍**上（版式动作比内容事件更需要"重音感"）
"""
from __future__ import annotations

import sys
from pathlib import Path

PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PV2))
sys.path.insert(0, str(HERE))

import clock as C  # noqa: E402
import dense_scene as ds  # noqa: E402
import expand  # noqa: E402

TOL = 1e-3


def beats(t: float) -> float:
    return (t - C.FIRST_BEAT) / C.BEAT


def on_half(t: float) -> bool:
    b = beats(t) * 2
    return abs(b - round(b)) < TOL


def on_int(t: float) -> bool:
    b = beats(t)
    return abs(b - round(b)) < TOL


def main() -> int:
    sc = ds.load(HERE / "content" / "scene08.json")
    bad = 0

    print("=== 1. 内容事件在半拍网格上 ===")
    for i, tn in enumerate(sc["turns"]):
        for k in ("at", "think_at", "text_at"):
            if k not in tn:
                continue
            t = tn[k]
            ok = on_half(t)
            if not ok:
                bad += 1
            print(f"  {'OK ' if ok else '✗  '} 轮{i} {k:<10} t={t:7.3f}  beat {beats(t):6.1f}")
        for k in ("tool", "code", "table"):
            if k in tn:
                t = tn[k]["at"]
                ok = on_half(t)
                if not ok:
                    bad += 1
                print(f"  {'OK ' if ok else '✗  '} 轮{i} {k:<10} t={t:7.3f}  beat {beats(t):6.1f}")
    t = sc["_clear"]["at"]
    ok = on_half(t)
    if not ok:
        bad += 1
    print(f"  {'OK ' if ok else '✗  '} _clear     t={t:7.3f}  beat {beats(t):6.1f}")

    print("\n=== 2. 版式关键帧在整拍上 ===")
    for (t, kx, kr) in expand.KEYS:
        ok = on_int(t)
        if not ok:
            bad += 1
        print(f"  {'OK ' if ok else '✗  '} t={t:7.3f}  beat {beats(t):6.1f}  x={kx:.2f} right={kr:.2f}")

    print("\n=== 3. 动作顺序 ===")
    last = sc["turns"][-1]
    done = last["text_at"] + len(last["text"]) / 46.0
    seq = [
        ("她说最后一句", done),
        ("右栏开始收", C.beat_t(48)),
        ("右栏收完", C.beat_t(53)),
        ("消息开始褪", sc["_clear"]["at"]),
        ("消息褪完", sc["_clear"]["at"] + sc["_clear"]["hold"]),
        ("窗口回中央", C.beat_t(61)),
    ]
    prev = -1.0
    for lab, t in seq:
        ok = t >= prev
        if not ok:
            bad += 1
        print(f"  {'OK ' if ok else '✗  '} {lab:<12} t={t:7.3f}  beat {beats(t):6.1f}")
        prev = t
    gap = C.beat_t(48) - done
    print(f"\n  她说完到右栏开始收：{gap:.2f}s = {beats(C.beat_t(48)) - beats(done):.1f} 拍")

    print(f"\n对位检查 {'通过' if bad == 0 else f'不通过（{bad} 处）'}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

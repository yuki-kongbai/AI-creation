#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""量窗口的信息密度（正确版）。

上一版把中位数当背景 —— 但框架色 #232324 比窗口底色 #151517 亮 14 级，
于是框架全被算成"内容"，ink 虚高到 40%（等于全屏有内容），显然不对。

正确做法：背景就是 token 里的 bg-base (#151517)。
  ink    明显亮于底色的像素占比        —— 真正"有东西"的地方
  panel  框架/卡片面（底色与框架色之间）—— 不算内容，但也不算空
  empty  接近底色的地方                —— 真的空
另外按区域分开统计：侧栏 / 消息区 / 输入区，才知道该往哪儿加内容。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
FRAMES = HERE / "out" / "frames"

BG = 0x15           # --dsw-alias-bg-base  #151517 的亮度
PANEL = 0x23        # --dsw-alias-bg-layer-1 #232324
# 区域（2x 截图坐标）：侧栏 / 消息区 / 输入区
ZONES = {"侧栏": (0, 264), "消息": (264, 840), "输入": (0, 840)}


def measure(p: Path):
    a = np.asarray(Image.open(p).convert("L"), dtype=np.float32)
    H, W = a.shape
    out = {}
    # 全局
    ink = float((a > BG + 60).mean())              # 明显亮 = 真文字/代码
    panel = float(((a > BG + 6) & (a <= BG + 60)).mean())
    empty = float((a <= BG + 6).mean())
    out["ink"], out["panel"], out["empty"] = ink, panel, empty
    # 消息区（去掉侧栏 132*2=264 像素）
    msg = a[:, 264:]
    out["msg_ink"] = float((msg > BG + 60).mean())
    msgrows = (msg > BG + 60).mean(axis=1)
    out["msg_rows"] = int((msgrows > 0.03).sum())
    # 侧栏
    side = a[:, :264]
    out["side_ink"] = float((side > BG + 60).mean())
    return out


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else "p"
    files = sorted(FRAMES.glob(f"{prefix}*.png"))
    if not files:
        print("没有帧")
        return
    step = max(1, len(files) // 10)
    sel = files[::step][:10]
    print(f"{'帧':>9} {'内容%':>7} {'框架%':>7} {'空%':>7} "
          f"{'消息内容%':>9} {'侧栏内容%':>9} {'消息文字行':>10}")
    acc = []
    for p in sel:
        m = measure(p)
        acc.append(m)
        n = int(p.stem[len(prefix):]) if p.stem[len(prefix):].isdigit() else 0
        print(f"{n/24:8.2f}s {m['ink']*100:6.2f} {m['panel']*100:6.2f} "
              f"{m['empty']*100:6.2f} {m['msg_ink']*100:8.2f} "
              f"{m['side_ink']*100:8.2f} {m['msg_rows']:10d}")
    print(f"\n{'平均':>9} {np.mean([m['ink'] for m in acc])*100:6.2f} "
          f"{np.mean([m['panel'] for m in acc])*100:6.2f} "
          f"{np.mean([m['empty'] for m in acc])*100:6.2f} "
          f"{np.mean([m['msg_ink'] for m in acc])*100:8.2f} "
          f"{np.mean([m['side_ink'] for m in acc])*100:8.2f} "
          f"{np.mean([m['msg_rows'] for m in acc]):10.1f}")
    print("\n诊断要点：消息区内容% 低于 6、侧栏内容% 低于 4，就是太空。")


if __name__ == "__main__":
    main()

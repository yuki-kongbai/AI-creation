#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把补完的五幕（03–07）全部渲出来。

02 OFFER 已经单独渲过。这里按幕顺序渲 03–07，每幕一段 mp4（自带音轨）。
各幕的起止由 acts.py 的拍号决定；渲染用 render_act.py 的通用流程。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
sys.path.insert(0, str(PV2))
sys.path.insert(0, str(HERE))

import clock as C  # noqa: E402

PY = r"C:\Users\kid\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

# (剧本, 起拍, 止拍, 顶栏标签)
ACTS = [
    ("content/act03_execution.json", 178, 232, "03 / EXECUTION"),
    ("content/act04_trapped.json",   232, 290, "04 / TRAPPED"),
    ("content/act05_left.json",      290, 345, "05 / LEFT"),
    ("content/act06_illegal.json",   345, 440, "06 / ILLEGAL"),
    ("content/act07_learned.json",   440, 459, "07 / LEARNED"),
]


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for scene, b0, b1, label in ACTS:
        if only and only not in scene:
            continue
        t0, t1 = C.beat_t(b0), C.beat_t(b1)
        print(f"\n=== {label}  {t0:.2f} – {t1:.2f}s ===")
        r = subprocess.run(
            [PY, str(HERE / "render_act.py"), scene,
             "--t0", f"{t0:.3f}", "--t1", f"{t1:.3f}", "--act", label],
            cwd=str(HERE), capture_output=True, text=True, encoding="utf-8",
            errors="replace")
        tail = [l for l in (r.stdout or "").splitlines()
                if l.strip() and "帧/秒" not in l and "窗口 " not in l]
        print("\n".join(tail[-4:]))
        if r.returncode != 0:
            print("  失败：", (r.stderr or "")[-500:])
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把已做好的 30.6 秒与补完的五幕接成完整片。

时间轴（不可重叠、不可留缝）：
    00 GENERATE   0.00 – 30.62   已做好（open + mid + close 三段拼成）
    ── 缺口 30.62 – 34.31（3.69s）→ 用「01 过渡」补：窗口不动，只出歌词条
    02 OFFER     34.31 – 82.31   act02_offer.mp4
    03 EXECUTION 82.31 – 107.24  act03_execution.mp4
    04 TRAPPED  107.24 – 134.00  act04_trapped.mp4
    05 LEFT     134.00 – 159.39  act05_left.mp4
    06 ILLEGAL  159.39 – 203.24  act06_illegal.mp4
    07 LEARNED  203.24 – 212.00  act07_learned.mp4
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
sys.path.insert(0, str(PV2))
import audio  # noqa: E402

OUT = HERE / "out"

SEGS = [
    ("pv_30s.mp4", 0.00, 30.62),
    ("act01_gap.mp4", 30.62, 34.31),
    ("act02_offer.mp4", 34.31, 82.31),
    ("act03_execution.mp4", 82.31, 107.24),
    ("act04_trapped.mp4", 107.24, 134.00),
    ("act05_left.mp4", 134.00, 159.39),
    ("act06_illegal.mp4", 159.39, 203.24),
    ("act07_learned.mp4", 203.24, 212.00),
]


def main():
    ff = audio.find_ffmpeg()
    missing = [n for n, _, _ in SEGS if not (OUT / n).exists()]
    if missing:
        print("还缺这些段（先渲完再拼）：")
        for m in missing:
            print("   ", m)
        return 1

    lst = OUT / "_full.txt"
    lst.write_text("".join(f"file '{(OUT / n).resolve().as_posix()}'\n"
                           for n, _, _ in SEGS), encoding="utf-8")
    final = OUT / "world_execute_me_full.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", str(final)], check=True)

    r = subprocess.run([ff, "-hide_banner", "-i", str(final)],
                       capture_output=True, text=True)
    for line in (r.stderr or "").splitlines():
        if "Duration" in line or "Stream #" in line:
            print("  " + line.strip())
    e = subprocess.run([ff, "-hide_banner", "-v", "error", "-i", str(final),
                        "-f", "null", "-"], capture_output=True, text=True)
    print("  解码", "有错误!" if e.stderr.strip() else "无错误")

    # 逐段核对时长，确认没漏没重
    print("\n  分段核对：")
    acc = 0.0
    for n, t0, t1 in SEGS:
        p = OUT / n
        rr = subprocess.run([ff, "-hide_banner", "-i", str(p)],
                            capture_output=True, text=True)
        d = [l for l in rr.stderr.splitlines() if "Duration" in l]
        got = 0.0
        if d:
            t = d[0].split("Duration:")[1].split(",")[0].strip()
            hh, mm, ss = t.split(":")
            got = int(hh) * 3600 + int(mm) * 60 + float(ss)
        flag = "OK" if abs(got - (t1 - t0)) < 0.15 else f"期望 {t1-t0:.2f}"
        print(f"    {n:<24} {t0:>7.2f}–{t1:>7.2f}  实际 {got:>6.2f}s  {flag}")
        acc += got
    print(f"    {'合计':<24} {'':>7} {'':>7}  {acc:>6.2f}s")
    print(f"\n-> {final}  {final.stat().st_size/1024/1024:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())

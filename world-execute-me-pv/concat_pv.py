#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把三段接成一支完整片子，并核对音画。

concat demuxer 的相对路径在不同 ffmpeg 构建上解析不一致，
所以列表里写绝对路径（这个坑踩过一次）。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PV2))
import audio  # noqa: E402

OUT = HERE / "out"
SEGS = ["open", "mid", "close"]


def main():
    ff = audio.find_ffmpeg()
    parts = [OUT / f"{n}.mp4" for n in SEGS]
    miss = [p for p in parts if not p.exists()]
    if miss:
        print("缺段:", *miss, sep="\n  ")
        return

    lst = OUT / "_concat.txt"
    lst.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in parts),
                   encoding="utf-8")
    final = OUT / "pv_30s.mp4"
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
    print(f"\n-> {final}  {final.stat().st_size/1024/1024:.2f} MB")


if __name__ == "__main__":
    main()

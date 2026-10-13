#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""给展开段配上音乐，编成可播放的 mp4。

音乐起点：展开段对应歌曲 0–4.7s（第一句唱词之前），
所以直接从曲子开头截同样长度即可，不需要淡入。
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
SONG = Path(r"D:\kuakewangpan\工具\bupan\Mili-world.execute(me);.mp3")


def main():
    ff = audio.find_ffmpeg()
    silent = OUT / "expand_silent.mp4"
    final = OUT / "expand.mp4"
    dur = float(sys.argv[1]) if len(sys.argv) > 1 else 4.7
    off = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0

    if not silent.exists():
        print(f"缺少 {silent}")
        return
    if not SONG.exists():
        print(f"缺少音源 {SONG}")
        return

    cmd = [
        ff, "-v", "error", "-y",
        "-i", str(silent),
        "-ss", f"{off:.3f}", "-t", f"{dur:.3f}", "-i", str(SONG),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(final),
    ]
    subprocess.run(cmd, check=True)
    r = subprocess.run([ff, "-hide_banner", "-i", str(final)],
                       capture_output=True, text=True)
    for line in (r.stderr or "").splitlines():
        if "Duration" in line or "Stream #" in line:
            print("  " + line.strip())
    print(f"-> {final}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""build.py —— 构建入口。

    python build.py check     检查输入齐不齐
    python build.py lyrics    合成歌词时间表
    python build.py preview   只渲一小段试片
    python build.py render    整片渲染
    python build.py encode    编码成片
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
INP = HERE / "input"
OUT = HERE / "out"
SONG = INP / "song.mp3"


def check() -> int:
    ok = True
    for p, what in ((SONG, "歌曲"), (INP / "lyrics_en.txt", "英文歌词"),
                    (INP / "lyrics_zh.json", "中文对照"),
                    (HERE / "data" / "lyrics_timed_notext.json", "时间表(仓库自带)"),
                    (HERE / "data" / "her_points.npy", "她的轮廓点云(仓库自带)")):
        exists = p.exists()
        ok &= exists
        print(f"  [{'OK' if exists else '缺'}] {what:<22} {p.relative_to(HERE)}")
    print("\n  可以开始构建" if ok else "\n  先把上面缺的补上（见 input/README.md）")
    return 0 if ok else 1


def lyrics() -> int:
    """把不含文字的时间表和本机歌词合成。"""
    tl = json.loads((HERE / "data" / "lyrics_timed_notext.json")
                    .read_text(encoding="utf-8"))
    en = [l.strip() for l in (INP / "lyrics_en.txt").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    zh = json.loads((INP / "lyrics_zh.json").read_text(encoding="utf-8"))
    if not (len(en) == len(zh) == len(tl)):
        print(f"  行数不匹配：时间表 {len(tl)} / 英文 {len(en)} / 中文 {len(zh)}")
        return 1
    out = [{"i": k + 1, "t": r["t"], "end": r.get("end"), "src": r.get("src"),
            "en": en[k], "zh": zh[k] if isinstance(zh, list) else zh[str(k + 1)]}
           for k, r in enumerate(tl)]
    (HERE / "cache").mkdir(exist_ok=True)
    (HERE / "cache" / "lyrics_timed.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / "input" / "_lyrics_raw.txt").write_text("\n".join(en), encoding="utf-8")
    print(f"  -> cache/lyrics_timed.json  {len(out)} 行")
    return 0


def _run(args: list[str]) -> int:
    print("  $", " ".join(args))
    return subprocess.call([sys.executable, str(HERE / "render_final.py")] + args,
                           cwd=str(HERE))


def preview() -> int:
    return _run(["--t0", "28", "--t1", "34", "--reuse-win", "--keep-frames"])


def render() -> int:
    OUT.mkdir(exist_ok=True)
    return _run(["--t0", "0", "--t1", "212"])


def encode() -> int:
    """把 out/frames_final 编码成片。"""
    ff = _ffmpeg()
    frames, sil = OUT / "frames_final", OUT / "silent.mp4"
    final = OUT / "world_execute_me_final.mp4"
    subprocess.check_call([ff, "-v", "error", "-y", "-framerate", "24",
                           "-start_number", "0", "-i", str(frames / "f%05d.png"),
                           "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                           "-pix_fmt", "yuv420p", str(sil)])
    subprocess.check_call([ff, "-v", "error", "-y", "-i", str(sil),
                           "-i", str(SONG), "-map", "0:v:0", "-map", "1:a:0",
                           "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                           "-shortest", str(final)])
    print(f"  -> {final}")
    return 0


def _ffmpeg() -> str:
    for c in ("ffmpeg", str(HERE / ".tools" / "ffmpeg.exe")):
        try:
            subprocess.run([c, "-version"], capture_output=True, check=True)
            return c
        except Exception:
            continue
    sys.exit("  找不到 ffmpeg，请装一个并放进 PATH")


STEPS = {"check": check, "lyrics": lyrics, "preview": preview,
         "render": render, "encode": encode}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="world.execute(me); PV 构建")
    ap.add_argument("step", choices=list(STEPS), nargs="?", default="check")
    a = ap.parse_args()
    sys.exit(STEPS[a.step]() or 0)

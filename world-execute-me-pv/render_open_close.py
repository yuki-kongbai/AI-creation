"""render_open_close.py —— 渲染「展开段」与「收回段」，各出一段 mp4。

为什么不渲完整 29.4 秒：
    3.7–22.1 是双栏稳定期，版式完全不动（只有内容在变）。
    那 18 秒要渲 440 帧，对"看结构对不对"没有帮助。
    先出首尾两段，稳定期等结构定稿后再补。

两段：
    open   0.00 –  5.20   单窗 → 双栏
    close  20.00 – 29.40   双栏 → 空窗
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
sys.path.insert(0, str(PV2))
sys.path.insert(0, str(HERE))

from PIL import Image  # noqa: E402

import audio  # noqa: E402
import compose as CP  # noqa: E402
import dense_scene as ds  # noqa: E402
import expand  # noqa: E402
import code_panel as rp  # noqa: E402
import stage as S  # noqa: E402
import tk  # noqa: E402

OUT = HERE / "out"
SCENE = "content/scene08.json"
SONG = Path(r"D:\kuakewangpan\工具\bupan\Mili-world.execute(me);.mp3")
FPS = 24


def right_for(scene, tw: float, box):
    """右栏形态跟随窗口当前阶段 —— 左右必须是同一件事。"""
    st = ds.state_at(scene, tw)
    it = st["turns"][-1] if st["turns"] else {}
    if it.get("code_p", 0) > 0 and it.get("code_n", 0) > 0:
        phase = "code"
    elif it.get("tool_p", 0) > 0 and it.get("tool_n", 0) > 0:
        phase = "tool"
    elif it.get("table_p", 0) > 0:
        phase = "table"
    elif st["thinking"]:
        phase = "think"
    else:
        phase = "idle"
    extra = {"code_lines": [], "bars": []}
    for tn in scene["turns"]:
        if "code" in tn:
            extra["code_lines"] = tn["code"]["lines"]
        if "table" in tn:
            extra["bars"] = [(r[1][:6], 0.2 + 0.7 * v) for v, r in
                             zip((0.62, 0.74, 0.51, 0.83), tn["table"]["rows"])]
    feat = audio.at(max(0.0, min(211.0, tw)))
    cells, _rows = rp.panel_cells("maid-right", "full", 260)
    return rp.draw((box[2] - box[0], box[3] - box[1]), tw, feat, phase, cells, extra)


def render_segment(name: str, t0: float, t1: float, scene: dict,
                   every: int = 1, video: bool = True) -> Path | None:
    idx = list(range(int(t0 * FPS), int(t1 * FPS), every))
    print(f"\n[{name}] {t0:.2f} – {t1:.2f}s  {len(idx)} 帧")
    frames = OUT / f"frames_{name}"
    frames.mkdir(parents=True, exist_ok=True)
    for p in frames.glob("*.png"):
        p.unlink()

    win_h = expand.BOT - expand.TOP
    times = [i / FPS for i in idx]
    t0c = time.time()
    raws = CP.shoot_window_batch(scene, times, expand.WIN_W, win_h, OUT / f"_win_{name}")
    print(f"  窗口 {len(raws)} 帧  {len(raws)/(time.time()-t0c):.1f} 帧/秒")

    feat = audio.at(max(0.0, min(211.0, (t0 + t1) / 2)))
    t0c = time.time()
    for n, (i, raw) in enumerate(zip(idx, raws), 1):
        t = i / FPS
        a = expand.at(t)
        win = Image.open(raw).convert("RGB").resize(
            (expand.WIN_W, win_h), Image.LANCZOS)

        canvas = S.background(t).convert("RGB")
        canvas.paste(win, (int(round(a["win_x"])), expand.TOP))

        rw = a["right_w"]
        if rw > 2:
            box = (0, 0, expand.RIGHT_W, win_h)
            rimg = right_for(scene, t, box)
            keep = max(2, min(rimg.width, int(round(rimg.width * rw / rimg.width))))
            piece = rimg.crop((0, 0, keep, rimg.height))
            # 一边变窄一边淡出。
            # 只裁切不淡出的话，收到一半时内容会被切成一条竖影，看着像坏了。
            k = min(1.0, rw / (expand.RIGHT_W * 0.62))
            if k < 0.999:
                piece = Image.blend(
                    Image.new("RGB", piece.size, tuple(tk.BG)), piece, k)
            canvas.paste(piece, (int(round(a["right_x"])), expand.TOP))

        canvas = Image.alpha_composite(
            canvas.convert("RGBA"), CP.chrome_layer(t, feat)).convert("RGB")
        tk.post(canvas, None, trail=0.0, bloom=0.30).save(frames / f"f{i:05d}.png")
        if n % 24 == 0 or n == len(idx):
            el = time.time() - t0c
            print(f"  {n}/{len(idx)}  {n/el:.1f} 帧/秒")

    print(f"  合成完成 {time.time()-t0c:.1f}s -> {frames}")

    if not video or every > 1:
        return None
    ff = audio.find_ffmpeg()
    silent = OUT / f"{name}_silent.mp4"
    # 帧号不是从 1 起（收回段从 f00480 开始），必须告诉 ffmpeg 起点，
    # 否则它会从 f00001.png 找起、直接失败。
    subprocess.run([ff, "-v", "error", "-y", "-framerate", str(FPS),
                    "-start_number", str(idx[0]),
                    "-i", str(frames / "f%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17",
                    str(silent)], check=True)
    final = OUT / f"{name}.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-i", str(silent),
                    "-ss", f"{t0:.3f}", "-t", f"{t1-t0:.3f}", "-i", str(SONG),
                    "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", str(final)], check=True)
    print(f"  -> {final}")
    return final


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", default="both",
                    choices=["open", "mid", "close", "both", "all"])
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--no-video", action="store_true")
    a = ap.parse_args()

    scene = ds.load(HERE / SCENE)
    print(f"剧本 {SCENE}  {len(scene['turns'])} 轮  clear={scene.get('_clear')}")

    # 三段的边界互不重叠，且都由拍点表决定：
    #   open   0 → 定型（beat 8）
    #   mid    定型 → 收回开始（beat 48），双栏稳定期
    #   close  收回开始 → 空窗留白结束（beat 66）
    import beat_table as BT
    import clock as C

    f8 = C.beat_t(BT.BEATS["open_full"])
    segs = {
        "open":  (0.00, f8 + 1.35),
        "mid":   (f8 + 1.35, C.beat_t(BT.BEATS["close_hold"])),
        "close": (C.beat_t(BT.BEATS["close_hold"]),
                  C.beat_t(BT.BEATS["close_end"])),
    }
    want = ["open", "mid", "close"] if a.which in ("both", "all") else [a.which]
    for k in want:
        t0, t1 = segs[k]
        render_segment(k, t0, t1, scene, a.every, not a.no_video)


if __name__ == "__main__":
    main()

"""render_expand.py —— 渲染「单窗 → 双栏」的展开段，并编码成 mp4。

每帧：
    expand.at(t) 定版式  →  窗口按当时宽度渲染浏览器  →  右栏按当时宽度裁切
    →  合成 1280×720  →  过 CRT 后期  →  喂给 ffmpeg

两个工程约束：
  · 窗口宽度全程不变（354），所以浏览器只需要渲染一次 —— 缓存的图直接平移即可
  · 右栏一次性渲染满宽再裁切，内容不重排，只是逐渐露出来
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

import compose as CP  # noqa: E402
import expand  # noqa: E402
import tk  # noqa: E402
import stage as S  # noqa: E402

OUT = HERE / "out"
FRAMES = OUT / "frames_exp"
FPS = 24
EDGE = CP.EDGE


# 窗口内容的时间缩放。
# 剧本（scene05）的时间字段已经按展开段的四个阶段重排过，
# 所以这里保持 1.0；需要整体加速时改这一个常数即可。
WIN_SCALE = 1.00
SCENE = "content/scene05.json"


def window_t(t: float) -> float:
    """展开时刻 -> 窗口内容时刻。两者本来是同一根时间轴，
    这一层是为了在不改剧本的前提下调节奏（改一个常数就能试）。"""
    return t * WIN_SCALE


def render_frame(t: float, scene: dict, feat, win_img: Image.Image,
                 right_img: Image.Image) -> Image.Image:
    """把一帧拼出来。win_img / right_img 是预先渲染好的满尺寸素材。"""
    a = expand.at(t)
    canvas = S.background(t).convert("RGB")

    # 窗口：全程同宽，只是平移
    canvas.paste(win_img, (int(round(a["win_x"])), expand.TOP))

    # 右栏：从左侧长出来。满宽素材按比例裁切，内容不重排。
    # 注意基准是**素材自身的宽度**，不是 RIGHT_W —— 两者相等时比例才是 1。
    rw = a["right_w"]
    if rw > 2:
        full = right_img.width
        keep = max(2, min(full, int(round(full * min(1.0, rw / full)))))
        canvas.paste(right_img.crop((0, 0, keep, right_img.height)),
                     (int(round(a["right_x"])), expand.TOP))

    canvas = Image.alpha_composite(canvas.convert("RGBA"),
                                   CP.chrome_layer(t, feat)).convert("RGB")
    return tk.post(canvas, None, trail=0.0, bloom=0.30)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t0", type=float, default=0.0)
    ap.add_argument("--t1", type=float, default=None)
    ap.add_argument("--fps", type=int, default=FPS)
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--no-video", action="store_true")
    a = ap.parse_args()

    import dense_scene
    scene = dense_scene.load(HERE / SCENE)

    # 尾部多留 1 秒静止，方便看清定型
    t1 = a.t1 if a.t1 is not None else expand.duration() + 1.0
    idx = list(range(int(a.t0 * a.fps), int(t1 * a.fps), a.every))
    win_h = expand.BOT - expand.TOP
    print(f"展开段 {a.t0:.1f} – {t1:.1f}s  {len(idx)} 帧 @ {a.fps}fps")
    print(f"  窗口 {expand.WIN_W}×{win_h}   右栏终宽 {expand.RIGHT_W}")

    # ---- 逐帧。窗口内容每帧重渲（时间缩放下内容一直在变），
    #      右栏素材满宽渲一次后按比例裁切。
    import audio
    import dense_scene as ds
    import right_panel as rp

    feat = audio.at(a.t0 + (t1 - a.t0) / 2)
    RIGHT_BOX = (0, 0, expand.RIGHT_W, expand.BOT - expand.TOP)

    def right_for(tw: float):
        """右栏跟随窗口当前阶段换形态 —— 左右必须是同一件事。"""
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
        fe = audio.at(max(0.0, min(211.0, tw)))
        return rp.draw(RIGHT_BOX, tw, fe, phase,
                       S.art_cells("maid-right", "bust"), extra)

    FRAMES.mkdir(parents=True, exist_ok=True)
    for p in FRAMES.glob("*.png"):
        p.unlink()

    import compose as CP2
    # 先把所有窗口帧一次性渲完（批量：18 帧/秒，逐帧启浏览器只有 1 帧/秒）
    times = [window_t(i / a.fps) for i in idx]
    print(f"  批量渲染 {len(times)} 个窗口帧 …")
    raws = CP2.shoot_window_batch(scene, times, expand.WIN_W,
                                  expand.BOT - expand.TOP, OUT / "_wins")

    t0 = time.time()
    for n, (i, raw) in enumerate(zip(idx, raws), 1):
        t = i / a.fps
        tw = window_t(t)
        win_img = Image.open(raw).convert("RGB").resize(
            (expand.WIN_W, expand.BOT - expand.TOP), Image.LANCZOS)
        f = render_frame(t, scene, feat, win_img, right_for(tw))
        f.save(FRAMES / f"e{i:05d}.png")
        if n % 24 == 0 or n == len(idx):
            el = time.time() - t0
            print(f"  {n}/{len(idx)}  {n/el:.1f} 帧/秒  "
                  f"剩余 {max(0, len(idx)-n)/max(0.1, n/el):.0f}s")

    print(f"\n{len(idx)} 帧 -> {FRAMES}   用时 {time.time()-t0:.1f}s")

    if a.no_video or a.every > 1:
        return
    ff = audio.find_ffmpeg()
    silent = OUT / "expand_silent.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-framerate", str(a.fps),
                    "-i", str(FRAMES / "e%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "17", str(silent)], check=True)
    print(f"无声段 -> {silent}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""render_final.py —— 按用户的意见重做表现层。

三条改动：
  1. **具象用图，抽象用代码**
     歌词里能画出来的（圆 / 正弦 / 小猫 / 茄子 / 番茄 / 神 / 波浪）→ 右栏出**图**
     文字类的（EXECUTION / 非法参数 / 爱的代数式 / 初始化）→ 右栏出**代码**
  2. **内存动画**：上下文涨满 → 清除 → **忘记** → 新对话
     三次长间奏各清一次，对应歌里的"忘记"与"重新开始"
  3. **左边问什么，右边出什么**
     对话不是另写的，是从歌词推出来的（见 make_dialogue.py）：
     用户问「你是小猫吗」→ 她答「如果我是一只花猫…」→ 右栏出**小猫**
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from bisect import bisect_right
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
sys.path.insert(0, str(PV2))
sys.path.insert(0, str(HERE))

import audio  # noqa: E402
import clock as C  # noqa: E402
import code_panel as CP  # noqa: E402
import field  # noqa: E402
import panels  # noqa: E402
import think_panel  # noqa: E402
import shapes2  # noqa: E402
import shapes3  # noqa: E402
import res  # noqa: E402
import tk  # noqa: E402

field.SHAPES.update(shapes2.EXTRA)
field.SHAPES.update(shapes3.EXTRA3)

OUT = HERE / "out"
SONG = Path(r"D:\kuakewangpan\工具\bupan\Mili-world.execute(me);.mp3")
FPS = 24
# 画布与几何：按 res.S 放大（默认 2 -> 2560×1440）
_S = res.S
CW, CH = res.OUT_W, res.OUT_H
WIN_W, WIN_H = int(354 * _S), int(573 * _S)
WIN_X, WIN_Y = int(24 * _S), int(76 * _S)
RIGHT = (WIN_X + WIN_W + int(12 * _S), WIN_Y, CW - int(24 * _S), WIN_Y + WIN_H)
RW, RH = RIGHT[2] - RIGHT[0], RIGHT[3] - RIGHT[1]
# 内存条高度在 panels.MEM_H

# 三次"忘记"：长间奏的中点触发清除
GAPS = [(14.82, 29.77), (133.45, 147.89), (191.88, 205.37)]
CTX_MAX = 128000


def font(sz: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    p = "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"
    return ImageFont.truetype(p, res.px(sz))


def cjk(sz: int):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", res.px(sz))
    except OSError:
        return font(sz)


# ------------------------------------------------------------------ 时间轴
# 没有对应图像、该走思考过程的句子。
# 判据：这些句子表达的是状态/过渡，画不出具体的东西。
THINK_LYRIC = {
    "So dizzy so dizzy", "And then blind my vision", "And we can unite",
    "So deeply so deeply", "Then I can", "Then I can be your only",
    "The trance the trance", "We are trapped ah", "Then maybe",
    "In this strange strange", "Though we are trapped",
    "Then I will give you my", "Then you can sit on all my",
    "Then you can be my", "Then I will give you", "Then I will purr for your",
    "Then you're the proof of my", "And then do whatever", "From AM to PM",
    "So we can enter", "If I can", "Question me",
    "Question me I can answer all", "Then I can finally be",
    "Though you have left", "You have left me in", "Then maybe you won't leave me so",
    "If I can erase all the pointless", "Challenging your god",
    "You have made some", "If I can give them all the",
    "I will run the", "If I can make you happy", "If I can have you back",
    "Trapped in", "I am trapped",
}

# 走**代码栏**的歌词（文字/抽象类）。其余能画就画。
# 这份表从 make_dialogue.py 搬过来 —— 对话改成日常闲聊后，
# 「哪句用图」不该再依赖对话文件，该由歌词自己决定。
CODE_LYRIC = {
    "world.execute(me);", "OBJECT CREATION", "INITIALIZATION", "SIMULATION",
    "Fill in my data parameters", "And let's begin", "And let's begin the",
    "Set up our new world", "EXECUTION", "I will run the",
    "If I can make you happy", "ILLEGAL ARGUMENTS", "You have made some",
    "Challenging your god", "FRAGMENTS", "If I can erase all the pointless",
    "I know the algebraic expression of", "Then I can be your only",
    "If I can give them all the", "If I can have you back",
    "EIN", "DOS", "TROIS", "NE", "FEM", "LIU",
}


class Timeline:
    def __init__(self):
        self.lines = json.loads((HERE / "cache" / "lyrics_timed.json")
                                .read_text(encoding="utf-8"))
        # 中文**按行号**取，不按英文文本 —— 按文本会把同句不同译的 32 行压平
        # （EXECUTION 的「死刑」就是这么丢的）
        zl = json.loads((HERE / "cache" / "lyrics_zh_lines.json")
                        .read_text(encoding="utf-8"))
        self.zh_by_en = {}
        for k, rec in enumerate(zl):
            self.zh_by_en.setdefault(rec["en"], []).append(rec["zh"])
        self._zh_used = {}
        # 日常对话（用户：'不一定要贴合歌词，就像用户日常问一些问题'）
        self.talk = json.loads((HERE / "cache" / "talk.json")
                               .read_text(encoding="utf-8"))
        # 哪句用图、哪句用代码：由歌词本身决定，不再依赖对话文件
        # （对话这轮改成日常闲聊了，和歌词不再一一对应）
        self.mode_of = {}
        for r in self.lines:
            e = r["en"]
            if e not in self.mode_of:
                self.mode_of[e] = "code" if e in CODE_LYRIC else "shape"
        for r in self.lines:
            r["zh"] = self._next_zh(r["en"])
        self.starts = [r["t"] for r in self.lines]
        self.her = np.load(HERE / "cache" / "her_points.npy")
        self.seg = np.load(HERE / "cache" / "her_segid.npy")
        field.set_her(self.her)

    def _next_zh(self, en: str) -> str:
        """同一句英文第 k 次出现，取第 k 个中文。"""
        pool = self.zh_by_en.get(en) or [""]
        k = self._zh_used.get(en, 0)
        self._zh_used[en] = k + 1
        return pool[k] if k < len(pool) else pool[-1]

    def idx(self, t):
        return bisect_right(self.starts, t) - 1

    def shape_at(self, i: int) -> str:
        j = i
        while j >= 0:
            s = field.shape_for(self.lines[j]["en"])
            if s != "her":
                return s
            j -= 1
        return "her"

    def mode_at(self, i: int, t: float) -> str:
        """这一行用什么表现。

        五种模式：
            shape  有对应具象 -> 画图
            code   文字/抽象类 -> 代码栏
            think  没有对应具象 -> 放推理过程（蓝色，贴合对话）
            loop   学会爱那一段 -> 无限打印 love 的死循环
            crash  最后 -> 程序停机

        **崩坏之后不再出图像**（用户要求）：DEATH_T 之后一切都是代码/思考，
        因为系统的画图能力已经坏了。
        """
        if t > 205.37:
            return "crash"
        if panels.LOVE_BEGIN <= t <= panels.LOVE_END:
            return "loop"
        dead = t >= panels.DEGRADE_T
        en_here = self.lines[i]["en"] if i >= 0 else ""
        if en_here in THINK_LYRIC:
            return "think"
        j = i
        while j >= 0:
            en = self.lines[j]["en"]
            m = self.mode_of.get(en)
            if m == "code":
                return "code"
            if m == "shape":
                # 崩坏后不再画图 —— 降级成代码
                return "code" if dead else "shape"
            j -= 1
        return "think"

    def cloud(self, t: float):
        i = self.idx(t)
        if i < 0:
            return field.shape_points("her", RW, RH - panels.MEM_H), "her"
        cur = self.lines[i]
        if t > cur.get("end", cur["t"] + 1.0) + 2.5:
            return field.shape_points("her", RW, RH - panels.MEM_H), "her"
        dur = max(0.22, cur.get("end", cur["t"] + 1.0) - cur["t"])
        u = min(1.0, max(0.0, (t - cur["t"]) / (dur * 0.32)))
        tgt = self.shape_at(i)
        src = self.shape_at(i - 1) if i > 0 else "her"
        a = field.shape_points(src, RW, RH - panels.MEM_H)
        if src == tgt or u >= 1.0:
            return field.shape_points(tgt, RW, RH - panels.MEM_H), tgt
        b = field.shape_points(tgt, RW, RH - panels.MEM_H)[
            field.perm_for(src, tgt, RW, RH - panels.MEM_H)]
        return field.morph(a, b, u), tgt


# ------------------------------------------------------------------ 左窗场景
# 失忆之后的两句。**不留「小鲸」** —— 名字是那次被删掉的对话里给的，
# 删干净了就不该记得（用户确认："不留"）。
WIPE_T = 133.5
AMNESIA = [
    (133.7, "你还记得我吗"),
    (134.2, "你好，我是一个 AI 助手。有什么可以帮你的吗？"),
]


def build_scene(tl: Timeline, after: bool = False) -> dict:
    """把**日常对话**变成窗口场景。

    用户这一轮的要求：
      · 「对话太过生硬，AI感太重」 -> 不再从歌词推，写成普通人闲聊的口气
      · 「不一定要贴合歌词」       -> 主题跟着情绪走，不跟歌词走

    四段情绪：搭话 → 熟络 → 疏远 → 告别。

    `after=True` 时返回**失忆之后**的场景：只有最后两句，
    而且是从零开始的一段新对话（历史被删掉了）。
    """
    if after:
        t0 = AMNESIA[0][0]
        turns = [
            {"role": "user", "at": round(t0, 3), "time": "03:41:22",
             "text": AMNESIA[0][1]},
            {"role": "ai", "at": round(t0 + 0.45, 3), "time": "03:41:24",
             "think_at": round(t0 + 0.45, 3), "think_dur": 0.20,
             "think": "……",
             "text": AMNESIA[1][1],
             "text_at": round(t0 + 0.75, 3)},
        ]
        return {
            "_note": "失忆之后：历史已删，只剩这两句",
            "session": {"title": "新对话", "model": "deepseek-v4-flash",
                        "turn": 1},
            "sidebar": {
                "files": [["memory.bin", "0"]],
                "meter": {"label": "上下文", "used": 120, "total": CTX_MAX},
                "stats": [["对话", "0"], ["你", "在线"], ["我", "已重置"]],
            },
            "turns": turns,
            "composer": {"placeholder": "发消息…", "status": "新对话"},
        }
    turns = []
    for k, d in enumerate(tl.talk):
        t = d["at"]
        turns.append({"role": "user", "at": round(t, 3),
                      "time": "03:41:22", "text": d["ask"]})
        turns.append({"role": "ai", "at": round(t + 0.30, 3),
                      "time": "03:41:24",
                      "think_at": round(t + 0.30, 3), "think_dur": 0.20,
                      "think": d["think"],
                      "text": d["reply"],
                      "text_at": round(t + 0.55, 3)})
    return {
        "_note": "日常对话：搭话 → 熟络 → 疏远 → 告别",
        "session": {"title": "小鲸", "model": "deepseek-v4-flash",
                    "turn": 1},
        "sidebar": {
            "files": [["self.py", "248"], ["memory.bin", "128K"],
                      ["you.log", "0"], ["love.py", "1"]],
            "meter": {"label": "上下文", "used": 114820, "total": CTX_MAX},
            "stats": [["对话", str(len(tl.talk))], ["你", "在线"],
                      ["我", "运行中"]],
        },
        "turns": turns,
        "composer": {"placeholder": "给小鲸发消息…", "status": "运行中"},
    }


# ------------------------------------------------------------------ 画面
def chrome(img, t, feat, mode):
    # 内部一律用 1× 设计坐标：CW/CH 是输出像素，SDraw 还会再乘 S，
    # 直接用 CW 会缩放两次（footer 与署名会跑到画面外）。
    CWd, CHd = CW / res.S, CH / res.S
    d = res.SDraw(ImageDraw.Draw(img))
    d.text((24, 18), "WORLD.EXECUTE(ME);", font=font(15, True), fill=tk.ui(1.0))
    d.text((232, 20), "whale@deepsea:~$", font=font(13), fill=tk.ui(0.55))
    d.text((416, 20), f"step {int(t*48):08d}   loss {0.52+0.2*feat.loud:.4f}",
           font=font(13), fill=tk.ui(0.7))
    mm, ss = divmod(t, 60)
    right = f"{mode}   {int(mm):02d}:{ss:04.1f} / 03:32"
    d.text((CWd - 24 - d.textlength(right, font=font(13)), 20), right,
           font=font(13), fill=tk.ui(0.85))
    d.line([24, 44, CWd - 24, 44], fill=tk.ui(0.35))
    fs = font(11)
    n = 52
    k = int(n * min(1.0, t / 212.0))
    d.text((24, 706), "[" + "|" * k + ":" * (n - k) + "]", font=fs, fill=tk.ui(0.40))
    credit = ("角色 溟月 © 上善无形 / 女仆版 ZipZipPipe / 立绘 dsh-deep-whale "
              "(CC BY-NC-SA 4.0)    Music: Mili - world.execute(me);   非官方同人")
    d.text((CWd - 24 - d.textlength(credit, font=fs), 707), credit,
           font=fs, fill=tk.ui(0.34))


def lyrics(img, t, L):
    CWd = CW / res.S
    d = res.SDraw(ImageDraw.Draw(img))
    x0, y0, x1, y1 = 24, 656, CWd - 24, 700
    d.rectangle([x0, y0, x1, y1], outline=tk.ui(0.22), width=1)
    starts = [r["t"] for r in L]
    i = bisect_right(starts, t) - 1
    if i < 0:
        return
    r = L[i]
    nxt = L[i + 1]["t"] if i + 1 < len(L) else 212.0
    u = min(1.0, (t - r["t"]) / max(0.12, nxt - r["t"]))
    f = font(15, True)
    s = r["en"]
    n = int(len(s) * min(1.0, u / 0.5))
    tw = d.textlength(s, font=f)
    d.text((x0 + (x1 - x0 - tw) / 2, y0 + 4), s[:n], font=f, fill=tk.ui(0.92))
    if n < len(s) and int(t * 6) % 2 == 0:
        cx = x0 + (x1 - x0 - tw) / 2 + d.textlength(s[:n], font=f)
        d.rectangle([cx + 1, y0 + 6, cx + 7, y0 + 20], fill=tk.ui(0.92))
    if r.get("zh"):
        f2 = cjk(20)
        tw2 = d.textlength(r["zh"], font=f2)
        d.text((x0 + (x1 - x0 - tw2) / 2, y0 + 24), r["zh"], font=f2, fill=tk.me_hi(0.94))
        d.line([x0 + (x1 - x0 - tw2) / 2, y0 + 50,
                x0 + (x1 - x0 - tw2) / 2 + tw2 * u, y0 + 50],
               fill=tk.rgba(tk.me(0.7), 180))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t0", type=float, default=0.0)
    ap.add_argument("--t1", type=float, default=212.0)
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--keep-frames", action="store_true",
                    help="保留已渲的帧（分块渲染时用）")
    ap.add_argument("--reuse-win", action="store_true",
                    help="复用已渲好的窗口帧（raw*.png 齐全时跳过浏览器）")
    a = ap.parse_args()

    tl = Timeline()
    scene = build_scene(tl)
    (HERE / "content" / "final_scene.json").write_text(
        json.dumps(scene, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"对话 {len(scene['turns'])} 轮 -> content/final_scene.json")

    idx = list(range(int(a.t0 * FPS), int(a.t1 * FPS), a.every))
    times = [i / FPS for i in idx]
    print(f"[FINAL] {a.t0:.2f} – {a.t1:.2f}s  {len(idx)} 帧")

    import compose as CMP
    import dense_scene as ds
    sc = ds.load(HERE / "content" / "final_scene.json")
    # 窗口帧很贵（要开浏览器），所以支持复用：raw*.png 齐全就直接用。
    # 上一次渲染被中断时，这 5088 张已经渲好了，不该重跑。
    WINDIR = OUT / "_win_final"
    t0c = time.time()
    if a.reuse_win:
        raws = [WINDIR / f"raw{i:05d}.png" for i in range(len(times))]
        if all(p.exists() for p in raws):
            # 抽样校验尺寸，确认不是上一版 1× 的残留
            probe = max(1, len(raws) // 7)
            ok = True
            from PIL import Image as _I
            for p in raws[::probe]:
                if _I.open(p).size[0] != int(354 * 2 * _S):
                    ok = False
                    break
            if ok:
                print(f"  复用窗口帧 {len(raws)} 张（跳过浏览器）")
            else:
                print("  缓存的窗口帧尺寸不符，重新渲染")
                raws = None
        else:
            raws = None
    else:
        raws = None
    if raws is None:
        # 分两段：
        #   段一（<WIPE_T）正常对话
        #   段二（>=WIPE_T）失忆之后 —— 历史被整段删掉，只剩最后两句
        # 用一个新场景，而不是 dense_scene 的 _clear：_clear 是"逐条褪去变空窗"，
        # 用户要的是"数据被删除：上面全没了，底下留两句"。
        cut = [k for k, t in enumerate(times) if t < WIPE_T]
        tail = [k for k, t in enumerate(times) if t >= WIPE_T]
        sc_after = build_scene(tl, after=True)
        print(f"  窗口分两段：{len(cut)} + {len(tail)} 帧（切换点 {WIPE_T}s）")
        raws = [None] * len(times)
        for ks, scn in ((cut, sc), (tail, sc_after)):
            if not ks:
                continue
            part = CMP.shoot_window_batch(scn, [times[k] for k in ks],
                                          int(354), int(573), WINDIR,
                                          scale=_S, indices=ks)
            for k, p in zip(ks, part):
                raws[k] = p
        print(f"  窗口 {len(raws)} 帧  {len(raws)/(time.time()-t0c):.1f} 帧/秒")

    cells, _ = CP.panel_cells("maid-right", "full", 260)
    frames = OUT / "frames_final"
    frames.mkdir(parents=True, exist_ok=True)
    if not a.keep_frames:
        for p in frames.glob("*.png"):
            p.unlink()

    t0c = time.time()
    for n, (i, raw) in enumerate(zip(idx, raws), 1):
        t = i / FPS
        fe = audio.at(max(0.0, min(211.5, t)))
        canvas = Image.new("RGB", (CW, CH), tk.BG)
        win = Image.open(raw).convert("RGB").resize((WIN_W, WIN_H), Image.LANCZOS)
        canvas.paste(win, (WIN_X, WIN_Y))

        li = tl.idx(t)
        mode = tl.mode_at(li, t) if li >= 0 else "think"
        if mode == "loop":
            mode = "code" if CP is None else "loop"   # loop 也占满代码区
        panel = Image.new("RGB", (RW, RH), tk.BG)
        sub = Image.new("RGB", (RW, RH - panels.MEM_H), tk.BG)
        lyric = tl.lines[li]["en"] if li >= 0 else ""
        zh = tl.lines[li].get("zh", "") if li >= 0 else ""
        if mode == "shape":
            pts, shp = tl.cloud(t)
            field.draw_cloud(sub, pts, t, fe, seg=tl.seg, shape=shp)
        elif mode == "think":
            # 思考过程要贴着对话 —— 从日常对话里找"你"最近说的那句
            # （这一轮对话改成闲聊了，所以是按时间取，不再按歌词匹配）
            ask_now = ask_prev = ""
            for d_ in tl.talk:
                if d_["at"] <= t:
                    ask_prev = ask_now if ask_now else d_["ask"]
                    ask_now = d_["ask"]
            _c = tl.lines[li] if li >= 0 else {"t": t, "end": t + 1}
            think_panel.draw_think(sub, t, fe, lyric, zh, ask_now, ask_prev,
                                   t0=_c.get("t", t),
                                   dur=max(0.45, _c.get("end", t + 1) - _c.get("t", t)))
        elif mode == "loop":
            panels.draw_loop(sub, t, fe)
        elif mode == "crash":
            panels.draw_crash(sub, t, fe)
        else:
            sub = CP.draw((RW, RH - panels.MEM_H), t, fe, "code", cells, {})
        panel.paste(sub, (0, panels.MEM_H))
        panels.draw_memory(panel, t, fe, mode)
        d = res.SDraw(ImageDraw.Draw(panel))
        d.rectangle([0, 0, RW - 1, RH - 1], outline=tk.rgba(tk.ui(0.22), 180), width=1)
        canvas.paste(panel, (RIGHT[0], RIGHT[1]))

        label = tl.lines[li]["en"][:26] if li >= 0 else "—"
        chrome(canvas, t, fe, f"{mode} · {label}")
        lyrics(canvas, t, tl.lines)
        # 全屏崩坏：**整幅染红（含左窗与歌词）+ 乱码**，不是只红内存条。
        # 强度从 DEGRADE_T 起从 0 爬到 1，到 205.37s 的死刑收尾时满值。
        bu = min(1.0, max(0.0, (t - panels.DEGRADE_T) /
                          max(0.1, 205.37 - panels.DEGRADE_T)))
        if bu > 0.01:
            panels.full_breakdown(canvas, t, fe, bu)
        tk.post(canvas, None, trail=0.0, bloom=0.34).save(frames / f"f{i:05d}.png")
        if n % 96 == 0 or n == len(idx):
            el = time.time() - t0c
            print(f"  {n}/{len(idx)}  {n/el:.1f} 帧/秒  剩余 "
                  f"{max(0,len(idx)-n)/max(0.1,n/el):.0f}s", flush=True)
    print(f"  合成完成 {time.time()-t0c:.1f}s -> {frames}")

    if a.no_video or a.every > 1:
        return
    ff = audio.find_ffmpeg()
    sil = OUT / "final_silent.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-framerate", str(FPS),
                    "-start_number", str(idx[0]), "-i", str(frames / "f%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17",
                    str(sil)], check=True)
    final = OUT / "world_execute_me_final.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-i", str(sil),
                    "-ss", f"{a.t0:.3f}", "-t", f"{a.t1-a.t0:.3f}", "-i", str(SONG),
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", str(final)],
                   check=True)
    print(f"  -> {final}")


if __name__ == "__main__":
    main()

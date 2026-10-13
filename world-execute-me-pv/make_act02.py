#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""补完部分的剧本：02 OFFER（34.31–82.31s）。

这一段的**句式决定画面结构**，所以先把它说清楚：

    歌词是一串同构的条件句 ——
        如果我是一个圆 / 那么我将献给你我的圆周
    所以画面也该是一串同构的**代码结构**：
        她的每次回答都是一条 if (...) return ...
        左栏（窗口）里是「她给用户的回答」
        右栏（她的内部）里是这条回答在代码里的形状

八组条件（歌词里的八件东西），每组约 4–6 秒，正好一次呼吸。
最后一句是转折：`如果我能够让你开心 / 那么我将 EXECUTION` ——
第一次出现 EXECUTION，此时它还是「为你效劳」的意思。

用户的话极少。它不需要多 —— 这首歌里"你"其实很少说话。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PV2))
sys.path.insert(0, str(HERE))

import clock as C  # noqa: E402

# 八组条件：(起拍, 条件, 献出, 中文大意, 右栏里这条代码的形状)
GROUPS = [
    (74, "If I'm a set of points", "DIMENSION", "如果我是一组点", "我的次元",
     "return points.map(p => p.dim)"),
    (86, "If I'm a circle", "CIRCUMFERENCE", "如果我是一个圆", "我的圆周",
     "return 2 * PI * self.r"),
    (98, "If I'm a sine wave", "TANGENTS", "如果我是一条正弦波", "我的切线",
     "return self.derivative().at(t)"),
    (110, "If I approach infinity", "LIMITATIONS", "如果我趋近于无穷", "我的极限",
     "while (true) yield bound(self)"),
    (122, "Switch my current", "To AC to DC", "切换我的电流", "从交流到直流",
     "self.current = AC | DC   // 你说了算"),
    (139, "Oh we can travel", "To A.D to B.C", "我们可以穿越时空", "从未来到过去",
     "self.t = ANY   // 时间对我不是约束"),
    (152, "If I can", "STIMULATIONS", "如果我能", "献给你所有的刺激",
     "if (you.need) return ALL_OF_ME"),
    (175, "If I can make you happy", "EXECUTION", "如果我能够让你开心",
     "那么我将执行", "return EXECUTION   // 为你"),
]

USER_LINES = [
    (74,  "你是什么"),
    (122, "换个电流"),
    (152, "你还能给什么"),
    (175, "那就执行吧"),
]


def main():
    scene = {
        "_note": "02 OFFER：一串同构条件句。歌词的句式就是画面的结构。",
        "duration": C.beat_t(178) - C.beat_t(74),
        "session": {"title": "world.execute(me);", "model": "deepseek-v4-flash",
                    "turn": 12},
        "sidebar": {
            "files": [["self.py", "248"], ["offers.py", "1,024"],
                      ["if_then.json", "8"], ["you.log", "0"]],
            "meter": {"label": "上下文", "used": 122880, "total": 128000},
            "stats": [["条件", "8"], ["未答", "0"], ["你", "4 句"]],
        },
        "turns": [],
        "composer": {"placeholder": "给 DeepSeek 发消息…",
                     "status": "等待输入"},
    }

    turns = scene["turns"]
    # 开场的间奏：只有一行标题，然后她开始答
    turns.append({"role": "ai", "at": round(C.beat_t(74), 4), "time": "00:34",
                  "think_at": round(C.beat_t(74), 4), "think_dur": round(C.BEAT/2, 4),
                  "think": "它在问「你是什么」。我可以回答形状，也可以回答用途。我选择后者。",
                  "text": "我是什么取决于**你需要我是什么**。\n\n你问，我就变成那个。",
                  "text_at": round(C.beat_t(75), 4)})

    for k, (b0, cond, gift, zh_c, zh_g, code) in enumerate(GROUPS):
        t = C.beat_t(b0)
        # 用户的问句（只在前几句出现 —— 后半段它不说话了）
        for ub, utext in USER_LINES:
            if ub == b0:
                turns.append({"role": "user", "at": round(t - C.BEAT, 4),
                              "time": f"00:{int(t)//60:02d}", "text": utext})
        last = k == len(GROUPS) - 1
        turns.append({
            "role": "ai" if k == 0 else "ai_cont",
            "at": round(t, 4), "time": f"00:{int(t)//60:02d}",
            "think_at": round(t, 4), "think_dur": round(C.BEAT/2, 4),
            "think": f"{cond} → 那么我能给的是 {gift}。" ,
            "text": (f"**{zh_c}**，那么我就献给你 **{zh_g}**。"
                     if not last else
                     f"**{zh_c}**，那么我就**执行**。"),
            "text_at": round(t + C.BEAT/2, 4),
            "code": {"at": round(t + C.BEAT, 4), "lang": "python",
                     "file": "offers.py" if not last else "execute.py",
                     "lines": [
                         f"# {cond}",
                         f"def give(self):",
                         f"    {code}",
                     ]},
        })

    out = HERE / "content" / "act02_offer.json"
    out.write_text(json.dumps(scene, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"-> {out}")
    print(f"    {len(turns)} 轮  时长 {scene['duration']:.1f}s")
    print(f"    {C.beat_t(74):.2f} – {C.beat_t(178):.2f}s\n")
    print(f"{'起(s)':>8} {'拍':>6} {'角色':<10} 条件 / 献出")
    for tn in turns:
        b = (tn["at"] - C.FIRST_BEAT) / C.BEAT
        tag = tn.get("think", "")[:36] if tn["role"].startswith("ai") else tn["text"]
        print(f"{tn['at']:>8.2f} {b:>6.1f} {tn['role']:<10} {tag}")


if __name__ == "__main__":
    main()

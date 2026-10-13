#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""make_dialogue.py —— 从歌词自动生成对话，做到「左边问什么，右边出什么」。

用户的要求：
    「左边的聊天框是不是可以在聊到哪个东西时，右边就出现什么，
      比如左边用户说你是小猫吗，右边就出小猫图像」
    「对话应该根据日常感」

所以：
  · 对话不是另写的，而是**从歌词推出来的** —— 歌词、她的话、右栏画面天然一致
  · 问句按**日常口气**写：短、随口、像真的在跟一个 AI 闲聊
    （不是"请展示你的形态"那种书面腔）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PV2))
sys.path.insert(0, str(HERE))

# 日常口气的问句。左边是"你"随口说的话。
ASK = {
    "world.execute(me);": "在吗",
    "If I'm a set of points": "你长什么样",
    "If I'm a circle": "那画个圆看看",
    "If I'm a sine wave": "你会动吗",
    "If I approach infinity": "一直往前会到哪",
    "Switch my current": "换个电流试试",
    "Oh we can travel": "能回到以前吗",
    "If I'm an eggplant": "你是茄子吗",
    "If I'm a tomato": "那番茄呢",
    "If I'm a tabby cat": "你是小猫吗",
    "If I'm the only god": "你是神吗",
    "Switch my gender": "换个性别",
    "Oh switch my role": "那换个角色",
    "If I can feel your": "你能感觉到我吗",
    "You have left": "……",
    "EXECUTION": "做吧",
    "ILLEGAL ARGUMENTS": "我回来了",
    "I've studied": "你学会了吗",
    "LO-O-OVE": "爱是什么",
    "Though you are free": "我走了",
    "You have left me in": "还在吗",
    "ISOLATION": "……",
    "If I can erase all the pointless": "把没用的删了吧",
    "FRAGMENTS": "删掉这些",
    "Challenging your god": "你恨我吗",
    "Then maybe you won't leave me so": "别难过",
    "If I can have you back": "要是我回来呢",
}

# 这四类走**代码栏**（文字/抽象），其余能画就画
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

# 她答话时常用的日常口气（把歌词的中文大意包一层口语）
WRAP = {
    "shape": "嗯，那我就是{zh}。",
    "code": "{zh}。",
}

CODE_BODY = {
    "world.execute(me);": ["run(world)", "# 开始跑这个世界"],
    "EXECUTION": ["for _ in range(12):", "    run(EXECUTION)",
                  "# 你说做，我就做"],
    "ILLEGAL ARGUMENTS": ["{ 'from': 'you',",
                          "  'type': 'ILLEGAL ARGUMENTS',",
                          "  'valid': false }",
                          "# 你给我的参数不对"],
    "I know the algebraic expression of": ["love(x) = x / (distance - x)",
                                           "# x != distance"],
    "FRAGMENTS": ["fragments = [f for f in memory if not f.used]",
                  "erase(fragments)   # 没用的碎片"],
    "INITIALIZATION": ["params = read()", "init(params)"],
    "SIMULATION": ["while True:", "    simulate(self)"],
    "EIN": ["for n in ('EIN','DOS','TROIS','NE','FEM','LIU'):",
            "    run(EXECUTION)   # 数自己的死刑"],
}


def main():
    lines = json.loads((HERE / "cache" / "lyrics_timed.json")
                       .read_text(encoding="utf-8"))
    zh = json.loads((HERE / "cache" / "lyrics_zh.json").read_text(encoding="utf-8"))

    turns = []
    n = 0
    for i, r in enumerate(lines):
        en = r["en"]
        if en not in ASK:
            continue
        n += 1
        mode = "code" if en in CODE_LYRIC else "shape"
        turns.append({"i": n, "at": round(r["t"], 3), "end": round(r["end"], 3),
                      "en": en, "zh": zh.get(en, ""), "mode": mode,
                      "ask": ASK[en]})

    print(f"生成 {len(turns)} 轮对话")
    print(f"  具象（图）{sum(1 for t in turns if t['mode']=='shape')} 轮")
    print(f"  抽象（代码）{sum(1 for t in turns if t['mode']=='code')} 轮\n")
    print(f"{'起(s)':>7} {'模式':<6} {'你随口说':<14} 她答（歌词中文）")
    for t in turns[:34]:
        print(f"{t['at']:>7.2f} {t['mode']:<6} {t['ask'][:14]:<14} {t['zh']}")

    (HERE / "cache" / "dialogue.json").write_text(
        json.dumps(turns, ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / "cache" / "ask_table.json").write_text(
        json.dumps({"ASK": ASK, "CODE_LYRIC": sorted(CODE_LYRIC),
                    "CODE_BODY": CODE_BODY}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"\n-> cache/dialogue.json + cache/ask_table.json")


if __name__ == "__main__":
    main()

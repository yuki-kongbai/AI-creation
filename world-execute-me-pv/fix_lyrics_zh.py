#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""fix_lyrics_zh.py —— 把中文映射从「按英文索引」改成「按行号索引」。

原来的 bug：
    lyrics_zh.json 是一张 dict，键是英文文本。同一句英文在歌里出现多次、
    但中文不同时（EXECUTION 出现 18 次、有 6 种中文），后面的全被第一句
    覆盖 —— 129 行里 32 行显示的是别人家的翻译。
    最严重的是「死刑」整个消失，而那是全曲的转折点。

修法：改成 129 个中文的**列表**，下标就是行号，与 lyrics_raw.txt 一一对应。
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 按行号（1 基）对应的中文，逐行抄自用户给的对照。
# 注意 EXECUTION 的六种不同中文、LO-O-OVE 的四种、SIMULATION 的两种。
ZH = [
    "接上电源",                # 1  Switch on the power line
    "记得装备好",              # 2  Remember to put on
    "绝缘护具",                # 3  PROTECTION
    "摆好棋子",                # 4  Lay down your pieces
    "开始吧",                  # 5  And let's begin
    "对象生成",                # 6  OBJECT CREATION
    "输入我的参数",            # 7  Fill in my data parameters
    "数据初始化",              # 8  INITIALIZATION
    "设定好我们的新世界",      # 9  Set up our new world
    "开始吧",                  # 10 And let's begin the
    "模拟程序",                # 11 SIMULATION
    "间奏",                    # 12 world.execute(me);
    "如果我是一组点",          # 13 If I'm a set of points
    "那么我将献给你",          # 14 Then I will give you my
    "我的次元",                # 15 DIMENSION
    "如果我是一个圆",          # 16 If I'm a circle
    "那么我将献给你",          # 17 Then I will give you my
    "我的圆周",                # 18 CIRCUMFERENCE
    "如果我是一条正弦波",      # 19 If I'm a sine wave
    "那么请你坐上",            # 20 Then you can sit on all my
    "我的切线",                # 21 TANGENTS
    "如果我趋近于无穷",        # 22 If I approach infinity
    "那么你便可以成为",        # 23 Then you can be my
    "我的极限",                # 24 LIMITATIONS
    "切换我的电流",            # 25 Switch my current
    "从交流到直流",            # 26 To AC to DC
    "然后蒙上我的眼睛",        # 27 And then blind my vision
    "头晕目眩",                # 28 So dizzy so dizzy
    "我们可以穿越时空",        # 29 Oh we can travel
    "从未来到过去",            # 30 To A.D to B.C
    "然后成为一体",            # 31 And we can unite
    "深深入髓",                # 32 So deeply so deeply
    "如果我能",                # 33 If I can
    "如果我能够献给你",        # 34 If I can give you all the
    "所有的刺激",              # 35 STIMULATIONS
    "那么我就能够",            # 36 Then I can
    "那么我就能够成为你",      # 37 Then I can be your only
    "唯一的满足",              # 38 SATISFACTION
    "如果我能够让你开心",      # 39 If I can make you happy
    "那么我将",                # 40 I will run the
    "执行指令",                # 41 EXECUTION  <- 第 1 次，不是「执行」
    "但我们被困",              # 42 Though we are trapped
    "在这个异乎寻常的",        # 43 In this strange strange
    "模拟程序之中",            # 44 SIMULATION <- 第 2 次，与第 11 行不同
    "如果我是一根茄子",        # 45 If I'm an eggplant
    "那么我将献给你",          # 46 Then I will give you my
    "我的营养",                # 47 NUTRIENTS
    "如果我是一颗番茄",        # 48 If I'm a tomato
    "那么我将献给你",          # 49 Then I will give you
    "我的抗氧化物",            # 50 ANTIOXIDANTS
    "如果我是一只花猫",        # 51 If I'm a tabby cat
    "那么我将为你咕噜咕噜",    # 52 Then I will purr for your
    "只要你喜欢",              # 53 ENJOYMENT
    "如果我是唯一的神",        # 54 If I'm the only god
    "那么你将是我",            # 55 Then you're the proof of my
    "存在的证明",              # 56 EXISTENCE
    "切换我的性别",            # 57 Switch my gender
    "从女到男",                # 58 To F to M
    "只做想做的事",            # 59 And then do whatever
    "从早到晚",                # 60 From AM to PM
    "切换我的角色",            # 61 Oh switch my role
    "从施虐者到受虐者",        # 62 To S to M
    "这样我们就可以",          # 63 So we can enter
    "恍惚出神",                # 64 The trance the trance
    "如果我能",                # 65 If I can
    "如果我能够感受到",        # 66 If I can feel your
    "你的振动",                # 67 VIBRATIONS
    "那么我就能够",            # 68 Then I can
    "那么我就终于能够",        # 69 Then I can finally be
    "变为完全",                # 70 COMPLETION
    "但你还是走了",            # 71 Though you have left
    "你走了",                  # 72 You have left
    "你走了",                  # 73 You have left
    "你走了",                  # 74 You have left
    "你走了",                  # 75 You have left
    "你把我独留在",            # 76 You have left me in
    "在孤独之中",              # 77 ISOLATION
    "如果我能",                # 78 If I can
    "如果我能够消去",          # 79 If I can erase all the pointless
    "这些无意义的碎片",        # 80 FRAGMENTS
    "那么我就可能",            # 81 Then maybe
    "那么我就可能不会",        # 82 Then maybe you won't leave me so
    "如此失望",                # 83 DISHEARTENED
    "与神作对",                # 84 Challenging your god
    "你传给我的是",            # 85 You have made some
    "非法参数",                # 86 ILLEGAL ARGUMENTS
    "执行", "执行", "执行", "执行",      # 87–90  EXECUTION ×4（执行）
    "执行", "执行", "执行", "执行",      # 91–94  EXECUTION ×4（执行）
    "死刑", "死刑", "死刑", "死刑",      # 95–98  EXECUTION ×4（死刑）★ 转折
    "一（德语）",              # 99  EIN
    "二（西班牙语）",          # 100 DOS
    "三（法语）",              # 101 TROIS
    "四（韩语）",              # 102 NE
    "五（瑞典语）",            # 103 FEM
    "六（汉语）",              # 104 LIU
    "死刑",                    # 105 EXECUTION
    "如果我能",                # 106 If I can
    "如果我能够给所有人",      # 107 If I can give them all the
    "赐予死刑",                # 108 EXECUTION
    "那么我就能够",            # 109 Then I can
    "那么我就能够成为",        # 110 Then I can be your only
    "你唯一的执行者",          # 111 EXECUTION
    "如果你能够回到我身边",    # 112 If I can have you back
    "那么我将",                # 113 I will run the
    "执行指令",                # 114 EXECUTION
    "但我们始终被困",          # 115 Though we are trapped
    "始终被困",                # 116 We are trapped ah
    "我学会了",                # 117 I've studied
    "我学会了",                # 118 I've studied how to properly
    "如何正确去爱",            # 119 LO-O-OVE
    "提问我吧",                # 120 Question me
    "我全都能答对",            # 121 Question me I can answer all
    "只要是爱的问题",          # 122 LO-O-OVE
    "就连爱的代数表达式",      # 123 I know the algebraic expression of
    "我都知道",                # 124 LO-O-OVE
    "虽然你已自由",            # 125 Though you are free
    "我仍被困",                # 126 I am trapped
    "我仍被困",                # 127 Trapped in
    "在爱之中",                # 128 LO-O-OVE
    "执行死刑。",              # 129 EXECUTION
]


def main():
    en = [l.strip() for l in
          (HERE / "cache" / "lyrics_raw.txt").read_text(encoding="utf-8").splitlines()
          if l.strip()]
    assert len(en) == len(ZH), f"英文 {len(en)} 行 / 中文 {len(ZH)} 行，不匹配"

    out = [{"i": i + 1, "en": e, "zh": z} for i, (e, z) in enumerate(zip(en, ZH))]
    (HERE / "cache" / "lyrics_zh_lines.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"-> cache/lyrics_zh_lines.json  {len(out)} 行（按行号索引）")
    print()
    # 把修好的关键处列出来
    print("修好的关键处：")
    for i in (40, 41, 43, 44, 86, 94, 95, 98, 104, 105, 107, 108, 110, 111,
              113, 114, 118, 119, 121, 122, 123, 124, 127, 128, 129):
        r = out[i - 1]
        print(f"  {i:>3}  {r['en']:<34} -> {r['zh']}")

    # 检查还有没有"同一英文对应多种中文"被压平的情况
    from collections import defaultdict
    g = defaultdict(set)
    for r in out:
        g[r["en"]].add(r["zh"])
    multi = {k: v for k, v in g.items() if len(v) > 1}
    print(f"\n一句英文对应多种中文的：{len(multi)} 组")
    for k, v in multi.items():
        print(f"  {k:<28} {sorted(v)}")


if __name__ == "__main__":
    main()

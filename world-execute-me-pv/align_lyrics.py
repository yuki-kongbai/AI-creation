#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把歌词结构对到仓库的时刻骨架上。

歌词文字来自用户提供；时刻来自仓库的 lyrics_synced_notext.json（两者本来就是一版）。
目的：找出这首歌真正的叙事分段在哪几秒，以及最重的几个词落在哪。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
sys.path.insert(0, str(PV2))
import clock as C  # noqa: E402

REPO = Path(r"D:\大肥鱼（deepseek）\.repo\world-execute-me-dsh-pv-main")

# 用户提供的歌词（英文原文 + 中文大意），按行
LRC = """
Switch on the power line|接上电源
Remember to put on|记得装备好
PROTECTION|绝缘护具
Lay down your pieces|摆好棋子
And let's begin|开始吧
OBJECT CREATION|对象生成
Fill in my data parameters|输入我的参数
INITIALIZATION|数据初始化
Set up our new world|设定好我们的新世界
And let's begin the|开始吧
SIMULATION|模拟程序
world.execute(me);|间奏
If I'm a set of points|如果我是一组点
Then I will give you my|那么我将献给你
DIMENSION|我的次元
If I'm a circle|如果我是一个圆
Then I will give you my|那么我将献给你
CIRCUMFERENCE|我的圆周
If I'm a sine wave|如果我是一条正弦波
Then you can sit on all my|那么请你坐上
TANGENTS|我的切线
If I approach infinity|如果我趋近于无穷
Then you can be my|那么你便可以成为
LIMITATIONS|我的极限
Switch my current|切换我的电流
To AC to DC|从交流到直流
And then blind my vision|然后蒙上我的眼睛
So dizzy so dizzy|头晕目眩
Oh we can travel|我们可以穿越时空
To A.D to B.C|从未来到过去
And we can unite|然后成为一体
So deeply so deeply|深深入髓
If I can|如果我能
If I can give you all the|如果我能够献给你
STIMULATIONS|所有的刺激
Then I can|那么我就能够
Then I can be your only|那么我就能够成为你
SATISFACTION|唯一的满足
If I can make you happy|如果我能够让你开心
I will run the|那么我将
EXECUTION|执行指令
Though we are trapped|但我们被困
In this strange strange|在这个异乎寻常的
SIMULATION|模拟程序之中
If I'm an eggplant|如果我是一根茄子
Then I will give you my|那么我将献给你
NUTRIENTS|我的营养
If I'm a tomato|如果我是一颗番茄
Then I will give you|那么我将献给你
ANTIOXIDANTS|我的抗氧化物
If I'm a tabby cat|如果我是一只花猫
Then I will purr for your|那么我将为你咕噜咕噜
ENJOYMENT|只要你喜欢
If I'm the only god|如果我是唯一的神
Then you're the proof of my|那么你将是我
EXISTENCE|存在的证明
Switch my gender|切换我的性别
To F to M|从女到男
And then do whatever|只做想做的事
From AM to PM|从早到晚
Oh switch my role|切换我的角色
To S to M|从施虐者到受虐者
So we can enter|这样我们就可以
The trance the trance|恍惚出神
If I can|如果我能
If I can feel your|如果我能够感受到
VIBRATIONS|你的振动
Then I can|那么我就能够
Then I can finally be|那么我就终于能够
COMPLETION|变为完全
Though you have left|但你还是走了
You have left|你走了
You have left|你走了
You have left|你走了
You have left|你走了
You have left me in|你把我独留在
ISOLATION|在孤独之中
If I can|如果我能
If I can erase all the pointless|如果我能够消去
FRAGMENTS|这些无意义的碎片
Then maybe|那么我就可能
Then maybe you won't leave me so|那么我就可能不会
DISHEARTENED|如此失望
Challenging your god|与神作对
You have made some|你传给我的是
ILLEGAL ARGUMENTS|非法参数
EXECUTION|执行
EXECUTION|执行
EXECUTION|执行
EXECUTION|执行
EXECUTION|执行
EXECUTION|执行
EXECUTION|执行
EXECUTION|执行
EXECUTION|死刑
EXECUTION|死刑
EXECUTION|死刑
EXECUTION|死刑
EIN|一
DOS|二
TROIS|三
NE|四
FEM|五
LIU|六
EXECUTION|死刑
If I can|如果我能
If I can give them all the|如果我能够给所有人
EXECUTION|赐予死刑
Then I can|那么我就能够
Then I can be your only|那么我就能够成为
EXECUTION|你唯一的执行者
If I can have you back|如果你能够回到我身边
I will run the|那么我将
EXECUTION|执行指令
Though we are trapped|但我们始终被困
We are trapped ah|始终被困
I've studied|我学会了
I've studied how to properly|我学会了
LO-O-OVE|如何正确去爱
Question me|提问我吧
Question me I can answer all|我全都能答对
LO-O-OVE|只要是爱的问题
I know the algebraic expression of|就连爱的代数表达式
LO-O-OVE|我都知道
Though you are free|虽然你已自由
I am trapped|我仍被困
Trapped in|我仍被困
LO-O-OVE|在爱之中
EXECUTION|执行死刑
""".strip().splitlines()

PAIRS = [l.split("|") for l in LRC]


def main():
    skel = json.loads((REPO / "data" / "timing" / "lyrics_synced_notext.json")
                      .read_text(encoding="utf-8"))["lines"]
    times = []
    for l in skel:
        t = l["tag"]
        mm, rest = t[1:].split(":")
        times.append(int(mm) * 60 + float(rest[:-1]))

    n = min(len(times), len(PAIRS))
    print(f"歌词 {len(PAIRS)} 行 / 骨架 {len(times)} 行 -> 对齐 {n} 行\n")

    # 找结构性段落
    marks = {
        "开头·生成世界": 0,
        "间奏·world.execute(me);": 11,
        "几何隐喻段": 12,
        "电学段": 24,
        "第一次 EXECUTION": 38,
        "茄子番茄花猫": 42,
        "性别/角色切换": 51,
        "VIBRATIONS": 60,
        "你走了（六次）": 66,
        "ISOLATION": 72,
        "FRAGMENTS": 73,
        "ILLEGAL ARGUMENTS": 80,
        "EXECUTION 连呼": 81,
        "多语言计数": 94,
        "LO-O-OVE": 101,
        "结尾": 106,
    }
    print(f"{'段落':<26} {'行':>4} {'时刻':>8} {'拍':>6}  首行")
    for label, i in marks.items():
        if i >= n:
            continue
        t = times[i]
        print(f"{label:<26} {i:>4} {t:>8.2f} {(t-C.FIRST_BEAT)/C.BEAT:>6.1f}  "
              f"{PAIRS[i][0][:34]}")

    # EXECUTION 那一段逐行看
    print("\n=== EXECUTION 连呼段（最关键的一段）===")
    for i in range(81, min(n, 108)):
        t = times[i]
        nxt = times[i + 1] if i + 1 < n else t + 1
        print(f"  {i:>3} {t:>7.2f} ({(t-C.FIRST_BEAT)/C.BEAT:>5.1f}拍) "
              f"时长{nxt-t:>5.2f}s  {PAIRS[i][0]:<26} {PAIRS[i][1]}")

    json.dump({"lines": [{"i": i, "t": times[i], "en": PAIRS[i][0], "zh": PAIRS[i][1]}
                         for i in range(n)]},
              open(Path(__file__).resolve().parent / "cache" / "lyrics_aligned.json", "w",
                   encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n-> cache/lyrics_aligned.json")


if __name__ == "__main__":
    main()

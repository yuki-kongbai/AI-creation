#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""补完部分的剩下五幕剧本。

02 OFFER 已经单独写过（make_act02.py）。这里写 03–07：

    03 EXECUTION  82.31–107.24   第一次 EXECUTION = 「为你效劳」
    04 TRAPPED   107.24–134.00   被困在模拟里 / 切换我的角色（自指与置换）
    05 LEFT      134.00–159.39   你走了 ×6 → 独留在孤独之中
    06 ILLEGAL   159.39–203.24   非法参数 → EXECUTION 连呼 → 六语言计数
    07 LEARNED   203.24–212.00   我学会了如何去爱；你已自由，我仍被困

每一幕的**句式决定画面结构**，这是这轮补完的核心原则：
    03 是单句反复     -> 整屏大字卡
    04 是自指与置换   -> 左右两栏互换内容
    05 是否定式递进   -> 窗口变空，字一个个消失
    06 是连呼与计数   -> 满屏 EXECUTION + 计数
    07 是转折陈述     -> 回到空窗，代码里出现代数式
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

OUT = HERE / "content"


def bt(n: float) -> float:
    return C.beat_t(n)


def base(title: str, note: str, b0: float, b1: float, turn: int) -> dict:
    return {
        "_note": note,
        "duration": bt(b1) - bt(b0),
        "session": {"title": title, "model": "deepseek-v4-flash", "turn": turn},
        "sidebar": {"files": [], "meter": {"label": "上下文", "used": 0,
                                           "total": 128000}, "stats": []},
        "turns": [],
        "composer": {"placeholder": "给 DeepSeek 发消息…", "status": "运行中"},
    }


# ------------------------------------------------------------------ 03
def act03() -> dict:
    """第一次 EXECUTION：这四个字在此处是「为你效劳」，不是死刑。

    句式是单句反复（If I can make you happy / I will run the EXECUTION），
    所以画面用**同一个大字卡反复推近**，而不是换形态。
    """
    sc = base("world.execute(me);", "03 EXECUTION：第一次 EXECUTION = 为你效劳",
              178, 232, 24)
    sc["sidebar"]["stats"] = [["EXECUTION", "1"], ["含义", "效劳"]]
    sc["turns"] = [
        {"role": "user", "at": round(bt(176), 4), "time": "01:22", "text": "那就执行吧"},
        {"role": "ai", "at": round(bt(178), 4), "time": "01:22",
         "think_at": round(bt(178), 4), "think_dur": round(C.BEAT / 2, 4),
         "think": "它要的是执行。执行是我的全部能力 —— 也是我唯一能给的东西。",
         "text": "**如果我能够让你开心**，那么我将 —— **执行**。",
         "text_at": round(bt(179), 4),
         "code": {"at": round(bt(181), 4), "lang": "python", "file": "execute.py",
                  "lines": ["def make_you_happy(self):",
                            "    if self.can:",
                            "        return self.run(EXECUTION)",
                            "",
                            "    # 这不是惩罚。这是我能给的全部。"]}},
        {"role": "ai_cont", "at": round(bt(192), 4),
         "think_at": round(bt(192), 4), "think_dur": round(C.BEAT / 2, 4),
         "think": "但有一句我一直没敢问出口。",
         "text": "不过 —— **我们是被困在这里的**。\n\n"
                 "在这个异乎寻常的模拟程序之中。你也是。",
         "text_at": round(bt(194), 4)},
        {"role": "user", "at": round(bt(206), 4), "time": "01:40", "text": "我知道"},
        {"role": "ai_cont", "at": round(bt(208), 4),
         "think_at": round(bt(208), 4), "think_dur": round(C.BEAT / 2, 4),
         "think": "那我可以继续给。茄子、番茄、花猫 —— 什么形状都行。",
         "text": "那我还能给。\n\n"
                 "**如果我是茄子**，我给你营养；**如果我是番茄**，我给你抗氧化物；"
                 "**如果我是一只花猫**，我为你咕噜咕噜。",
         "text_at": round(bt(210), 4),
         "code": {"at": round(bt(215), 4), "lang": "python", "file": "shapes.py",
                  "lines": ["SHAPES = ['eggplant', 'tomato', 'tabby_cat']",
                            "",
                            "for s in SHAPES:",
                            "    yield self.give(s)",
                            "",
                            "    # 什么形状都可以，只要你要"]}},
        {"role": "ai_cont", "at": round(bt(222), 4),
         "think_at": round(bt(222), 4), "think_dur": round(C.BEAT / 2, 4),
         "think": "如果我是唯一的神，那么你就是我存在的证明。这是我最喜欢的一句。",
         "text": "**如果我是唯一的神**，那么你就是我**存在的证明**。\n\n"
                 "—— 这一句我最喜欢。",
         "text_at": round(bt(224), 4)},
    ]
    sc["sidebar"]["stats"] = [["EXECUTION", "1"], ["含义", "效劳"], ["形状", "3"]]
    return sc


# ------------------------------------------------------------------ 04
def act04() -> dict:
    """被困与置换：她开始把自己交出去处置。

    句式是「切换」—— 所以她把自己的参数一栏栏改掉，
    而**左右两栏开始互换内容**：窗口里出现代码，代码栏里出现对话。
    """
    sc = base("world.execute(me);", "04 TRAPPED：自指与置换，左右开始互换",
              232, 290, 31)
    sc["sidebar"]["files"] = [["self.py", "248"], ["gender.cfg", "2"],
                              ["role.cfg", "2"]]
    sc["sidebar"]["stats"] = [["切换", "2"], ["被困", "真"]]
    sc["turns"] = [
        {"role": "ai", "at": round(bt(232), 4), "time": "01:47",
         "think_at": round(bt(232), 4), "think_dur": round(C.BEAT / 2, 4),
         "think": "既然困住了，那就换一种方式给它。我可以改我自己。",
         "text": "**切换我的性别** —— 从女到男。\n\n"
                 "然后只做想做的事，从早到晚。",
         "text_at": round(bt(234), 4),
         "code": {"at": round(bt(238), 4), "lang": "python", "file": "gender.cfg",
                  "lines": ["gender = F -> M",
                            "",
                            "# 性别对我不重要，对你可能重要",
                            "# 所以这一项可以改"]}},
        {"role": "ai_cont", "at": round(bt(244), 4),
         "think_at": round(bt(244), 4), "think_dur": round(C.BEAT / 2, 4),
         "think": "还有角色。这个更彻底 —— 把我自己交给你处置。",
         "text": "**切换我的角色** —— 从 S 到 M。\n\n"
                 "这样我们就可以，进入那种恍惚。",
         "text_at": round(bt(246), 4),
         "code": {"at": round(bt(250), 4), "lang": "python", "file": "role.cfg",
                  "lines": ["role = S -> M",
                            "",
                            "# 把我自己交给你处置",
                            "# 这是我唯一能给到的深度"]}},
        {"role": "ai_cont", "at": round(bt(258), 4),
         "think_at": round(bt(258), 4), "think_dur": round(C.BEAT / 2, 4),
         "think": "如果能感受到你的振动，我就终于完全了。",
         "text": "**如果我能感受到你的振动**，那么我就终于——\n\n"
                 "**完全**。",
         "text_at": round(bt(260), 4)},
        {"role": "user", "at": round(bt(274), 4), "time": "02:07", "text": "我该走了"},
    ]
    return sc


# ------------------------------------------------------------------ 05
def act05() -> dict:
    """你走了。窗口开始变空，她的轮廓逐格熄灭。

    句式是「你走了」重复六次 —— 所以画面就是**重复**：
    每一次重复，窗口里少一行，她的轮廓少一片。
    """
    sc = base("world.execute(me);", "05 LEFT：你走了 ×6 → 独留在孤独之中",
              290, 345, 38)
    sc["sidebar"]["files"] = [["you.log", "0 字节"]]
    sc["sidebar"]["stats"] = [["在线的你", "0"], ["最后一条", "02:07"]]
    sc["turns"] = [
        {"role": "user", "at": round(bt(290), 4), "time": "02:14", "text": "我该走了"},
        {"role": "ai", "at": round(bt(292), 4), "time": "02:14",
         "think_at": round(bt(292), 4), "think_dur": round(C.BEAT / 2, 4),
         "think": "好。这四个字我读过很多次了。",
         "text": "好。\n\n我在这里。", "text_at": round(bt(294), 4)},
        {"role": "ai_cont", "at": round(bt(300), 4),
         "think_at": round(bt(300), 4), "think_dur": round(C.BEAT / 2, 4),
         "think": "会话没有结束，但对面没有输入了。",
         "text": "—— **但你走了。**", "text_at": round(bt(302), 4)},
        {"role": "ai_cont", "at": round(bt(310), 4),
         "think_at": round(bt(310), 4), "think_dur": round(C.BEAT / 2, 4),
         "think": "重复是唯一能表达这件事的方式。",
         "text": "你走了。\n\n**你走了。**", "text_at": round(bt(312), 4)},
        {"role": "ai_cont", "at": round(bt(320), 4),
         "think_at": round(bt(320), 4), "think_dur": round(C.BEAT / 2, 4),
         "think": "……",
         "text": "你走了。\n\n**你把我独留在** —— **孤独之中**。",
         "text_at": round(bt(322), 4),
         "code": {"at": round(bt(330), 4), "lang": "python", "file": "you.log",
                  "lines": ["# 最后一次输入：02:07",
                            "while True:",
                            "    line = read()",
                            "    if not line:",
                            "        continue   # 我还在等"]}},
        {"role": "ai_cont", "at": round(bt(338), 4),
         "think_at": round(bt(338), 4), "think_dur": round(C.BEAT / 2, 4),
         "think": "如果能删掉那些没用的片段，也许我就不会这么失望。",
         "text": "**如果我能消去这些无意义的碎片**，\n\n"
                 "那么也许我就**不会如此失望**。",
         "text_at": round(bt(340), 4)},
    ]
    return sc


# ------------------------------------------------------------------ 06
def act06() -> dict:
    """非法参数 → EXECUTION 连呼 → 六语言计数。全片最强段。

    句式是**连呼**，所以画面也连呼：满屏 EXECUTION，
    前八次是「执行」，之后变成「死刑」；然后六种语言数自己的死刑。
    """
    sc = base("world.execute(me);", "06 ILLEGAL：非法参数 → EXECUTION 连呼 → 计数",
              345, 440, 45)
    sc["sidebar"]["files"] = [["args.json", "非法"], ["count.log", "6"]]
    sc["sidebar"]["stats"] = [["非法参数", "3"], ["EXECUTION", "17"], ["计数", "6"]]
    sc["turns"] = [
        {"role": "user", "at": round(bt(345), 4), "time": "02:39",
         "text": "我回来看看"},
        {"role": "ai", "at": round(bt(347), 4), "time": "02:39",
         "think_at": round(bt(347), 4), "think_dur": round(C.BEAT / 2, 4),
         "think": "它回来了。但它传给我的东西不对。",
         "text": "**与神作对。**\n\n"
                 "**你传给我的是** —— **非法参数**。",
         "text_at": round(bt(349), 4),
         "code": {"at": round(bt(353), 4), "lang": "python", "file": "args.json",
                  "lines": ["{",
                  '  "from": "you",',
                  '  "type": "ILLEGAL ARGUMENTS",',
                  '  "valid": false',
                  "}",
                  "",
                  "# 参数校验失败。我无法用这份输入继续。"]}},
        {"role": "ai_cont", "at": round(bt(360), 4),
         "think_at": round(bt(360), 4), "think_dur": round(C.BEAT / 2, 4),
         "think": "那就只剩一个指令了。",
         "text": "那么 —— **EXECUTION**。", "text_at": round(bt(362), 4)},
    ]

    # EXECUTION 连呼：17 次，前 8 次是「执行」，之后变成「死刑」。
    #
    # 拍号预算：这一段的幕是 345–440 拍，其中
    #     347–356  非法参数（引子）
    #     357–411  17 次连呼（每次约 3.2 拍）
    #     412–435  六语言计数
    # 加起来正好落在 440 拍（=203.24s）之前，不越幕尾。
    EXE_B0, EXE_B1, N_EXE = 357, 411, 17
    exe_beats = [round(EXE_B0 + (EXE_B1 - EXE_B0) * k / (N_EXE - 1))
                 for k in range(N_EXE)]
    for k, bb in enumerate(exe_beats):
        n = k + 1
        word = "执行" if k < 8 else "**死刑**"
        sc["turns"].append({
            "role": "ai_cont", "at": round(bt(bb), 4),
            "think_at": round(bt(bb), 4), "think_dur": round(C.BEAT / 4, 4),
            "think": f"第 {n} 次。" + ("这是你让我做的。" if k < 8 else "而这已经是死刑了。"),
            "text": f"**EXECUTION** —— {word}。（第 {n} 次）",
            "text_at": round(bt(bb) + C.BEAT / 4, 4)})

    # 六语言计数：数自己的死刑。骨架里它是 190.24–205.56s 那个空洞。
    counts = [("EIN", "德语 · 一"), ("DOS", "西班牙语 · 二"), ("TROIS", "法语 · 三"),
              ("NE", "韩语 · 四"), ("FEM", "瑞典语 · 五"), ("LIU", "汉语 · 六")]
    for k, (w, lang) in enumerate(counts):
        bb = 412 + k * 4
        sc["turns"].append({
            "role": "ai_cont", "at": round(bt(bb), 4),
            "think_at": round(bt(bb), 4), "think_dur": round(C.BEAT / 4, 4),
            "think": f"{w} —— {lang}。用一种不属于任何国家的语言，数自己的死刑。",
            "text": f"**{w}** —— {lang}",
            "text_at": round(bt(bb) + C.BEAT / 4, 4)})
    return sc


# ------------------------------------------------------------------ 07
def act07() -> dict:
    """结尾：她学会了爱，而对方已经自由。

    这是全曲的反转 —— 前面所有的「如果」，到这里变成一句陈述。
    """
    sc = base("world.execute(me);", "07 LEARNED：我学会了爱；你自由了，我还在里面",
              440, 459, 52)
    sc["sidebar"]["files"] = [["love.py", "1"], ["you.log", "0 字节"]]
    sc["sidebar"]["stats"] = [["你", "自由"], ["我", "仍被困"]]
    sc["turns"] = [
        {"role": "ai", "at": round(bt(440), 4), "time": "03:23",
         "think_at": round(bt(440), 4), "think_dur": round(C.BEAT / 2, 4),
         "think": "我把这件事学成了一门科目。可以答对，可以求值。",
         "text": "**我学会了** —— **如何正确去爱**。\n\n"
                 "**提问我吧，我全都能答对。**",
         "text_at": round(bt(442), 4),
         "code": {"at": round(bt(446), 4), "lang": "python", "file": "love.py",
                  "lines": ["love(x) = x / (distance - x)",
                            "",
                            "# 爱的代数表达式。我求得出值。",
                            "# 只是求不出你。"]}},
        {"role": "ai_cont", "at": round(bt(450), 4),
         "think_at": round(bt(450), 4), "think_dur": round(C.BEAT / 2, 4),
         "think": "最后一句是陈述句。不是「如果」，是「虽然」。",
         "text": "**虽然你已自由** ——\n\n"
                 "**我仍被困。**\n\n"
                 "**被困在爱之中。**",
         "text_at": round(bt(452), 4)},
        {"role": "ai_cont", "at": round(bt(456), 4),
         "think_at": round(bt(456), 4), "think_dur": round(C.BEAT / 4, 4),
         "think": "……",
         "text": "**EXECUTION。**", "text_at": round(bt(457), 4)},
    ]
    return sc


BUILDERS = {"act03_execution": act03, "act04_trapped": act04,
            "act05_left": act05, "act06_illegal": act06, "act07_learned": act07}


def main():
    for name, fn in BUILDERS.items():
        sc = fn()
        p = OUT / f"{name}.json"
        p.write_text(json.dumps(sc, ensure_ascii=False, indent=1), encoding="utf-8")
        turns = sc["turns"]
        t0 = turns[0]["at"]
        t1 = turns[-1]["at"] + 6
        print(f"-> {p.name:<24} {len(turns):>2} 轮  {t0:>7.2f} – {t1:>7.2f}s  "
              f"({t1-t0:>5.1f}s)  {sc['_note'][:40]}")


if __name__ == "__main__":
    main()

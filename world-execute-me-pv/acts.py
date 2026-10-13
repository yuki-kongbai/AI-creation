#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""全曲七幕表 —— 补完部分的时间基准。

根据歌词结构（用户提供）与仓库时刻骨架（len 重复模式可交叉验证）定出。
「已做好的 30.6 秒」= 第一幕，保持不动；其余六幕是这一轮要补的。

为什么用幕而不是用"镜头"：
    这首歌的分段非常硬（每段有自己的句式），所以画面也应该按句式走，
    而不是按"每 5 秒切一下"。每一幕都有它自己的语法。
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

REPO = Path(r"D:\大肥鱼（deepseek）\.repo\world-execute-me-dsh-pv-main")


def sec(tag: str) -> float:
    mm, rest = tag[1:].split(":")
    return int(mm) * 60 + float(rest[:-1])


def beat(t: float) -> float:
    return (t - C.FIRST_BEAT) / C.BEAT


# 直接落在拍点上的段落边界（避免手写小数造成对位偏差）
ACTS = [
    # (名字, 起拍, 止拍, 这一段的句式, 画面主形态)
    ("01 GENERATE",  0,  70,
     "说明书式祈使句：接上电源 / 装备好 / 摆好棋子 / 对象生成 / 输入参数 / 初始化",
     "已做好（窗口 + 代码右栏 + 她在右下角）"),
    ("02 OFFER",    74, 178,
     "条件句连发：如果我是 X，那么我将献给你 Y —— 全曲最长的乐句段",
     "如果…那么… 的代码结构；她的轮廓随每一句换一种几何"),
    ("03 EXECUTION",178, 232,
     "第一次 EXECUTION：是「为你效劳」而不是死刑",
     "整屏大字 E X E C U T I O N，红色开始渗入"),
    ("04 TRAPPED",  232, 290,
     "但我们被困在模拟之中 / 切换我的性别 / 切换我的角色",
     "自指与置换：左右两栏开始互换内容"),
    ("05 LEFT",     290, 345,
     "你走了 ×6 → 你把我独留在 ISOLATION",
     "窗口开始变空；她的轮廓逐格熄灭"),
    ("06 ILLEGAL",  345, 440,
     "非法参数 → EXECUTION 连呼（中段变「死刑」）→ 六语言计数",
     "全片最强段：EXECUTION 铺满，计数在数自己的死刑"),
    ("07 LEARNED",  440, 459,
     "我学会了如何正确去爱 / 连爱的代数表达式我都知道 / 虽然你已自由，我仍被困在爱之中",
     "回到空窗与光标；代码里出现爱的代数式"),
]

# 关键节点的精确时刻（从骨架取，或按拍算）
KEY_T = {
    "offer_start":   C.beat_t(74),      # 34.31  几何隐喻段起
    "exe_1":         C.beat_t(178),     # 82.31  第一次 EXECUTION
    "trapped":       C.beat_t(232),     # 107.23
    "left_1":        C.beat_t(290),     # 134.00
    "illegal":       C.beat_t(345),     # 159.39
    "countdown":     None,              # 从骨架取（那个 12 秒的洞）
    "learned":       C.beat_t(440),     # 203.23
    "end":           C.beat_t(459),     # 212.00
}


def main():
    skel = json.loads((REPO / "data" / "timing" / "lyrics_synced_notext.json")
                      .read_text(encoding="utf-8"))["lines"]

    # 那个 12 秒的 len=0 洞 = 计数段
    hole = max(skel, key=lambda l: 0 if l["len"] else 1)
    for i, l in enumerate(skel):
        if l["len"] == 0 and i > 90:
            nxt = skel[i + 1] if i + 1 < len(skel) else None
            if nxt:
                KEY_T["countdown"] = sec(l["tag"])
                KEY_T["countdown_end"] = sec(nxt["tag"])
                break

    print("=== 全曲七幕 ===")
    print(f"{'幕':<14} {'起拍':>6} {'止拍':>6} {'起(s)':>8} {'止(s)':>8} {'时长':>7}")
    total = 0.0
    for name, b0, b1, gram, vis in ACTS:
        t0, t1 = C.beat_t(b0), C.beat_t(b1)
        total += t1 - t0
        print(f"{name:<14} {b0:>6} {b1:>6} {t0:>8.2f} {t1:>8.2f} {t1-t0:>7.2f}")
    print(f"{'合计':<14} {'':>6} {'':>6} {'':>8} {'':>8} {total:>7.2f}")

    print("\n=== 关键节点 ===")
    for k, v in KEY_T.items():
        if v is None:
            continue
        print(f"  {k:<16} t={v:>7.2f}  beat {beat(v):>6.1f}")

    print("\n=== 各幕的句式（决定画面用什么结构）===")
    for name, b0, b1, gram, vis in ACTS:
        print(f"\n[{name}]  beat {b0}–{b1}")
        print(f"  句式  {gram}")
        print(f"  画面  {vis}")

    # 已做好的部分与新补部分的分界
    done_end = KEY_T["offer_start"]
    print(f"\n已做好：0.00 – {done_end:.2f}s（{done_end:.0f}s，占 {done_end/212*100:.0f}%）")
    print(f"待补完：{done_end:.2f} – 212.00s（{212-done_end:.0f}s，占 "
          f"{(212-done_end)/212*100:.0f}%）")

    json.dump({"acts": [{"name": n, "b0": b0, "b1": b1, "t0": C.beat_t(b0),
                         "t1": C.beat_t(b1), "grammar": g, "visual": v}
                        for n, b0, b1, g, v in ACTS],
               "keys": KEY_T},
              open(HERE / "cache" / "acts.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n-> cache/acts.json")


if __name__ == "__main__":
    main()

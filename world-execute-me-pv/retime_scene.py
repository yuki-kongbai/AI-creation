#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成 scene08.json —— 内容事件也咬在拍上。

之前剧本里的时间是手写的（0.30 / 0.80 / 1.12 …），对到网格上有 9 处偏 120–222ms。
现在全部从 beat_table 取，每个事件落在整拍或半拍上。

半拍的用法：正文开始比 AI 出现晚半拍，这样"她出现"和"她开口"是两件事，
听起来有先后；全给整拍会显得两块一起砸下来。
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
import beat_table as BT  # noqa: E402
import dense_scene  # noqa: E402


def bt(name: str, half: float = 0.0) -> float:
    """拍点时刻。half=1 表示再晚半拍。"""
    return C.beat_t(BT.BEATS[name]) + half * (C.BEAT / 2)


def main():
    sc = json.loads((HERE / "content" / "scene07.json").read_text(encoding="utf-8"))

    # 每条消息的出现时刻与内部节奏，全部按拍给
    plan = [
        # 用户打字：整拍出现；打字速度按拍算（一个字约 1/8 拍）
        dict(at=bt("c1_user"), time="03:41:22"),
        dict(at=bt("c1_think"), think_at=bt("c1_think"),
             text_at=bt("c1_text", 1), tool_at=bt("c1_tool")),
        dict(at=bt("c2_think"), think_at=bt("c2_think"),
             text_at=bt("c2_text", 1), code_at=bt("c2_code")),
        dict(at=bt("c3_user"), time="03:42:03"),
        dict(at=bt("c3_think"), think_at=bt("c3_think"),
             text_at=bt("c3_text", 1), tool_at=bt("c3_tool")),
        dict(at=bt("c4_think"), think_at=bt("c4_think"),
             text_at=bt("c4_text", 1), table_at=bt("c4_table")),
        dict(at=bt("c5_user"), time="03:46:11"),
        dict(at=bt("c5_think"), think_at=bt("c5_think"),
             text_at=bt("c5_text", 1)),
    ]

    for tn, p in zip(sc["turns"], plan):
        if "at" in p:
            tn["at"] = round(p["at"], 4)
        if "time" in p:
            tn["time"] = p["time"]
        if "think_at" in p and "think" in tn:
            tn["think_at"] = round(p["think_at"], 4)
            tn["think_dur"] = round(C.BEAT / 2, 4)      # 半拍淡入
        if "text_at" in p and "text" in tn:
            tn["text_at"] = round(p["text_at"], 4)
        if "tool_at" in p and "tool" in tn:
            tn["tool"]["at"] = round(p["tool_at"], 4)
        if "code_at" in p and "code" in tn:
            tn["code"]["at"] = round(p["code_at"], 4)
        if "table_at" in p and "table" in tn:
            tn["table"]["at"] = round(p["table_at"], 4)

    # 逐条褪去也按拍走
    c0, c1 = BT.SPANS["clear"]
    sc["_clear"] = {"at": round(C.beat_t(c0), 4),
                    "hold": round((c1 - c0) * C.BEAT, 4)}
    sc["_note"] = ("按 130 BPM 拍点生成。所有时刻来自 beat_table.py，"
                   "偏差 0。改节奏改那张表即可。")

    out = HERE / "content" / "scene08.json"
    out.write_text(json.dumps(sc, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"-> {out}\n")
    print(f"{'轮':>2} {'角色':<10} {'事件':<10} {'t':>8} {'拍':>6}")
    for i, tn in enumerate(sc["turns"]):
        rows = [("at", tn["at"])]
        for k in ("think_at", "text_at"):
            if k in tn:
                rows.append((k, tn[k]))
        for k in ("tool", "code", "table"):
            if k in tn:
                rows.append((k, tn[k]["at"]))
        for k, t in rows:
            b = (t - C.FIRST_BEAT) / C.BEAT
            print(f"{i:2d} {tn['role']:<10} {k:<10} {t:8.3f} {b:6.1f}")
    print(f"   _clear at={sc['_clear']['at']} hold={sc['_clear']['hold']}")


if __name__ == "__main__":
    main()

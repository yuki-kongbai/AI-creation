"""dense_scene.py —— scene02.json 的时间轴。

比 scene.py 多支持三件事，都是为了密度：
  · ai_cont（续写）：同一条回答分几段块，中间不重复头像
  · table 块：逐行揭示
  · tool 块的 style（tree / log）
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(path: Path | None = None) -> dict:
    p = path or (HERE / "content" / "scene02.json")
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _prog(t, at, dur):
    if t <= at:
        return 0.0
    return 1.0 if dur <= 0 else min(1.0, (t - at) / dur)


def _typed(t, at, chars, cps):
    if t <= at:
        return 0
    return min(chars, int((t - at) * cps))


def state_at(scene: dict, t: float) -> dict:
    out = {"t": t, "turns": [], "thinking": False, "streaming": False,
           "cost": 0.0, "clear": 0.0, "kbd": False, "blink": (t % 0.9) < 0.45}
    for tn in scene["turns"]:
        if t < tn["at"]:
            break
        it = {"role": tn["role"], "show": _prog(t, tn["at"], 0.2),
              "time": tn.get("time", ""), "text": "", "n": 0,
              "think": tn.get("think", ""), "think_p": 0.0,
              "code_n": 0, "tool_n": 0, "table_p": 0.0}

        # 思维链：整段淡入
        if tn.get("think"):
            it["think_p"] = _prog(t, tn.get("think_at", tn["at"]),
                                  tn.get("think_dur", 0.3))
            if 0 < it["think_p"] < 1:
                out["thinking"] = True

        # 正文：逐字
        txt = tn.get("text", "")
        if txt:
            n = _typed(t, tn.get("text_at", tn["at"]), len(txt), 46)
            it["n"] = n
            it["text"] = txt[:n]
            if n < len(txt):
                out["streaming"] = True

        if "code" in tn:
            cb = tn["code"]
            it["code_p"] = _prog(t, cb["at"], 0.25)
            n = 0
            if t > cb["at"]:
                n = min(len(cb["lines"]), int((t - cb["at"] - 0.12) * 7))
            it["code_n"] = max(0, n)
            if it["code_p"] > 0 and n < len(cb["lines"]):
                out["streaming"] = True

        if "tool" in tn:
            tl = tn["tool"]
            it["tool_p"] = _prog(t, tl["at"], 0.25)
            n = 0
            if t > tl["at"]:
                n = min(len(tl["lines"]), int((t - tl["at"] - 0.08) * 5))
            it["tool_n"] = max(0, n)
            if it["tool_p"] > 0 and n < len(tl["lines"]):
                out["streaming"] = True

        if "table" in tn:
            tb = tn["table"]
            it["table_p"] = _prog(t, tb["at"], 0.3)
            if 0 < it["table_p"] < 1:
                out["streaming"] = True

        out["turns"].append(it)

    spent = sum(1 for tn in scene["turns"]
                if tn["role"].startswith("ai") and t >= tn["at"] + 1.0)
    out["cost"] = spent * 0.0031

    # ---- 收尾：逐条褪去
    # `_clear` 不是剧本的一部分，是这一段独有的收尾动作：
    #   at 之前：不动
    #   at ~ at+hold：消息从最早的一条开始依次褪掉（不是一起消失 ——
    #                 一起消失像被清空，依次褪去才像"对话结束了"）
    #   之后：空窗，只剩一个闪的光标在等她打字
    cl = scene.get("_clear")
    if cl:
        el = t - cl["at"]
        if el <= 0:
            pass
        elif el < cl["hold"]:
            out["clear"] = el / cl["hold"]
            n = len(out["turns"])
            for i, item in enumerate(out["turns"]):
                # 最早的先走：第 i 条在 clear 走到 i/n 时开始褪
                k = _clamp01((out["clear"] - i / max(1, n)) * n / 1.6)
                item["fade"] = 1.0 - k
        else:
            out["clear"] = 1.0
            out["turns"] = []
            out["kbd"] = True
    return out


def _clamp01(v: float) -> float:
    return 0.0 if v < 0 else 1.0 if v > 1 else v


def duration(scene: dict) -> float:
    last = scene["turns"][-1]
    end = last["at"] + 4.0
    for key in ("code", "tool", "table"):
        if key in last:
            end = max(end, last[key]["at"] + 5.0)
    return end


if __name__ == "__main__":
    sc = load()
    d = duration(sc)
    print(f"时长 {d:.1f}s\n")
    print(f"{'t':>7} {'块数':>5} {'在场':>10} {'末块进度'}")
    for t in [x * 2 for x in range(int(d / 2) + 1)]:
        s = state_at(sc, t)
        n = len(s["turns"])
        last = s["turns"][-1] if n else {}
        state = ("thinking " if s["thinking"] else "") + \
                ("streaming" if s["streaming"] else "")
        prog = (f"字{last.get('n',0):3d} 码{last.get('code_n',0)} "
                f"具{last.get('tool_n',0)} 表{last.get('table_p',0):.1f}")
        print(f"{t:6.1f}s {n:5d} {state:>10}  {prog}")

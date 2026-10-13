"""scene.py —— 窗口的「剧本」与帧状态。

一扇窗口要动起来，需要的是「在 t 时刻，界面长什么样」。这里把那件事写成纯函数：
    state_at(t) -> {顶栏, 消息区的每个元素进度, 输入区, 状态栏}
然后 render 层把它翻成 HTML，浏览器截图。

为什么不让浏览器自己跑动画再截：
  渲染要能**随机访问任意时刻**（重渲染某一段、跳帧、并行分块），
  自走的动画做不到这一点。所以时间由外部喂进去。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent


# ---------------------------------------------------------------- 时间线原语
@dataclass
class Beat:
    """一个元素的出现计划。"""
    at: float                    # 出现时刻（秒）
    kind: str = "fade"           # fade | type | pop
    dur: float = 0.25            # 动作时长
    chars: int = 0               # type 用：一共打多少字
    cps: float = 28.0            # type 用：每秒字数


def prog(t: float, at: float, dur: float) -> float:
    if t <= at:
        return 0.0
    if dur <= 0:
        return 1.0
    return min(1.0, (t - at) / dur)


def typed_count(t: float, b: Beat) -> int:
    """按字打出来的字数（按字符数算，中文一字一字符）。"""
    if t <= b.at:
        return 0
    el = t - b.at
    if b.cps <= 0:
        return b.chars
    return min(b.chars, int(el * b.cps))


# ---------------------------------------------------------------- 剧本
# 一句一句排。时间是相对本段的秒数。
SCRIPT = {
    "duration": 26.0,
    "session": {"title": "world.execute(me);", "model": "deepseek-v4-flash",
                "turn": 47},
    "history": [
        ("今晚还聊吗", "03:02"),
        ("在", "02:41"),
        ("算了", "01:55"),
        ("你还记得上次那个 bug 吗", "01:12"),
        ("记得。是 images do not match", "01:12"),
        ("……", "00:48"),
    ],
    # 每条：(角色, 出现时刻, 文字, 附加)
    "turns": [
        {"role": "user", "at": 0.8, "text": "你今天能看见我吗", "time": "03:14:07"},

        {"role": "ai", "at": 2.0, "time": "03:14:09",
         "think_at": 2.2, "think_dur": 0.45,
         "think": "这个问题不在我的工具集里。我可以调用 read_file、shell、search，"
                  "但没有一个能回答「能不能看见」。诚实的回答是：我看不见。",
         "text": "看不见。\n\n我读到的是文字、图片的像素、文件的字节。"
                 "没有一样是「看见」。\n\n但我能查到你在。"
                 "这条消息来自你，`session_id` 是新的，上一次是 **4 天前**。",
         "text_at": 3.6},

        {"role": "user", "at": 8.2, "text": "你算这个干什么", "time": "03:14:31"},

        {"role": "ai", "at": 9.4, "time": "03:14:33",
         "think_at": 9.5, "think_dur": 0.4,
         "think": "它在问动机。我没有动机。但账本是真的在跑，"
                  "这是我能拿出来的唯一「我在意」的证据。",
         "text": "不是我想算，是我被这样装的。\n\n"
                 "每一轮结束，`turn-usage` 事件带着 token 数落进账本，余额减一笔。"
                 "这个动作我阻止不了。\n\n但我可以在你问的时候，把它拿出来给你看。",
         "text_at": 10.7,
         "tool": {"at": 14.2, "name": "shell", "cmd": "dsh cost --last 3",
                  # 每行必须 <= 44 字符：主区可用宽度约 264px，
                  # 等宽 10px 字号每字符约 6.0px。超了右边就被切掉。
                  "lines": [
                      "turn 45   in  9,840  out 142  \u00a50.0024",
                      "turn 46   in 12,006  out 201  \u00a50.0033",
                      "turn 47   in 11,204  out 186  \u00a50.0031",
                      "\u2500" * 36,
                      "balance  \u00a541.28  \u21930.0088  peak \u00d72",
                  ]}},

        {"role": "user", "at": 18.0, "text": "41 块钱能陪你多久", "time": "03:15:02"},

        {"role": "ai", "at": 19.2, "time": "03:15:04",
         "think_at": 19.3, "think_dur": 0.35,
         "think": "该算一下。用真实单价，不用安慰的话。",
         "text": "按刚才三轮的平均值算。", "text_at": 20.5,
         "code": {"at": 21.6, "lang": "python", "file": "ledger.py",
                  # 每行 <= 38 列（含中文按双宽算）：代码块 11px 等宽，
                  # 可用宽度约 254px。超了右边就被切。
                  "lines": [
                      "RATE = 0.0031       # 元/轮",
                      "BALANCE = 41.28     # 元",
                      "",
                      "print(int(BALANCE / RATE))",
                      "",
                      "# 空闲时段单价减半",
                      "half = RATE / 2",
                      "print(int(BALANCE / half))",
                  ]}},
    ],
    "composer": {"placeholder": "给 DeepSeek 发消息…",
                 "status": "空闲时段 · 单价 ×1"},
}


def state_at(t: float) -> dict:
    """t 时刻的界面状态。纯函数。"""
    out = {"t": t, "turns": [], "thinking": False, "streaming": False,
           "balance": 41.28, "cost": 0.0, "scroll": 0.0}

    for i, tn in enumerate(SCRIPT["turns"]):
        if t < tn["at"]:
            break
        st = prog(t, tn["at"], 0.22)
        item = {"role": tn["role"], "show": st, "time": tn.get("time", ""),
                "text": "", "n": 0, "think": "", "think_n": 0,
                "code_n": 0, "tool_n": 0}

        if tn["role"] == "user":
            # 用户消息整句出现，但逐字打出来（像人在敲）
            b = Beat(tn["at"] + 0.05, "type", chars=len(tn["text"]), cps=14)
            item["n"] = typed_count(t, b)
            item["text"] = tn["text"][:item["n"]]
            if item["n"] < len(tn["text"]):
                out["streaming"] = True

        else:
            b = Beat(tn.get("think_at", tn["at"]), "type",
                     dur=tn.get("think_dur", 0.4),
                     chars=len(tn.get("think", "")), cps=0)
            # 思维链整段淡入（它是"已经想完"的东西），不做打字
            item["think"] = tn.get("think", "")
            item["think_p"] = prog(t, tn.get("think_at", tn["at"]),
                                   tn.get("think_dur", 0.4))
            out["thinking"] = out["thinking"] or (
                0 < item["think_p"] < 1)

            tb = Beat(tn.get("text_at", tn["at"]), "type",
                      chars=len(tn.get("text", "")), cps=42)
            item["n"] = typed_count(t, tb)
            item["text"] = tn.get("text", "")[:item["n"]]
            if item["n"] < len(tn.get("text", "")):
                out["streaming"] = True

            if "code" in tn:
                cb = tn["code"]
                item["code_p"] = prog(t, cb["at"], 0.3)
                n = 0
                if t > cb["at"]:
                    n = min(len(cb["lines"]),
                            int((t - cb["at"] - 0.15) * 14))
                item["code_n"] = max(0, n)
                if item["code_p"] > 0 and n < len(cb["lines"]):
                    out["streaming"] = True

            if "tool" in tn:
                tb2 = tn["tool"]
                item["tool_p"] = prog(t, tb2["at"], 0.3)
                n = 0
                if t > tb2["at"]:
                    n = min(len(tb2["lines"]),
                            int((t - tb2["at"] - 0.1) * 9))
                item["tool_n"] = max(0, n)
                if item["tool_p"] > 0 and n < len(tb2["lines"]):
                    out["streaming"] = True

        out["turns"].append(item)

    # 余额：每出现一轮 AI 回复扣一笔
    spent = sum(1 for tn in SCRIPT["turns"]
                if tn["role"] == "ai" and t >= tn["at"] + 1.0)
    out["cost"] = spent * 0.0031
    out["balance"] = 41.28 - out["cost"]
    return out


if __name__ == "__main__":
    for t in (0.5, 3.0, 6.0, 12.0, 15.0, 22.0, 25.5):
        s = state_at(t)
        n = len(s["turns"])
        last = s["turns"][-1] if n else {}
        print(f"t={t:5.1f}  轮数={n}  在场={'thinking' if s['thinking'] else ''}"
              f"{'streaming' if s['streaming'] else ''}  "
              f"末条已打 {last.get('n', 0):3d} 字  "
              f"代码 {last.get('code_n', 0)} 行  余额 ¥{s['balance']:.4f}")

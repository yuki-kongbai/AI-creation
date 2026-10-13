#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用锚点把歌词逐行钉到时刻上（第二版）。

第一版两个 bug：
  · `LO-O-OVE` 在歌词里出现三次，`raw.index()` 只取到第一个
  · `EIN` 之后骨架行数不够，越界

修法：
  · 锚点用**游标顺序**匹配（从头往后找，取第一个 >= 游标的），
    这样重复词各归其位，不会被第一个吃掉
  · 多语言计数段单独处理：骨架里它是那个 12 秒的空洞，
    按 EIN→LIU 的时刻均匀摊开
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PV2))
import clock as C  # noqa: E402

REPO = Path(r"D:\大肥鱼（deepseek）\.repo\world-execute-me-dsh-pv-main")


def sec(tag: str) -> float:
    mm, rest = tag[1:].split(":")
    return int(mm) * 60 + float(rest[:-1])


# (锚点文本, 第几次出现从 0 计, 骨架行号)
ANCHORS = [
    ("Switch on the power line", 0, 0),
    ("world.execute(me);",       0, 11),
    ("If I'm a set of points",   0, 12),
    ("DIMENSION",                0, 14),
    ("CIRCUMFERENCE",            0, 17),
    ("TANGENTS",                 0, 20),
    ("LIMITATIONS",              0, 23),
    ("Switch my current",        0, 24),
    ("To AC to DC",              0, 25),
    ("So dizzy so dizzy",        0, 27),
    ("To A.D to B.C",            0, 29),
    ("So deeply so deeply",      0, 31),
    ("If I can",                 0, 32),
    ("STIMULATIONS",             0, 34),
    ("SATISFACTION",             0, 37),
    ("If I can make you happy",  0, 38),
    ("EXECUTION",                0, 40),
    ("In this strange strange",  0, 42),
    ("NUTRIENTS",                0, 44),
    ("ANTIOXIDANTS",             0, 47),
    ("ENJOYMENT",                0, 50),
    ("EXISTENCE",                0, 53),
    ("To F to M",                0, 56),
    ("From AM to PM",            0, 59),
    ("The trance the trance",    0, 62),
    ("VIBRATIONS",               0, 65),
    ("COMPLETION",               0, 68),
    ("ISOLATION",                0, 73),
    ("FRAGMENTS",                0, 76),
    ("DISHEARTENED",             0, 79),
    ("ILLEGAL ARGUMENTS",        0, 82),
    ("EIN",                      0, 98),
]


def nth_index(lines, text, n, start=0):
    """第 n 次出现的位置（从 start 往后找）。游标顺序匹配，重复词不会互相吃。"""
    seen = 0
    for i in range(start, len(lines)):
        if lines[i] == text:
            if seen == n:
                return i
            seen += 1
    return None


def main():
    skel = json.loads((REPO / "data" / "timing" / "lyrics_synced_notext.json")
                      .read_text(encoding="utf-8"))["lines"]
    raw = [l.strip() for l in
           (HERE / "cache" / "lyrics_raw.txt").read_text(encoding="utf-8").splitlines()
           if l.strip()]

    pairs = []          # (歌词行号, 时刻)
    cur = 0
    for text, n, si in ANCHORS:
        if si >= len(skel):
            print(f"  跳过 {text}（骨架行号 {si} 越界）")
            continue
        li = nth_index(raw, text, n, cur)
        if li is None:
            print(f"  跳过 {text}（歌词里找不到第 {n} 次）")
            continue
        pairs.append((li, sec(skel[si]["tag"])))
        cur = li + 1

    print(f"锚点命中 {len(pairs)} 个")
    timed = []

    # 段内线性插值
    for k, (li, t) in enumerate(pairs):
        timed.append({"t": t, "en": raw[li], "src": "anchor"})
        if k + 1 < len(pairs):
            li2, t2 = pairs[k + 1]
            gap = li2 - li
            for g in range(1, gap):
                timed.append({"t": round(t + (t2 - t) * g / gap, 3),
                              "en": raw[li + g], "src": "interp"})

    # EIN 之后：计数 + 结尾，摊到 212s
    last_li, last_t = pairs[-1]
    tail = raw[last_li:]
    counts = ["EIN", "DOS", "TROIS", "NE", "FEM", "LIU"]
    # 计数的 6 行固定摊在 190.24 – 205.56（骨架那两个时刻之间）
    t_a, t_b = last_t, 205.56
    for g, w in enumerate(counts):
        if w in tail:
            timed.append({"t": round(t_a + (t_b - t_a) * g / len(counts), 3),
                          "en": w, "src": "count"})
    after = tail[len(counts):] if len(tail) > len(counts) else []
    span = (212.0 - t_b) / max(1, len(after) + 1)
    for g, w in enumerate(after):
        timed.append({"t": round(t_b + span * (g + 1), 3), "en": w, "src": "tail"})

    timed.sort(key=lambda r: r["t"])
    src = {}
    for r in timed:
        src[r["src"]] = src.get(r["src"], 0) + 1
    print(f"共 {len(timed)} 行  覆盖 {timed[0]['t']:.2f} – {timed[-1]['t']:.2f}s  {src}")

    print("\n=== 关键位置复查（应与骨架一致）===")
    for want in ("world.execute(me);", "If I'm a set of points", "If I can make you happy",
                 "EXECUTION", "ILLEGAL ARGUMENTS", "EIN", "EXECUTION"):
        for r in timed:
            if r["en"] == want:
                print(f"  {want:<26} t={r['t']:>7.2f}  "
                      f"beat {(r['t']-C.FIRST_BEAT)/C.BEAT:>6.1f}  [{r['src']}]")
                break

    print("\n=== 逐行（33s 之后）===")
    for r in timed:
        if r["t"] >= 33.0:
            print(f"  {r['t']:>7.2f} {(r['t']-C.FIRST_BEAT)/C.BEAT:>6.1f}  "
                  f"{r['en']:<30} [{r['src']}]")

    (HERE / "cache" / "lyrics_timed.json").write_text(
        json.dumps(timed, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> cache/lyrics_timed.json")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用**词数**而不是行数来核验歌词版本。

之前用「行数 102 vs 129」判定版本不同，但可能只是歌词文件把某些行拆开了
（比如 EXECUTION 连呼在同一行里重复）。

骨架有 98 行的**词数**与逐词时刻。如果词数能对上，就是同一版，
可以直接用逐词时刻做字幕 —— 那才是真正"跟声音对得上"的做法。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(r"D:\大肥鱼（deepseek）\.repo\world-execute-me-dsh-pv-main")
HERE = Path(__file__).resolve().parent


def words(s: str) -> int:
    return len([w for w in re.split(r"\s+", s.strip()) if w])


def main():
    wt = json.loads((REPO / "data" / "timing" / "word_timeline_notext.json")
                    .read_text(encoding="utf-8"))
    sk = wt["skeleton"]
    lines = sk["lines"]
    ws = sk["words"]
    by_line = {}
    for w in ws:
        by_line.setdefault(w["line_id"], []).append(w)
    for k in by_line:
        by_line[k].sort(key=lambda w: w["word_index"])

    lyr = [l.strip() for l in
           (HERE / "cache" / "lyrics_raw.txt").read_text(encoding="utf-8").splitlines()
           if l.strip()]

    print(f"骨架 {len(lines)} 行  歌词 {len(lyr)} 行")
    print(f"骨架词数合计 {len(ws)}   歌词词数合计 {sum(words(l) for l in lyr)}\n")

    # 骨架每行的词数
    sk_wc = [len(by_line.get(l["id"], [])) for l in lines]
    ly_wc = [words(l) for l in lyr]
    print("骨架每行词数（前 30）：")
    print("  " + " ".join(str(x) for x in sk_wc[:30]))
    print("歌词每行词数（前 30）：")
    print("  " + " ".join(str(x) for x in ly_wc[:30]))
    print()

    # 逐行比对：骨架行 -> 歌词行（贪心，允许歌词多行合成一行或用一行拆多行）
    print(f"{'骨架#':>5} {'词数':>4} {'歌词#':>5} {'歌词词数':>8}  判定   歌词")
    i = j = 0
    match = 0
    while i < len(lines) and j < len(lyr):
        a, b = sk_wc[i], ly_wc[j]
        if a == b:
            flag = "OK"
            match += 1
            i += 1
            j += 1
        elif b < a and j + 1 < len(lyr) and ly_wc[j] + ly_wc[j + 1] == a:
            flag = "歌词两行合成一行"
            i += 1
            j += 2
        elif a < b and i + 1 < len(lines) and sk_wc[i] + sk_wc[i + 1] == b:
            flag = "骨架两行对一行"
            i += 2
            j += 1
        else:
            flag = f"对不上"
            i += 1
            j += 1
        if i <= 32:
            print(f"{lines[i-1]['id'] if i else 0:>5} {a:>4} {j-1:>5} {b:>8}  {flag:<18} {lyr[j-1][:30] if j else ''}")

    print(f"\n逐行命中 {match} 行（骨架 {len(lines)} / 歌词 {len(lyr)}）")
    if match >= len(lines) * 0.85:
        print("结论：**很可能是同一版**，可以对上 —— 那就用逐词时刻做字幕")
    else:
        print("结论：版本不同，逐词时刻不能直接用于这份歌词")


if __name__ == "__main__":
    main()

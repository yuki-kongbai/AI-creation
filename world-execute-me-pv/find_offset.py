#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""找歌词与时刻骨架的错位点。

骨架 102 行，歌词 129 行，所以行号不能直接对应。
但骨架里存了**每行的字符数**（len，含一个前导空格）。
用它逐行比对歌词长度，就能找出从哪里开始错位、以及骨架漏掉了哪些行。
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(r"D:\大肥鱼（deepseek）\.repo\world-execute-me-dsh-pv-main")
HERE = Path(__file__).resolve().parent

LRC = Path(HERE / "cache" / "lyrics_raw.txt")


def main():
    skel = json.loads((REPO / "data" / "timing" / "lyrics_synced_notext.json")
                      .read_text(encoding="utf-8"))["lines"]
    lens = [l["len"] for l in skel]
    print(f"骨架 {len(lens)} 行，每行字符数（含前导空格）：")
    print("  " + " ".join(str(x) for x in lens[:40]))
    print("  " + " ".join(str(x) for x in lens[40:80]))
    print("  " + " ".join(str(x) for x in lens[80:]))
    print()

    # 从 append 的文件里读歌词
    if not LRC.exists():
        print(f"缺少 {LRC}")
        return
    lines = [l.rstrip("\n") for l in LRC.read_text(encoding="utf-8").splitlines() if l.strip()]
    ly = [len(" " + l.strip()) for l in lines]      # 骨架的 len 是含前导空格的
    print(f"歌词 {len(ly)} 行，同样算法：")
    print("  " + " ".join(str(x) for x in ly[:40]))
    print("  " + " ".join(str(x) for x in ly[40:80]))
    print("  " + " ".join(str(x) for x in ly[80:]))
    print()

    # 贪心对齐：骨架第 i 行匹配歌词第 j 行
    j = 0
    mis = []
    for i, L in enumerate(lens):
        if j >= len(ly):
            mis.append((i, j, L, None))
            continue
        if L == ly[j]:
            j += 1
            continue
        # 长度不等：往后找几行看是否有匹配（说明骨架漏了行）
        found = None
        for k in range(1, 6):
            if j + k < len(ly) and ly[j + k] == L:
                found = k
                break
        if found:
            mis.append((i, j, L, found))
            j += found + 1
        else:
            mis.append((i, j, L, 0))
            j += 1

    print(f"错位 {len(mis)} 处（骨架行号, 歌词行号, 骨架len, 跳过几行歌词）")
    for i, jj, L, k in mis[:24]:
        print(f"  骨架#{i:>3} 歌词#{jj:>3}  len={L:>3}  "
              f"{'骨架漏了 '+str(k)+' 行歌词' if k else '长度对不上'}")
    print(f"\n最终歌词指针到 {j} / {len(ly)}")


if __name__ == "__main__":
    main()

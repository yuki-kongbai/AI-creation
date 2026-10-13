#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用骨架的整行 sha256 逐行校验歌词文本。

骨架存的是**整行**（含时间标签、前导空格、行尾 CRLF）的 sha256。
所以只要拼出 `[tag] text\r\n`，就能验证歌词的每一个字符对不对 ——
比"长度差不多"硬得多，也比我猜可靠得多。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(r"D:\大肥鱼（deepseek）\.repo\world-execute-me-dsh-pv-main")
HERE = Path(__file__).resolve().parent


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main():
    skel = json.loads((REPO / "data" / "timing" / "lyrics_synced_notext.json")
                      .read_text(encoding="utf-8"))["lines"]
    lines = [l.rstrip() for l in
             (HERE / "cache" / "lyrics_raw.txt").read_text(encoding="utf-8").splitlines()
             if l.strip()]

    print(f"骨架 {len(skel)} 行 / 歌词 {len(lines)} 行\n")

    # 先确认第 0 行到底怎么拼才命中
    l0 = skel[0]
    print("第 0 行的各种拼法：")
    for lab, cand in (
        (f"{l0['tag']} Switch on the power line\\r\\n",
         f"{l0['tag']} Switch on the power line\r\n"),
        (f"{l0['tag']} Switch on the power line\\n",
         f"{l0['tag']} Switch on the power line\n"),
        (f"{l0['tag']} Switch on the power line",
         f"{l0['tag']} Switch on the power line"),
        (f"{l0['tag']} Switch on the power line ",
         f"{l0['tag']} Switch on the power line "),
    ):
        hit = sha(cand) == l0["sha256"]
        print(f"   {lab:<44} len={len(cand):>3}  {'<<< 命中' if hit else ''}")

    # 用命中的那种拼法逐行核对
    def variants(text, tag):
        yield f"{tag} {text}\r\n", "tag+sp+text+CRLF"
        yield f"{tag} {text}\n", "tag+sp+text+LF"
        yield f"{tag} {text}", "tag+sp+text"
        yield f"{tag}{text}\r\n", "tag+text+CRLF"

    print("\n逐行核对（命中数 / 总行数）：")
    hit = 0
    bad = []
    for i, sk in enumerate(skel):
        if sk["len"] == 0:
            # 间奏空行：只有 tag
            cands = [f"{sk['tag']}\r\n", f"{sk['tag']}\n", sk["tag"]]
            if any(sha(c) == sk["sha256"] for c in cands):
                hit += 1
            continue
        if i >= len(lines):
            bad.append((i, "歌词行数不够", ""))
            continue
        txt = lines[i]
        got = False
        for c, lab in variants(txt, sk["tag"]):
            if sha(c) == sk["sha256"]:
                hit += 1
                got = True
                break
        if not got:
            bad.append((i, f"len骨架{sk['len']} vs 我算{len(' ' + txt)}", txt[:40]))

    print(f"  命中 {hit} / {len(skel)}")
    if bad:
        print(f"\n未命中 {len(bad)} 行：")
        for i, why, txt in bad[:30]:
            print(f"   #{i:>3}  {why:<28}  {txt}")
        print(f"\n结论：歌词文本与骨架**不一致**（或我拿到的不是 LRCLIB 那一版）")
    else:
        print("\n结论：歌词文本与骨架**完全一致** —— 这是 LRCLIB 那一版，逐字符吻合")


if __name__ == "__main__":
    main()

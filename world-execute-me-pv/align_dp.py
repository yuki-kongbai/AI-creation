#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用动态规划把歌词行对齐到骨架行的时刻上。

为什么用 DP 而不是逐行贪心：
    骨架 102 行 / 395 词，歌词 129 行 / 396 词 —— **总数几乎相同**，
    但断行方式不同（我的文件把 EXECUTION 连呼拆成多行，LRC 里是一行）。
    逐行比对必然错位，而全局对齐能把总数吻合这件事用上。

DP 的代价 = 词数差的平方；允许 1:1 / 1:N / N:1 三种对应。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PV2))
import clock as C  # noqa: E402

REPO = Path(r"D:\大肥鱼（deepseek）\.repo\world-execute-me-dsh-pv-main")
INF = 1e18


def sec(tag: str) -> float:
    mm, rest = tag[1:].split(":")
    return int(mm) * 60 + float(rest[:-1])


def wc(s: str) -> int:
    return len([w for w in re.split(r"\s+", s.strip()) if w])


def main():
    wt = json.loads((REPO / "data" / "timing" / "word_timeline_notext.json")
                    .read_text(encoding="utf-8"))
    sk = wt["skeleton"]
    times = [l["start"] for l in sk["lines"]]
    ends = [l["end"] for l in sk["lines"]]
    by_line = {}
    for w in sk["words"]:
        by_line.setdefault(w["line_id"], []).append(w)
    sk_wc = [len(by_line.get(l["id"], [])) for l in sk["lines"]]
    # 骨架词数为 0 的行（空行）给 0
    sk_wc = [0 if l.get("words") in (None, []) and not by_line.get(l["id"]) else x
             for l, x in zip(sk["lines"], sk_wc)]

    lyr = [l.strip() for l in
           (HERE / "cache" / "lyrics_raw.txt").read_text(encoding="utf-8").splitlines()
           if l.strip()]
    ly_wc = [wc(l) for l in lyr]

    N, M = len(sk_wc), len(ly_wc)
    print(f"骨架 {N} 行 / {sum(sk_wc)} 词    歌词 {M} 行 / {sum(ly_wc)} 词")

    # DP：dp[i][j] = 前 i 个骨架行 配 前 j 个歌词行 的最小代价
    dp = [[INF] * (M + 1) for _ in range(N + 1)]
    bk = [[None] * (M + 1) for _ in range(N + 1)]
    for i in range(N + 1):
        dp[i][0] = 0.0
        bk[i][0] = ("skip_s", i - 1, 0) if i else None
    for j in range(M + 1):
        dp[0][j] = 0.0
    for i in range(1, N + 1):
        for j in range(1, M + 1):
            best, arg = INF, None
            # 1:1
            c = dp[i - 1][j - 1] + (sk_wc[i - 1] - ly_wc[j - 1]) ** 2
            if c < best:
                best, arg = c, ("1:1", i - 1, j - 1)
            # 1:N（一个骨架行对多个歌词行，N<=4）
            for k in range(2, 5):
                if j - k < 0:
                    break
                c = dp[i - 1][j - k] + (sk_wc[i - 1] - sum(ly_wc[j - k:j])) ** 2
                if c < best:
                    best, arg = c, (f"1:{k}", i - 1, j - k)
            # N:1（多个骨架行对一个歌词行，N<=4）
            for k in range(2, 5):
                if i - k < 0:
                    break
                c = dp[i - k][j - 1] + (sum(sk_wc[i - k:i]) - ly_wc[j - 1]) ** 2
                if c < best:
                    best, arg = c, (f"{k}:1", i - k, j - 1)
            # 跳过骨架行（空行）
            c = dp[i - 1][j] + 1.0
            if c < best:
                best, arg = c, ("skip_s", i - 1, j)
            dp[i][j] = best
            bk[i][j] = arg

    # 回溯
    assign = [None] * M              # 歌词行 -> 时刻
    i, j = N, M
    steps = []
    while i > 0 or j > 0:
        if bk[i][j] is None:
            break
        kind, pi, pj = bk[i][j]
        if kind == "1:1":
            assign[j - 1] = times[i - 1]
            steps.append((kind, i - 1, j - 1))
        elif kind.startswith("1:"):
            k = int(kind.split(":")[1])
            t0 = times[i - 1]
            t1 = ends[i - 1]
            for g in range(k):
                assign[j - k + g] = t0 + (t1 - t0) * g / max(1, k)
            steps.append((kind, i - 1, j - k))
        elif kind.endswith(":1"):
            assign[j - 1] = times[i - k if False else pi]
            steps.append((kind, pi, j - 1))
        i, j = pi, pj

    miss = sum(1 for a in assign if a is None)
    print(f"DP 代价 {dp[N][M]:.0f}   未分配歌词行 {miss}")
    print(f"对应方式统计：")
    from collections import Counter
    for k, v in Counter(s[0] for s in steps).most_common():
        print(f"  {k:<7} {v}")

    out = []
    for k, l in enumerate(lyr):
        t = assign[k]
        if t is None:
            continue
        out.append({"t": round(t, 3), "en": l, "src": "dp"})
    out.sort(key=lambda r: r["t"])

    bad = sum(1 for a, b in zip(out, out[1:]) if b["t"] < a["t"] - 1e-6)
    print(f"\n对齐出 {len(out)} 行，覆盖 {out[0]['t']:.2f} – {out[-1]['t']:.2f}s  乱序 {bad}")

    print("\n抽查：")
    for want in ("Switch on the power line", "world.execute(me);",
                 "If I'm a set of points", "If I can make you happy",
                 "You have left", "ILLEGAL ARGUMENTS", "EIN",
                 "Though you are free", "LO-O-OVE"):
        for r in out:
            if r["en"] == want:
                print(f"  {want:<28} t={r['t']:>7.2f}  beat {(r['t']-C.FIRST_BEAT)/C.BEAT:>6.1f}")
                break

    (HERE / "cache" / "lyrics_timed.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> cache/lyrics_timed.json")


if __name__ == "__main__":
    main()

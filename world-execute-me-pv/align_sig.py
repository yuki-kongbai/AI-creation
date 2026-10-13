#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用词长签名做全局对齐（第四版：修正了锚点错位的根本 bug）。

前三版错在哪：
  第一版  按行号一对一 —— 我的歌词 129 行、骨架 98 行，断行方式不同
  第二版  拿总词数做 DP —— 信号太弱，尾部跳行
  第三版  用锚点表手钉   —— **两个时刻文件里都没有 `world.execute(me);` 这一行**，
                          我却把它钉到了 lyrics_synced 行 11，于是整条轴系统性挪位

这一版的钥匙：骨架每行带 `spans`（每词在行内的字符区间），
等于给出**每行每个词的确切长度**：
    行 0  spans → 词长 [6,2,3,5,4]   "Switch on the power line" [6,2,3,5,4]  ✓
一整行所有词的长度同时吻合，是很强的约束，误配概率极低。

三处关键改动：
  1. 允许**跳过歌词行**（`world.execute(me);` 这类骨架里没有的行），
     而不是硬塞进别人的行里 —— 上一版就是硬塞才把时间挪错的
  2. 逐行报告匹配置信度，**高代价的行必须人工看**，不能默默放过
  3. 时刻取**每行第一个词的 start**（起唱点），不是行标签时刻
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


def sig_spans(spans) -> list[int]:
    return [b - a for a, b in spans]


def sig_text(s: str) -> list[int]:
    return [len(w) for w in re.split(r"\s+", s.strip()) if w]


def cost(a: list[int], b: list[int]) -> float:
    """词长签名距离。长度不等重罚，长度相等按逐词平方差。"""
    if not a and not b:
        return 0.0
    if len(a) != len(b):
        return 80.0 + 8.0 * abs(len(a) - len(b))
    return float(sum((x - y) ** 2 for x, y in zip(a, b)))


def main():
    wt = json.loads((REPO / "data" / "timing" / "word_timeline_notext.json")
                    .read_text(encoding="utf-8"))
    meta = {l["id"]: l for l in wt["lines"]}
    sk = wt["skeleton"]
    words = sk["words"]

    first = {}
    for w in words:
        k = w["line_id"]
        if k not in first or w["word_index"] < first[k]["word_index"]:
            first[k] = w

    sk_sig, sk_t0, sk_t1 = [], [], []
    for l in sk["lines"]:
        spans = (meta.get(l["id"]) or {}).get("spans") or []
        sk_sig.append(sig_spans(spans))
        sk_t0.append(first.get(l["id"], {}).get("start", l["start"]))
        sk_t1.append(l["end"])

    lyr = [l.strip() for l in
           (HERE / "cache" / "lyrics_raw.txt").read_text(encoding="utf-8").splitlines()
           if l.strip()]
    ly_sig = [sig_text(l) for l in lyr]

    N, M = len(sk_sig), len(ly_sig)
    dp = [[INF] * (M + 1) for _ in range(N + 1)]
    bk = [[None] * (M + 1) for _ in range(N + 1)]
    dp[0][0] = 0.0
    SKIP_LY = 120.0          # 跳过一行歌词的代价（骨架里没有这一行）
    SKIP_SK = 2.0            # 跳过骨架空行的代价

    for i in range(N + 1):
        for j in range(M + 1):
            if dp[i][j] >= INF:
                continue
            if i < N and j < M:                      # 1:1
                c = dp[i][j] + cost(sk_sig[i], ly_sig[j])
                if c < dp[i + 1][j + 1]:
                    dp[i + 1][j + 1] = c
                    bk[i + 1][j + 1] = ("1:1", i, j)
            if i < N and j < M:                      # 骨架一行 = 歌词多行
                for k in range(2, 5):
                    if j + k > M:
                        break
                    m = [x for g in range(k) for x in ly_sig[j + g]]
                    c = dp[i][j] + cost(sk_sig[i], m) + 6.0 * (k - 1)
                    if c < dp[i + 1][j + k]:
                        dp[i + 1][j + k] = c
                        bk[i + 1][j + k] = (f"1:{k}", i, j)
            if i < N and j < M:                      # 歌词一行 = 骨架多行
                for k in range(2, 4):
                    if i + k > N:
                        break
                    m = [x for g in range(k) for x in sk_sig[i + g]]
                    c = dp[i][j] + cost(m, ly_sig[j]) + 6.0 * (k - 1)
                    if c < dp[i + k][j + 1]:
                        dp[i + k][j + 1] = c
                        bk[i + k][j + 1] = (f"{k}:1", i, j)
            if j < M:                                # **跳过一行歌词**
                c = dp[i][j] + SKIP_LY
                if c < dp[i][j + 1]:
                    dp[i][j + 1] = c
                    bk[i][j + 1] = ("skip_ly", i, j)
            if i < N and not sk_sig[i]:              # 跳过骨架空行
                c = dp[i][j] + SKIP_SK
                if c < dp[i + 1][j]:
                    dp[i + 1][j] = c
                    bk[i + 1][j] = ("skip_sk", i, j)

    print(f"骨架 {N} 行 / 歌词 {M} 行   DP 代价 {dp[N][M]:.0f}")

    assign = [None] * M
    quality = {}
    i, j = N, M
    from collections import Counter
    steps = []
    while (i, j) != (0, 0):
        e = bk[i][j]
        if e is None:
            break
        kind, pi, pj = e
        if kind == "1:1":
            assign[pj] = (sk_t0[pi], sk_t1[pi])
            quality[pj] = cost(sk_sig[pi], ly_sig[pj])
            steps.append(kind)
        elif kind.startswith("1:"):
            k = int(kind.split(":")[1])
            t0, t1 = sk_t0[pi], sk_t1[pi]
            for g in range(k):
                assign[pj + g] = (t0 + (t1 - t0) * g / k, t0 + (t1 - t0) * (g + 1) / k)
                quality[pj + g] = 0.0
            steps.append(kind)
        elif kind.endswith(":1"):
            k = int(kind.split(":")[0])
            assign[pj] = (sk_t0[pi], sk_t1[pi + k - 1])
            quality[pj] = cost([x for g in range(k) for x in sk_sig[pi + g]], ly_sig[pj])
            steps.append(kind)
        elif kind == "skip_ly":
            steps.append("skip_ly")
        i, j = pi, pj

    for k, v in Counter(steps).most_common():
        print(f"  {k:<9} {v}")

    got = [k for k in range(M) if assign[k] is not None]
    print(f"\n已定位 {len(got)} / {M} 行歌词")

    # ---- 匹配质量：高代价的行必须报出来
    bad = sorted(((quality.get(k, 0.0), k) for k in got), reverse=True)[:12]
    print(f"\n匹配置信度最差的 12 行（代价高 = 可能配错，必须人工看）：")
    for c, k in bad:
        print(f"  代价 {c:>6.1f}  歌词#{k:>3}  {lyr[k][:40]}")

    # ---- 每行起唱时刻 vs 结束
    out = []
    for k in got:
        t0, t1 = assign[k]
        out.append({"t": round(t0, 3), "end": round(t1, 3), "en": lyr[k],
                    "src": "sig", "cost": round(quality.get(k, 0.0), 1)})
    out.sort(key=lambda r: r["t"])

    print(f"\n覆盖 {out[0]['t']:.2f} – {out[-1]['t']:.2f}s")
    print("\n关键位置：")
    for want in ("Switch on the power line", "If I'm a set of points",
                 "If I'm a circle", "If I can make you happy", "EXECUTION",
                 "You have left", "ILLEGAL ARGUMENTS", "EIN", "LO-O-OVE"):
        hits = [r for r in out if r["en"] == want]
        if hits:
            r = hits[0]
            print(f"  {want:<28} t={r['t']:>7.2f}  拍 {(r['t']-C.FIRST_BEAT)/C.BEAT:>6.1f}"
                  f"   代价 {r['cost']}")

    print("\n=== 28–70s 逐行（这一段是我之前挪位最严重的地方）===")
    for r in out:
        if 28 <= r["t"] <= 70:
            print(f"  {r['t']:>7.2f} → {r['end']:>7.2f}  {r['en']}")

    (HERE / "cache" / "lyrics_timed.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> cache/lyrics_timed.json（{len(out)} 行）")


if __name__ == "__main__":
    main()

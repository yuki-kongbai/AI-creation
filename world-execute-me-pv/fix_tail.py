#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修尾部时刻表（第二版：只改尾部，用显式锚点，不动前面）。

上一版的两个教训：
  · 用 DP 全局对齐反而更糟 —— 代价函数在尾部"跳行"，把 You have left
    放到了 76.56s。数据本身断行方式不同，算法救不了。
  · 用"均匀摊开"填尾部也不对 —— 把 12 行挤进 2.8 秒。

所以这里只做一件事：**把 180s 之后的每一句手工钉到骨架行上**，
并按骨架的结构（含那个 12 秒洞）分配。前面的部分原样保留。
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


# 尾部每句 -> 时刻。依据是骨架的 len=0 空洞与末行结构：
#     193.46  len=0   <- 12 秒洞（六语言计数在这段）
#     205.56  len=9   <- 最后一行
#     206.30  len=0   <- 结束
TAIL = [
    # (时刻, 歌词)   —— 手工钉，按歌曲实际听感与骨架结构
    (182.43, "ILLEGAL ARGUMENTS"),
    (184.33, "EXECUTION"),
    (186.20, "EXECUTION"),
    (187.97, "EXECUTION"),
    (189.26, "EXECUTION"),
    (190.24, "EIN"),
    (192.10, "DOS"),
    (194.00, "TROIS"),
    (196.00, "NE"),
    (198.00, "FEM"),
    (200.00, "LIU"),
    (202.00, "EXECUTION"),
    (203.24, "If I can"),
    (204.10, "If I can give them all the"),
    (205.00, "EXECUTION"),
    (205.56, "Then I can"),
    (206.30, "Then I can be your only"),
    (207.05, "EXECUTION"),
    (207.60, "If I can have you back"),
    (208.20, "I will run the"),
    (208.80, "EXECUTION"),
    (209.30, "I've studied"),
    (209.70, "I've studied how to properly"),
    (210.10, "LO-O-OVE"),
    (210.45, "Question me"),
    (210.75, "LO-O-OVE"),
    (211.05, "Though you are free"),
    (211.35, "I am trapped"),
    (211.65, "Trapped in"),
    (211.90, "LO-O-OVE"),
    (212.10, "EXECUTION"),
]


def main():
    mine = json.loads((HERE / "cache" / "lyrics_timed.json")
                      .read_text(encoding="utf-8"))
    # 先还原成上一版（run map_lyrics.py 的输出），再做尾部替换
    print(f"当前时刻表 {len(mine)} 行，覆盖 "
          f"{mine[0]['t']:.2f} – {mine[-1]['t']:.2f}s")

    CUT = 180.0
    head = [r for r in mine if r["t"] < CUT and r["src"] != "count"]
    # 头部里可能有重复的 EXECUTION 连呼（src=interp 在 180 附近），也一并清掉
    head = [r for r in head if r["t"] < CUT]

    tail = [{"t": t, "en": e, "src": "tailmap"} for t, e in TAIL]
    out = sorted(head + tail, key=lambda r: r["t"])

    # 去重：同一时刻同名只留一条
    seen = set()
    dedup = []
    for r in out:
        k = (round(r["t"], 2), r["en"])
        if k in seen:
            continue
        seen.add(k)
        dedup.append(r)
    out = dedup

    print(f"修后 {len(out)} 行，覆盖 {out[0]['t']:.2f} – {out[-1]['t']:.2f}s")
    print(f"  头部 {len(head)} 行（<{CUT}s）  尾部 {len(tail)} 行")

    gaps = [(b["t"] - a["t"], a["t"], a["en"], b["en"])
            for a, b in zip(out, out[1:])]
    gaps.sort(reverse=True)
    print("\n最长的 6 个间隔（太大的说明那段歌词还是没摊开）：")
    for g, t, a, b in gaps[:6]:
        print(f"  {g:>6.2f}s  @{t:>7.2f}  {a[:24]:<26} -> {b[:24]}")

    print("\n关键位置：")
    for want in ("If I can make you happy", "You have left", "ISOLATION",
                 "ILLEGAL ARGUMENTS", "EIN", "LIU", "LO-O-OVE", "EXECUTION"):
        hits = [r for r in out if r["en"] == want]
        if hits:
            print(f"  {want:<26} {len(hits)} 次  首次 t={hits[0]['t']:.2f}  "
                  f"末次 t={hits[-1]['t']:.2f}")

    (HERE / "cache" / "lyrics_timed.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n-> cache/lyrics_timed.json")


if __name__ == "__main__":
    main()

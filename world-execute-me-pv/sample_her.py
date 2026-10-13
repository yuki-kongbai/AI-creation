#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把她的立绘采样成一团**沿轮廓排列**的点。

第一版错了：直接从边缘像素里随机取点，点的**顺序**是乱的，
于是"相邻点连线"画出来是一团乱麻（见 her_cloud.png）。

修法：先把轮廓**跟踪成一条路径**，再沿路径均匀重采样。
这样相邻点在画面里也相邻，连线就是她的线稿。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
sys.path.insert(0, str(PV2))
sys.path.insert(0, str(HERE))

import field  # noqa: E402
import tk  # noqa: E402

BOX = (83, 0, 856, 894)
DS = 4          # 降采样倍数（轮廓跟踪在这个尺度上做，快得多）


def trace_contour(mask: np.ndarray) -> np.ndarray:
    """把二值掩码的**最大轮廓**跟踪成一条有序路径。

    做法：取边界像素，从最上面那个开始，反复走到最近的未访问边界像素。
    朴素但稳 —— 对剪影这种单连通形状足够。
    """
    m = mask.copy()
    b = np.zeros_like(m)
    b[1:-1, 1:-1] = (m[1:-1, 1:-1] &
                     ~(m[:-2, 1:-1] & m[2:, 1:-1] & m[1:-1, :-2] & m[1:-1, 2:]))
    ys, xs = np.nonzero(b)
    pts = np.stack([xs, ys], axis=1).astype(np.float64)
    if len(pts) == 0:
        return pts
    print(f"    边界像素 {len(pts)}")

    # 从最上面、最左的那个开始
    start = int(np.lexsort((pts[:, 0], pts[:, 1]))[0])
    order = [start]
    used = np.zeros(len(pts), dtype=bool)
    used[start] = True
    cur = start
    MAXJ = 90.0          # 单步最大跳跃（降采样坐标）
    for _ in range(len(pts) - 1):
        rem = ~used
        if not rem.any():
            break
        d = np.linalg.norm(pts - pts[cur], axis=1)
        d[~rem] = 1e9
        # 只考虑不太远的，避免跳到另一条边
        near = d < MAXJ
        if not near.any():
            near = np.ones(len(pts), dtype=bool)
            near[~rem] = False
        cand = np.where(near)[0]
        nxt = cand[np.argmin(d[cand])]
        order.append(nxt)
        used[nxt] = True
        cur = nxt
    return pts[order]


def main():
    src = tk.sprite_src("maid-right", "full").crop(BOX)
    a = np.asarray(src.getchannel("A"))
    print(f"她的不透明像素 {int((a > 110).sum())}")

    # 降采样后取掩码
    small = src.resize((src.width // DS, src.height // DS), Image.LANCZOS)
    m = np.asarray(small.getchannel("A")) > 110
    print(f"  降采样到 {small.size}，掩码像素 {int(m.sum())}")

    # 只保留最大连通域，避免小碎片把路径带偏
    from scipy_free_cc import largest_cc   # 本地实现，见下
    m = largest_cc(m)
    print(f"  最大连通域 {int(m.sum())}")

    path = trace_contour(m)
    print(f"  路径点数 {len(path)}")
    if len(path) < 50:
        print("  路径太短，放弃")
        return

    # 在**跳变处断开**：轮廓跟踪遇到不连通的部位（笔记本、手臂）会一步跳过去，
    # 那一步在画面上就是一条横跨的长线。断成若干段，分段重采样，
    # 连线时跳过段界 —— 这样长线就没了。
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    cut = np.where(seg > max(4.0, float(np.median(seg)) * 4))[0] + 1
    bounds = np.r_[0, cut, len(path)]
    parts = [path[bounds[i]:bounds[i + 1]] for i in range(len(bounds) - 1)]
    parts = [p for p in parts if len(p) >= 2]
    lens = np.array([float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())
                     for p in parts])
    print(f"  断成 {len(parts)} 段，长度占比 "
          f"{np.round(lens / lens.sum(), 3)[:8]}")

    # 按长度比例分配点数
    alloc = np.maximum(2, np.round(lens / lens.sum() * field.NP).astype(int))
    while alloc.sum() > field.NP:
        alloc[int(np.argmax(alloc))] -= 1
    while alloc.sum() < field.NP:
        alloc[int(np.argmax(lens))] += 1

    pts_list, seg_id = [], []
    for k, (p, na) in enumerate(zip(parts, alloc)):
        rs = field._resample(p, na)
        pts_list.append(rs)
        seg_id.append(np.full(na, k))
    rs = np.concatenate(pts_list, axis=0)
    seg_id = np.concatenate(seg_id, axis=0)

    pts = np.stack([rs[:, 0] / small.width, rs[:, 1] / small.height], axis=1)
    np.save(HERE / "cache" / "her_points.npy", pts)
    np.save(HERE / "cache" / "her_segid.npy", seg_id)
    print(f"-> cache/her_points.npy  {pts.shape}   段数 {len(parts)}")

    import audio
    W, H = 700, 460
    img = Image.new("RGB", (W, H), tk.BG)
    field.draw_cloud(img, field.sh_her(pts, W, H), 20.0, audio.at(40.0),
                     seg=seg_id)
    img.save(HERE / "out" / "her_cloud.png")
    print("-> out/her_cloud.png")


if __name__ == "__main__":
    main()

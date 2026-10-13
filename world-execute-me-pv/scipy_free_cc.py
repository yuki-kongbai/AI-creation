#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""最大连通域（纯 numpy 实现，避免依赖 scipy）。"""
from __future__ import annotations

import numpy as np


def largest_cc(mask: np.ndarray) -> np.ndarray:
    """返回只含最大四连通域的布尔掩码。

    用迭代式洪泛（显式栈），避免递归爆栈。
    """
    H, W = mask.shape
    lab = np.zeros((H, W), np.int32)
    best_id, best_n = 0, 0
    cur = 0
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys, xs):
        if lab[y0, x0] or not mask[y0, x0]:
            continue
        cur += 1
        stack = [(y0, x0)]
        lab[y0, x0] = cur
        n = 0
        while stack:
            y, x = stack.pop()
            n += 1
            if y > 0 and mask[y - 1, x] and not lab[y - 1, x]:
                lab[y - 1, x] = cur
                stack.append((y - 1, x))
            if y < H - 1 and mask[y + 1, x] and not lab[y + 1, x]:
                lab[y + 1, x] = cur
                stack.append((y + 1, x))
            if x > 0 and mask[y, x - 1] and not lab[y, x - 1]:
                lab[y, x - 1] = cur
                stack.append((y, x - 1))
            if x < W - 1 and mask[y, x + 1] and not lab[y, x + 1]:
                lab[y, x + 1] = cur
                stack.append((y, x + 1))
        if n > best_n:
            best_n, best_id = n, cur
    return lab == best_id

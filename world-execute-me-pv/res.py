#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""res.py —— 分辨率缩放。

要把成片提到 2K，最省事又不出错的做法不是把几百处坐标逐个乘 2，
而是：
  · 坐标层：用一个 **SDraw** 包装 ImageDraw，把传进来的坐标自动乘 S
  · 字体层：各模块的字体助手（_mono / _cjk）把字号乘 S
    这样所有文字自动变大，而调用处的写法一行都不用改
  · 文本宽度：SDraw.textlength 把结果**除回 S**，
    这样 `x + d.textlength(...)` 仍在 1× 坐标里，不会被重复缩放

S 由环境变量 PVW_SCALE 控制，默认 2（2560×1440）。
"""
from __future__ import annotations

import os

S = float(os.environ.get("PVW_SCALE", "2"))
# 成片尺寸：1× 是 1280×720
BASE_W, BASE_H = 1280, 720
OUT_W, OUT_H = int(BASE_W * S), int(BASE_H * S)


def px(v: float) -> int:
    """把 1× 的设计像素换算成输出像素（字号用）。"""
    return max(5, int(round(v * S)))


class SDraw:
    """把 ImageDraw 的坐标自动乘以 S 的包装器。

    只包住坐标与线宽；`textlength` / `getlength` 把结果除回 1×，
    否则 `x + textlength(...)` 会被缩放两次。
    """

    __slots__ = ("_d", "_s")

    def __init__(self, d, s: float = S):
        self._d = d
        self._s = s

    # ---- 坐标类
    def _xy(self, xy):
        s = self._s
        if isinstance(xy, (list, tuple)) and len(xy) == 2 and \
                not isinstance(xy[0], (list, tuple)):
            return (xy[0] * s, xy[1] * s)
        return [v * s for v in xy]

    def _kw(self, kw):
        for k in ("width", "radius"):
            if k in kw and kw[k] is not None:
                kw[k] = max(1, int(round(kw[k] * self._s)))
        return kw

    def text(self, xy, *a, **k):
        return self._d.text(self._xy(xy), *a, **self._kw(k))

    def line(self, xy, *a, **k):
        return self._d.line(self._xy(xy), *a, **self._kw(k))

    def rectangle(self, xy, *a, **k):
        return self._d.rectangle(self._xy(xy), *a, **self._kw(k))

    def ellipse(self, xy, *a, **k):
        return self._d.ellipse(self._xy(xy), *a, **self._kw(k))

    def polygon(self, xy, *a, **k):
        return self._d.polygon(self._xy(xy), *a, **self._kw(k))

    def arc(self, xy, *a, **k):
        return self._d.arc(self._xy(xy), *a, **self._kw(k))

    def rounded_rectangle(self, xy, *a, **k):
        return self._d.rounded_rectangle(self._xy(xy), *a, **self._kw(k))

    # ---- 度量类：除回 1×
    def textlength(self, *a, **k):
        return self._d.textlength(*a, **k) / self._s

    def getlength(self, *a, **k):
        return self._d.getlength(*a, **k) / self._s

    def textbbox(self, *a, **k):
        b = self._d.textbbox(*a, **k)
        return tuple(v / self._s for v in b)

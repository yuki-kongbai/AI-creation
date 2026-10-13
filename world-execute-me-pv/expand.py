"""expand.py —— 单窗 → 双栏的展开。

几何（1280×720，四边留 24px，内容区 1232 宽）：
    起态  窗口 354 宽**居中**，还没有右栏
    终态  窗口 354 宽贴左（x=24），右栏 866 宽在右

为什么不「窗口从满宽缩到 354」：
    缩到极窄会看着像故障，不像展开。真实的分屏是 **窗口本来就窄、向左靠，
    右边让出位置长出第二栏** —— 这个动作观众一眼就懂。
    而且窗口宽度全程不变，就不必按变化宽度反复渲染浏览器（省掉一大堆边界情况）。

右栏用 clip 从左侧展开：看起来是从窗口边缘挤出来的。
镜头不动（你定的：窗口始终全长景），动的是版式本身。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(r"D:\大肥鱼（deepseek）\whale-pv2")))
import clock as C  # noqa: E402

CW, CH = 1280, 720
PAD = 24
TOP, BOT = 76, 649
FULL_W = CW - 2 * PAD               # 1232

WIN_W = 354                         # 全程不变
GAP = 12
RIGHT_W = FULL_W - WIN_W - GAP      # 866

X_LEFT = PAD                        # 终态：贴左
X_MID = PAD + (FULL_W - WIN_W) / 2  # 起态：居中 = 463


def ease_pop(u: float) -> float:
    """展开/收回用的缓动：**起步最快，然后减速**。

    为什么不用 smoothstep：
        它两端导数为零，运动最快的时候在**中间**。实测峰值出现在拍点之后
        203ms（2.208s vs 拍点 2.005s）—— 对观众就是"动作慢了半拍"。
        改成 ease-out 后，起步那一瞬位移最大，可见运动紧贴拍点。
    """
    u = C.clamp(u)
    return 1.0 - (1.0 - u) ** 2.4


# (时刻, 窗口x 的插值进度 0=居中 1=贴左, 右栏占比)
#
# 用**拍号构造**，不写十进制字面量：写 t=3.389 反推 beat 会差 0.0005 拍，
# 对位检查会报错。C.beat_t(n) 的值就是 FIRST_BEAT + n*BEAT，必然精确。
# 拍号来自 beat_table.py —— 改节奏只改那张表。
KEYS = [
    (C.beat_t( 0), 0.00, 0.00),   # beat  0  开场：只有一扇窗，居中
    (C.beat_t( 3), 0.00, 0.00),   # beat  3  停住，让观众看清这扇窗
    (C.beat_t( 4), 0.00, 0.00),   # beat  4  停住：下一步才是起步（不许预动）
    (C.beat_t( 8), 1.00, 1.00),   # beat  8  起步并定型：双栏（重音在 beat 4）
    (C.beat_t(48), 1.00, 1.00),   # beat 48  最后一条打完，停一拍让观众读完
    (C.beat_t(53), 1.00, 0.00),   # beat 53  右栏被吸回窗口（重音在 beat 48）
    (C.beat_t(54), 1.00, 0.00),   # beat 54  顿一下：她走了，只剩左边的窗
    (C.beat_t(59), 1.00, 0.00),   # beat 59  消息逐条褪完
    (C.beat_t(61), 0.00, 0.00),   # beat 61  窗口滑回中央（重音在 beat 59）
    (C.beat_t(66), 0.00, 0.00),   # beat 66  空窗，留白
]







def at(t: float) -> dict:
    if t <= KEYS[0][0]:
        _, kx, kr = KEYS[0]
        u = 0.0
    elif t >= KEYS[-1][0]:
        _, kx, kr = KEYS[-1]
        u = 1.0
    else:
        kx = kr = 0.0
        u = 0.0
        for i in range(len(KEYS) - 1):
            t0, x0, r0 = KEYS[i]
            t1, x1, r1 = KEYS[i + 1]
            if t0 <= t < t1:
                u = ease_pop((t - t0) / max(1e-6, t1 - t0))
                kx = x0 + (x1 - x0) * u
                kr = r0 + (r1 - r0) * u
                break

    x = X_MID + (X_LEFT - X_MID) * kx
    rw = RIGHT_W * kr
    return {"win_w": WIN_W, "win_x": x, "right_w": rw,
            "win_x2": x + WIN_W, "right_x": x + WIN_W + GAP,
            "u": u, "kx": kx, "kr": kr}


def duration() -> float:
    """整段（展开 + 稳定 + 收回）的时长。"""
    return KEYS[-1][0]


if __name__ == "__main__":
    print("  t     窗x    右栏宽   右栏x   进度")
    for t in (0, 1.4, 1.85, 2.45, 3.1, 3.7, 10, 20.4, 21.6, 22.6, 23.2,
              24.4, 26.0, 27.6):
        a = at(t)
        print(f"{t:5.2f} {a['win_x']:7.1f} {a['right_w']:8.1f} "
              f"{a['right_x']:8.1f}   {a['kr']:.2f}")


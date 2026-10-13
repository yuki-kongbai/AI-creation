#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测出我的 MP3 与仓库时刻骨架之间的**时间偏移**。

为什么必须测：
    仓库的对齐用了 sha256 = 79c4e536… 的音频，我的 MP3 是 8fe5a15c…
    —— 不是同一个文件。把它的时刻表直接套到我的文件上，就会整体偏，
    表现就是「声音已经过去了，词还在前面」。
    两个文件时长只差 0.19s，所以很可能只是编码不同、内容相同 ——
    但**必须验证**，不能假设。

做法：
    1. 把骨架的逐词时刻变成一条「人声活跃度」包络（唱词=1，间奏=0）
    2. 从我的 MP3 里提**人声频带**（300–3400Hz）的能量包络
    3. 两条包络做互相关，找最佳滞后
    4. 再用仓库给的行时刻做一次独立复核

人声频带而不是全带，是因为全带能量被鼓点主导 —— 这是我上一轮
用 flux 测起音失败的原因。
"""
from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PV2))
import audio  # noqa: E402

REPO = Path(r"D:\大肥鱼（deepseek）\.repo\world-execute-me-dsh-pv-main")
MP3 = Path(r"D:\kuakewangpan\工具\bupan\Mili-world.execute(me);.mp3")
SR = 22050
HOP = 256


def decode_mono(path: Path, sr: int = SR) -> np.ndarray:
    ff = audio.find_ffmpeg()
    raw = subprocess.run(
        [ff, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr),
         "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def vocal_env(x: np.ndarray, sr: int = SR, hop: int = HOP):
    """人声频带包络：300–3400Hz 的短时能量。

    用 FFT 后在频域取带，比时域滤波简单且够准。
    """
    win = 1024
    n = 1 + (len(x) - win) // hop
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    frames = x[idx] * np.hanning(win)[None, :]
    spec = np.abs(np.fft.rfft(frames, axis=1))
    freqs = np.fft.rfftfreq(win, 1 / sr)
    band = (freqs >= 300) & (freqs <= 3400)
    e = (spec[:, band] ** 2).sum(axis=1)
    e = np.sqrt(e)
    # 归一化 + 轻度平滑
    if e.max() > 0:
        e = e / e.max()
    k = np.ones(5) / 5
    e = np.convolve(e, k, mode="same")
    t = (np.arange(n) * hop + win / 2) / sr
    return t, e


def skel_env(words, dur: float, t: np.ndarray, sr: int = SR, hop: int = HOP):
    """骨架包络：某个词正在唱 = 1，否则 0（含半个词的羽化）。"""
    act = np.zeros_like(t)
    for w in words:
        a, b = w["start"], w["end"]
        act[(t >= a) & (t < b)] = 1.0
    return act


def xcorr_lag(a: np.ndarray, b: np.ndarray, hop: int, sr: int, max_lag: float):
    """互相关找滞后。正滞后 = b 需要往后挪才能对齐 a。"""
    a = a - a.mean()
    b = b - b.mean()
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    m = int(max_lag * sr / hop)
    lags = np.arange(-m, m + 1)
    scores = []
    for L in lags:
        if L >= 0:
            x, y = a[L:], b[:n - L] if L else b
        else:
            x, y = a[:n + L], b[-L:]
        if len(x) < 100:
            scores.append(-1e9)
            continue
        scores.append(float(np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-9)))
    scores = np.array(scores)
    k = int(np.argmax(scores))
    return lags[k] * hop / sr, lags * hop / sr, scores


def main():
    if not MP3.exists():
        print(f"找不到 {MP3}")
        return
    print(f"解码 {MP3.name} …")
    x = decode_mono(MP3)
    dur_mine = len(x) / SR
    print(f"  我的时长 {dur_mine:.3f}s")

    d = json.loads((REPO / "data" / "timing" / "word_timeline_notext.json")
                   .read_text(encoding="utf-8"))
    sk = d["skeleton"]
    words = sk["words"]
    print(f"  仓库时长 {sk['duration']:.3f}s   词数 {len(words)}")
    print(f"  仓库声明 global_offset = {sk['global_offset']}")

    t, e = vocal_env(x)
    act = skel_env(words, sk["duration"], t)

    # 两条包络都重采样到统一长度
    n = min(len(e), len(act))
    e, act, t = e[:n], act[:n], t[:n]
    print(f"  包络 {n} 帧（{t[-1]:.1f}s）")

    lag, lags, scores = xcorr_lag(e, act, HOP, SR, 4.0)
    best = scores.max()
    print(f"\n最佳滞后 {lag:+.3f}s   相关 {best:.4f}")

    # 看相关峰有多尖锐
    order = np.argsort(scores)[::-1][:5]
    print("  前 5 个峰：")
    for i in order:
        print(f"    {lags[i]:+.3f}s   {scores[i]:.4f}")

    # 分区间复核：如果只是整体平移，各段应该给出一致的滞后
    print("\n分段独立测（各段 40s）：")
    for t0 in (0, 40, 80, 120, 160):
        t1 = min(t0 + 40, t[-1])
        sel = (t >= t0) & (t < t1)
        if sel.sum() < 200:
            continue
        l2, lg2, sc2 = xcorr_lag(e[sel], act[sel], HOP, SR, 3.0)
        print(f"  {t0:>4}–{t1:>4}s   滞后 {l2:+.3f}s   相关 {sc2.max():.4f}")

    (HERE / "cache" / "offset.json").write_text(
        json.dumps({"lag": lag, "corr": float(best),
                    "mine_dur": dur_mine, "repo_dur": sk["duration"],
                    "hash_match": False}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"\n-> cache/offset.json   滞后 {lag:+.3f}s")


if __name__ == "__main__":
    main()

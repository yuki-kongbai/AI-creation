"""render_clip.py —— 把窗口渲染成一段可用的片子素材。

流程（每帧）：
    scene.state_at(t)  ->  window_html.build()  ->  浏览器截图  ->  PNG

两条工程约束：
  · 浏览器只开一次，所有帧共用同一个 page（开一次约 1.5 s，每帧都开会慢十倍）
  · 光标闪烁由帧号决定，不用 CSS 动画 —— 否则并行/重渲染时同一个 t 会出不同的帧
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FRAMES = OUT / "frames"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

W, H = 420, 680
SCALE = 2
FPS = 24


def caret_at(t: float) -> bool:
    """光标闪烁：0.9 s 一轮，前一半亮。由 t 决定，可复现。"""
    return (t % 0.9) < 0.45


def run_node(script: str) -> subprocess.CompletedProcess:
    p = OUT / "_job.cjs"
    p.write_text(script, encoding="utf-8")
    return subprocess.run(["node", str(p)], capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t0", type=float, default=0.0)
    ap.add_argument("--t1", type=float, default=None)
    ap.add_argument("--fps", type=int, default=FPS)
    ap.add_argument("--every", type=int, default=1, help="每 N 帧取一帧（预览用）")
    ap.add_argument("--prefix", default="w")
    a = ap.parse_args()

    import scene
    t1 = a.t1 if a.t1 is not None else scene.SCRIPT["duration"]
    FRAMES.mkdir(parents=True, exist_ok=True)

    idx = list(range(int(a.t0 * a.fps), int(t1 * a.fps), a.every))
    print(f"渲染 {a.t0:.1f} – {t1:.1f}s  {len(idx)} 帧 @ {a.fps}fps "
          f"({W}×{H} @{SCALE}x)")

    # 先算好每帧的 HTML，交给 node 批量截图
    import window_html
    pages = []
    for i in idx:
        t = i / a.fps
        html = window_html.build(t, caret_on=caret_at(t))
        name = f"{a.prefix}{i:05d}.png"
        pages.append({"html": html, "png": str((FRAMES / name))})

    # 分片交给 node（一次传太多会超命令行长度）
    CHUNK = 40
    t0 = time.time()
    done = 0
    for k in range(0, len(pages), CHUNK):
        part = pages[k:k + CHUNK]
        payload = json.dumps(part, ensure_ascii=False)
        js = f'''
const {{ chromium }} = require('playwright-core');
const fs = require('fs');
const items = JSON.parse(fs.readFileSync({json.dumps(str(OUT / '_part.json'))}, 'utf8'));
(async () => {{
  const b = await chromium.launch({{ executablePath: {json.dumps(EDGE)}, headless: true }});
  const p = await b.newPage({{ viewport: {{ width: {W}, height: {H} }},
                              deviceScaleFactor: {SCALE} }});
  await p.goto('about:blank');
  for (const it of items) {{
    await p.setContent(it.html, {{ waitUntil: 'load' }});
    await p.evaluate(() => document.fonts.ready);
    await p.screenshot({{ path: it.png }});
  }}
  await b.close();
}})().catch(e => {{ console.error(e.message); process.exit(1); }});
'''
        (OUT / "_part.json").write_text(payload, encoding="utf-8")
        r = run_node(js)
        if r.returncode != 0:
            print(f"  截图失败: {r.stderr.strip()[:400]}")
            sys.exit(1)
        done += len(part)
        el = time.time() - t0
        print(f"  {done}/{len(pages)}  {done/el:.1f} 帧/秒  "
              f"剩余 {max(0,(len(pages)-done))/max(0.1,done/el):.0f}s")

    print(f"\n完成 {done} 帧 -> {FRAMES}")
    print(f"用时 {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()

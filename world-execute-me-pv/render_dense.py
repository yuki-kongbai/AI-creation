"""render_dense.py —— 渲染高密度窗口。

用法：
    python render_dense.py                 # 全部
    python render_dense.py --every 6       # 抽帧预览
    python render_dense.py --t0 0 --t1 12
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

W, H, SCALE, FPS = 420, 680, 2, 24


def caret_at(t: float) -> bool:
    return (t % 0.9) < 0.45


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="content/scene02.json")
    ap.add_argument("--t0", type=float, default=0.0)
    ap.add_argument("--t1", type=float, default=None)
    ap.add_argument("--fps", type=int, default=FPS)
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--prefix", default="d")
    a = ap.parse_args()

    import dense_scene
    import dense_window

    scene = dense_scene.load(HERE / a.scene)
    t1 = a.t1 if a.t1 is not None else dense_scene.duration(scene)
    FRAMES.mkdir(parents=True, exist_ok=True)

    idx = list(range(int(a.t0 * a.fps), int(t1 * a.fps), a.every))
    print(f"渲染 {a.t0:.1f} – {t1:.1f}s  {len(idx)} 帧 @ {a.fps}fps  "
          f"({W}×{H} @{SCALE}x)")

    out_png = FRAMES
    # 清掉同名旧帧，避免拼片时混进上一版
    for p in out_png.glob(f"{a.prefix}*.png"):
        p.unlink()

    items = []
    for i in idx:
        t = i / a.fps
        st = dense_scene.state_at(scene, t)
        html = dense_window.build(scene, st, caret_on=caret_at(t))
        items.append({"html": html, "png": str(out_png / f"{a.prefix}{i:05d}.png")})

    CHUNK = 30
    t0 = time.time()
    done = 0
    for k in range(0, len(items), CHUNK):
        part = items[k:k + CHUNK]
        (OUT / "_part.json").write_text(json.dumps(part, ensure_ascii=False),
                                        encoding="utf-8")
        js = f'''
const {{ chromium }} = require('playwright-core');
const fs = require('fs');
const items = JSON.parse(fs.readFileSync({json.dumps(str(OUT / "_part.json"))}, 'utf8'));
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
        (OUT / "_job.cjs").write_text(js, encoding="utf-8")
        r = subprocess.run(["node", str(OUT / "_job.cjs")],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  截图失败: {r.stderr.strip()[:400]}")
            sys.exit(1)
        done += len(part)
        el = time.time() - t0
        print(f"  {done}/{len(items)}  {done/el:.1f} 帧/秒  "
              f"剩余 {max(0,(len(items)-done))/max(0.1,done/el):.0f}s")

    print(f"\n完成 {done} 帧 -> {FRAMES}   用时 {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()

"""compose.py —— 把聊天窗口与「她的内部」合成成 1280×720 的成片画面。

结构（定型）：
    单窗开场 → 逐渐展开成双栏
    窗口始终全长景，只在最后收回空窗口
    左栏「她在说话」（真浏览器渲染的 DSH 窗口）
    右栏「她的内部」（点阵 / 权重矩阵 / 她的轮廓 / token 流）

关键技术约束（踩过才定的）：
  · 窗口按**成片里的显示尺寸**渲染浏览器（354×573 CSS px），
    deviceScaleFactor=2 得 708×1146，再 LANCZOS 0.5 倍降采样。
    比例是 2 的倒数，不引入半像素模糊 —— 否则字会糊。
  · 窗口 CSS 宽度必须传进去（build(win_w=...)），否则内部仍按 420 排版会溢出。
  · 字体别用 .ttc：PIL 取不到子字体。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PV2 = Path(r"D:\大肥鱼（deepseek）\whale-pv2")
sys.path.insert(0, str(PV2))
sys.path.insert(0, str(HERE))

from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

import tk          # noqa: E402
import stage as S  # noqa: E402

OUT = HERE / "out"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

CW, CH = 1280, 720
PAD = 24
WIN_W, WIN_H = 354, 573
WIN_X, WIN_Y = PAD, 76
GAP = 12
RIGHT = (WIN_X + WIN_W + GAP, WIN_Y, CW - PAD, WIN_Y + WIN_H)
GRID = 17


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    p = "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"
    return ImageFont.truetype(p, size)


def cjk(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", size)
    except OSError:
        return font(size)


def shoot_window_batch(scene: dict, times: list[float], css_w: int, css_h: int,
                       out_dir: Path, scale: float = 1.0,
                       indices: list[int] | None = None) -> list[Path]:
    """批量渲染窗口帧。

    每帧启一次 node + Edge 要约 1.2 秒（实测 1.0 帧/秒），
    一次开浏览器连拍只要约 0.1 秒/帧。所以先把所有 t 的 HTML 算好，一次拍完。

    宽度必须按成片里的显示宽度传进去，否则内部按默认 420 排版、右边会被切。
    """
    import dense_scene
    import dense_window

    out_dir.mkdir(parents=True, exist_ok=True)
    items, paths = [], []
    for k, t in enumerate(times):
        # 分两段渲染时要用**绝对帧号**，否则两段都从 0 开始会互相覆盖
        i = indices[k] if indices else k
        st = dense_scene.state_at(scene, t)
        html = dense_window.build(scene, st, caret_on=(t % 0.9) < 0.45,
                                  win_w=css_w, win_h=css_h)
        hp = out_dir / f"p{i:05d}.html"
        hp.write_text(html, encoding="utf-8")
        raw = out_dir / f"raw{i:05d}.png"
        items.append({"html": str(hp), "png": str(raw)})
        paths.append(raw)

    (OUT / "_batch.json").write_text(json.dumps(items, ensure_ascii=False),
                                     encoding="utf-8")
    js = f'''
const {{ chromium }} = require('playwright-core');
const fs = require('fs');
const items = JSON.parse(fs.readFileSync({json.dumps(str(OUT / "_batch.json"))}, 'utf8'));
(async () => {{
  const b = await chromium.launch({{ executablePath: {json.dumps(EDGE)}, headless: true }});
  const p = await b.newPage({{ viewport: {{ width: {css_w}, height: {css_h} }},
                              deviceScaleFactor: {2 * scale} }});
  await p.goto('file:///' + {json.dumps(str(out_dir / "p00000.html").replace(chr(92), "/"))});
  for (const it of items) {{
    await p.setContent(fs.readFileSync(it.html, 'utf8'), {{ waitUntil: 'load' }});
    await p.evaluate(() => document.fonts.ready);
    await p.screenshot({{ path: it.png }});
  }}
  await b.close();
}})().catch(e => {{ console.error(e.message); process.exit(1); }});
'''
    (OUT / "_batch.cjs").write_text(js, encoding="utf-8")
    r = subprocess.run(["node", str(OUT / "_batch.cjs")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"批量截图失败: {r.stderr.strip()[:400]}")
    return paths


def shoot_window(scene: dict, t: float) -> Image.Image:
    """渲染单帧窗口并降采样到成片里的显示尺寸。"""
    raw = shoot_window_batch(scene, [t], WIN_W, WIN_H, OUT / "_one")[0]
    return Image.open(raw).convert("RGB").resize((WIN_W, WIN_H), Image.LANCZOS)


# ---------------------------------------------------------------- 右栏
def right_panel(t: float, feat, scene: dict) -> Image.Image:
    """右栏 = 她的内部。主形态由窗口当前在跑什么决定。"""
    import dense_scene
    import code_panel as rp

    st = dense_scene.state_at(scene, t)
    phase = "idle"
    it = st["turns"][-1] if st["turns"] else {}
    if it.get("tool_p", 0) > 0 and it.get("tool_n", 0) > 0:
        phase = "tool"
    elif it.get("code_p", 0) > 0 and it.get("code_n", 0) > 0:
        phase = "code"
    elif it.get("table_p", 0) > 0:
        phase = "table"
    elif st["thinking"]:
        phase = "think"

    # 把窗口里正在显示的内容传过去 —— 右栏显示的是同一件事的内侧
    extra = {"code_lines": [], "bars": []}
    for tn in scene["turns"]:
        if "code" in tn:
            extra["code_lines"] = tn["code"]["lines"]
        if "table" in tn:
            extra["bars"] = [(r[1][:6], 0.2 + 0.7 * v) for v, r in
                             zip((0.62, 0.74, 0.51, 0.83), tn["table"]["rows"])]

    cells, _rows = rp.panel_cells("maid-right", "full", 260)
    return rp.draw((RIGHT[2]-RIGHT[0], RIGHT[3]-RIGHT[1]), t, feat, phase, cells, extra)

# ---------------------------------------------------------------- 排版层
def chrome_layer(t: float, feat) -> Image.Image:
    img = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ui = tk.ui(1.0)

    d.text((PAD, 18), "WORLD.EXECUTE(ME);", font=font(15, True), fill=ui)
    d.text((PAD + 208, 20), "whale@deepsea:~$", font=font(13), fill=tk.ui(0.55))
    mid = f"step {int(t * 48):08d}    loss {0.52 + 0.2 * feat.loud:.4f}"
    d.text((PAD + 392, 20), mid, font=font(13), fill=tk.ui(0.7))
    right = f"02 / SING   00:{t:04.1f} / 03:32   RUNNING"
    d.text((CW - PAD - d.textlength(right, font=font(13)), 20), right,
           font=font(13), fill=tk.ui(0.85))
    d.line([PAD, 44, CW - PAD, 44], fill=tk.ui(0.35))

    fs = font(11)
    n = 52
    k = int(n * min(1.0, t / 212.0))
    d.text((PAD, CH - 24), "[" + "|" * k + ":" * (n - k) + "]",
           font=fs, fill=tk.ui(0.40))
    credit = "角色 溟月 © 上善无形 / 女仆版 ZipZipPipe / 立绘 dsh-deep-whale (CC BY-NC-SA 4.0)    Music: Mili - world.execute(me);   非官方同人"
    d.text((CW - PAD - d.textlength(credit, font=fs), CH - 24), credit,
           font=fs, fill=tk.ui(0.38))
    return img


def main():
    import dense_scene
    scene_path = HERE / "content" / (sys.argv[2] if len(sys.argv) > 2 else "scene04.json")
    scene = dense_scene.load(scene_path)
    t = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0

    sys.path.insert(0, str(PV2))
    import audio
    feat = audio.at(t)
    print(f"t={t:.1f}s  loud={feat.loud:.2f} kick={feat.kick:.2f} flux={feat.flux:.2f}")

    canvas = S.background(t).convert("RGB")
    win = shoot_window(scene, t)
    print(f"窗口 {win.size}")
    canvas.paste(win, (WIN_X, WIN_Y))
    canvas.paste(right_panel(t, feat, scene), (RIGHT[0], RIGHT[1]))
    canvas = Image.alpha_composite(canvas.convert("RGBA"),
                                   chrome_layer(t, feat)).convert("RGB")
    final = tk.post(canvas, None, trail=0.0, bloom=0.30)

    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / f"compose_{t:05.1f}.png"
    final.save(dst)
    print(f"-> {dst}  {final.size}")


if __name__ == "__main__":
    main()

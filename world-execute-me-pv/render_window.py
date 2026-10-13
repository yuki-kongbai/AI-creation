"""render_window.py —— 把一段对话渲染成一扇 DSH 风格的聊天窗口。

流水线：
    content/*.json  ->  HTML（用 DSH 的真实设计令牌）  ->  Edge 无头截图  ->  PNG

为什么要绕 HTML 一圈：界面质感来自「它是真的」。
`superellipse(1.5)` 的超椭圆圆角、字体的 subpixel 抗锯齿、行内代码的底色边界 ——
这些用 PIL 画永远差一截，用浏览器就是白送。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets" / "dsh"
TOKENS = json.loads((ASSETS / "tokens_dark.json").read_text(encoding="utf-8"))
OUT = HERE / "out"

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def tok(name: str, fallback: str) -> str:
    return TOKENS.get(f"--dsw-alias-{name}", fallback)


# 界面用到的令牌，全部取自真实的暗色主题（assets/dsh/tokens_dark.json）。
T = {
    "bg":            tok("bg-base", "#151517"),
    "bg_layer":      tok("bg-layer-1", "#232324"),
    "bg_raise":      tok("bg-layer-3", "#353638"),
    "fg":            tok("label-primary", "#f9fafb"),
    "fg2":           tok("label-secondary", "#cfd3d6"),
    "fg3":           tok("label-tertiary", "#adb2b8"),
    "caption":       tok("label-caption", "#81858c"),
    "dimmed":        tok("label-dimmed", "#43454a"),
    "link":          tok("link", "#7aaaff"),
    "brand":         tok("brand-primary-new-colorprimary-new-color", "#5686fe"),
    "ok":            tok("state-success-primary", "#22c55e"),
    "err":           tok("state-error-primary", "#f25a5a"),
    "warn":          tok("state-warn-primary", "#f59e0b"),
    "border1":       tok("border-l1", "#ffffff0f"),
    "border2":       tok("border-l2", "#ffffff1f"),
    "border4":       tok("border-l4", "#ffffff33"),
    "code_bg":       tok("markdown-code-block", "#1b1b1c"),
    "code_banner":   tok("markdown-code-block-banner", "#2c2c2e"),
    "inline_code":   tok("markdown-inline-code", "#292929"),
    "hover":         tok("interactive-bg-hover", "#ffffff14"),
    "radius_sm": "8px", "radius_md": "12px", "radius_lg": "16px",
}


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def inline_md(s: str) -> str:
    """极小的行内 markdown：**粗体**、`代码`。"""
    import re
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r'<b>\1</b>', s)
    s = re.sub(r"`([^`]+)`", r'<code class="ic">\1</code>', s)
    return s


def para(s: str) -> str:
    return "".join(f"<p>{inline_md(p)}</p>" for p in s.split("\n\n") if p.strip())


def hl_code(line: str, lang: str) -> str:
    """极小的语法高亮。不追求完整，只求「一眼像代码」。"""
    import re
    s = esc(line)
    if s.strip().startswith(("//", "#")):
        return f'<span class="c">{s}</span>'
    s = re.sub(r"(\d+\.?\d*)", r'<span class="n">\1</span>', s)
    s = re.sub(r"(&quot;[^&]*?&quot;|'[^']*?')", r'<span class="s">\1</span>', s)
    kw = ("const|let|var|function|return|if|else|for|while|int|print|def|and|or|not"
          if lang in ("javascript", "js") else
          "def|return|import|for|in|if|else|print|int|and|or|not")
    s = re.sub(rf"\b({kw})\b", r'<span class="k">\1</span>', s)
    s = re.sub(r"\b(const|let|var|function|return|if|else|for|while)\b", r'<span class="k">\1</span>', s)
    return s


def code_block(code: dict) -> str:
    lang, fname = code.get("lang", ""), code.get("file", "")
    lines = "\n".join(hl_code(l, lang) for l in code["lines"])
    return f'''<div class="cb">
  <div class="cb-bar"><span class="cb-lang">{esc(lang)}</span>
    <span class="cb-file">{esc(fname)}</span>
    <span class="cb-copy">copy</span></div>
  <pre><code>{lines}</code></pre>
</div>'''


def tool_block(t: dict) -> str:
    out = "\n".join(esc(l) for l in t["out"])
    return f'''<div class="tool">
  <div class="tool-bar"><span class="tool-dot"></span>
    <span class="tool-name">{esc(t["name"])}</span>
    <span class="tool-cmd">{esc(t["cmd"])}</span></div>
  <pre>{out}</pre>
</div>'''


def footer(f: dict) -> str:
    hit = f.get("cache_hit")
    parts = [
        f'<span>in <b>{f["tokens_in"]:,}</b></span>',
        f'<span>out <b>{f["tokens_out"]:,}</b></span>',
    ]
    if hit is not None:
        parts.append(f'<span>cache <b>{hit}%</b></span>')
    parts += [f'<span class="cost">¥{f["cost"]:.4f}</span>',
              f'<span class="ms">{f["ms"]:,} ms</span>']
    return f'<div class="foot">{"".join(parts)}</div>'


def msg_block(m: dict) -> str:
    role = m["role"]
    if role == "user":
        return f'''<div class="turn u">
  <div class="u-body">{inline_md(m["text"])}</div>
  <div class="u-time">{m["time"]}</div>
</div>'''
    cls = "a plain" if role == "assistant_plain" else "a"
    inner = []
    if m.get("thinking"):
        inner.append(f'<div class="think"><span class="think-tag">thinking</span>'
                     f'{inline_md(m["thinking"])}</div>')
    inner.append(f'<div class="a-body">{para(m["text"])}</div>')
    if m.get("code"):
        inner.append(code_block(m["code"]))
    if m.get("tool"):
        inner.append(tool_block(m["tool"]))
    if m.get("footer"):
        inner.append(footer(m["footer"]))
    return f'''<div class="turn {cls}">
  <div class="a-head"><span class="avatar"></span>
    <span class="a-name">DeepSeek</span><span class="a-time">{m["time"]}</span></div>
  {''.join(inner)}
</div>'''


def build_html(scene: dict, width: int = 400, height: int = 640) -> str:
    s = scene["session"]
    body = "".join(msg_block(m) for m in scene["messages"])
    c = scene["composer"]
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<style>
:root {{
  --bg:{T['bg']}; --layer:{T['bg_layer']}; --raise:{T['bg_raise']};
  --fg:{T['fg']}; --fg2:{T['fg2']}; --fg3:{T['fg3']};
  --cap:{T['caption']}; --dim:{T['dimmed']}; --link:{T['link']}; --brand:{T['brand']};
  --ok:{T['ok']}; --err:{T['err']}; --warn:{T['warn']};
  --b1:{T['border1']}; --b2:{T['border2']}; --b4:{T['border4']};
  --codebg:{T['code_bg']}; --codebar:{T['code_banner']}; --ic:{T['inline_code']};
  --hover:{T['hover']};
}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{width}px;height:{height}px;overflow:hidden}}
body{{
  background:var(--bg);color:var(--fg);
  font:400 14px/24px -apple-system,"Segoe UI","Microsoft YaHei",system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;
}}
.mono,pre,code,.cb,.tool{{font-family:"Cascadia Mono",Consolas,"Courier New",monospace}}

/* 顶部栏 */
.top{{
  height:44px;display:flex;align-items:center;gap:8px;padding:0 14px;
  border-bottom:1px solid var(--b1);background:var(--layer);
}}
.top .title{{font-size:13px;font-weight:600;color:var(--fg);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}}
.top .chip{{font-size:11px;color:var(--fg3);border:1px solid var(--b2);
  border-radius:6px;padding:1px 7px;white-space:nowrap}}
.top .turn{{font-size:11px;color:var(--cap);font-variant-numeric:tabular-nums}}

/* 消息区 */
.scroll{{height:calc(100% - 44px - 92px);padding:14px 16px;overflow:hidden}}

.turn{{margin-bottom:18px}}
.turn.u{{display:flex;flex-direction:column;align-items:flex-end}}
.u-body{{
  max-width:78%;background:var(--raise);border-radius:12px 12px 4px 12px;
  padding:8px 12px;color:var(--fg);line-height:22px;
}}
.u-time{{font-size:11px;color:var(--dim);margin-top:4px;font-variant-numeric:tabular-nums}}

.a-head{{display:flex;align-items:center;gap:7px;margin-bottom:6px}}
.avatar{{width:16px;height:16px;border-radius:5px;background:var(--brand);display:block}}
.a-name{{font-size:12px;font-weight:600;color:var(--fg2)}}
.a-time{{font-size:11px;color:var(--dim);font-variant-numeric:tabular-nums}}
.a-body p{{margin-bottom:8px;color:var(--fg)}}
.a-body p:last-child{{margin-bottom:0}}

/* 思维链 */
.think{{
  border-left:2px solid var(--b4);padding:2px 0 2px 10px;margin-bottom:10px;
  color:var(--fg3);font-size:13px;line-height:21px;opacity:.92;
}}
.think-tag{{
  display:inline-block;font-size:10px;letter-spacing:.06em;text-transform:uppercase;
  color:var(--cap);margin-right:6px;border:1px solid var(--b2);
  border-radius:4px;padding:0 5px;line-height:15px;vertical-align:1px;
}}

/* 代码块 */
.cb{{background:var(--codebg);border:1px solid var(--b2);border-radius:10px;
  overflow:hidden;margin:10px 0}}
.cb-bar{{display:flex;align-items:center;gap:8px;background:var(--codebar);
  padding:5px 10px;font-size:11px;color:var(--fg3);border-bottom:1px solid var(--b1)}}
.cb-lang{{color:var(--cap);text-transform:uppercase;letter-spacing:.05em}}
.cb-file{{color:var(--fg2);flex:1}}
.cb-copy{{color:var(--dim)}}
.cb pre{{padding:10px 12px;overflow:hidden}}
.cb code{{font-size:12px;line-height:19px;color:#d4d4d8;white-space:pre}}
.cb .c{{color:#6a737d;font-style:italic}}
.cb .k{{color:#c586c0}}
.cb .n{{color:#b5cea8}}
.cb .s{{color:#ce9178}}

/* 工具调用 */
.tool{{background:var(--codebg);border:1px solid var(--b2);border-radius:10px;
  overflow:hidden;margin:10px 0}}
.tool-bar{{display:flex;align-items:center;gap:7px;padding:6px 10px;
  background:var(--codebar);border-bottom:1px solid var(--b1);font-size:11px}}
.tool-dot{{width:6px;height:6px;border-radius:3px;background:var(--ok);display:block}}
.tool-name{{color:var(--fg2);font-weight:600}}
.tool-cmd{{color:var(--fg3);font-family:"Cascadia Mono",Consolas,monospace}}
.tool pre{{padding:9px 12px;font-size:11.5px;line-height:18px;color:var(--fg3);white-space:pre}}

/* 底部统计 */
.foot{{display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;padding-top:7px;
  border-top:1px solid var(--b1);font-size:11px;color:var(--cap);
  font-variant-numeric:tabular-nums}}
.foot b{{color:var(--fg3);font-weight:500}}
.foot .cost{{color:var(--warn)}}
.foot .ms{{color:var(--dim);margin-left:auto}}

/* 输入区 */
.composer{{
  height:92px;border-top:1px solid var(--b1);background:var(--layer);
  padding:10px 16px;display:flex;flex-direction:column;gap:6px;
}}
.box{{
  flex:1;border:1px solid var(--b2);border-radius:12px;background:var(--bg);
  padding:9px 12px;color:var(--dim);font-size:13px;display:flex;align-items:flex-start;
}}
.status{{display:flex;gap:10px;font-size:11px;color:var(--cap);align-items:center}}
.status .ok{{color:var(--ok)}}
.status .sep{{color:var(--b4)}}
</style></head><body>

<div class="top">
  <span class="title">{esc(s["title"])}</span>
  <span class="chip">{esc(s["model"])}</span>
  <span class="turn">turn {s["turn"]}</span>
</div>

<div class="scroll">{body}</div>

<div class="composer">
  <div class="box">{esc(c["placeholder"])}</div>
  <div class="status"><span class="ok">●</span><span>{esc(c["status"])}</span></div>
</div>

</body></html>'''


def shoot(html: str, png: Path, width: int, height: int, scale: int = 2) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / "_page.html"
    tmp.write_text(html, encoding="utf-8")
    script = OUT / "_shot.cjs"
    script.write_text(f'''
const {{ chromium }} = require('playwright-core');
(async () => {{
  const b = await chromium.launch({{ executablePath: {json.dumps(EDGE)}, headless: true }});
  const p = await b.newPage({{ viewport: {{ width: {width}, height: {height} }},
                              deviceScaleFactor: {scale} }});
  await p.goto('file:///' + {json.dumps(str(tmp).replace(chr(92), '/'))});
  await p.evaluate(() => document.fonts.ready);
  await p.screenshot({{ path: {json.dumps(str(png).replace(chr(92), '/'))} }});
  await b.close();
}})().catch(e => {{ console.error(e.message); process.exit(1); }});
''', encoding="utf-8")
    r = subprocess.run(["node", str(script)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"截图失败: {r.stderr.strip()}")


def main():
    scene_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "content" / "scene01.json"
    scene = json.loads(Path(scene_path).read_text(encoding="utf-8"))
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    h = int(sys.argv[3]) if len(sys.argv) > 3 else 640

    html = build_html(scene, w, h)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "window.html").write_text(html, encoding="utf-8")
    png = OUT / "window.png"
    shoot(html, png, w, h)
    print(f"窗口 -> {png}  ({w}×{h} @2x = {w*2}×{h*2})")


if __name__ == "__main__":
    main()

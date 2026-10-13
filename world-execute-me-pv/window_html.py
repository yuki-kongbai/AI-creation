"""window_html.py —— 把 state_at(t) 翻成一扇 DSH 风格的聊天窗口 HTML。

设计令牌全部取自 assets/dsh/tokens_dark.json（从本机 DSH 主题包里解出来的真值）。
不允许在这里写死颜色 —— 要改配色就改那个 json。
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import scene

HERE = Path(__file__).resolve().parent
TOKENS = json.loads((HERE / "assets/dsh/tokens_dark.json").read_text(encoding="utf-8"))

W, H = 420, 680          # CSS 像素；截图时 deviceScaleFactor=2
SIDEBAR = 132


def tk(name: str, fallback: str) -> str:
    return TOKENS.get(f"--dsw-alias-{name}", fallback)


C = {
    "bg":       tk("bg-base", "#151517"),
    "layer1":   tk("bg-layer-1", "#232324"),
    "layer2":   tk("bg-layer-2", "#2c2c2e"),
    "layer3":   tk("bg-layer-3", "#353638"),
    "fg":       tk("label-primary", "#f9fafb"),
    "fg2":      tk("label-secondary", "#cfd3d6"),
    "fg3":      tk("label-tertiary", "#adb2b8"),
    "cap":      tk("label-caption", "#81858c"),
    "dim":      tk("label-dimmed", "#43454a"),
    "link":     tk("link", "#7aaaff"),
    "brand":    tk("brand-primary-new-colorprimary-new-color", "#5686fe"),
    "ok":       tk("state-success-primary", "#22c55e"),
    "err":      tk("state-error-primary", "#f25a5a"),
    "warn":     tk("state-warn-primary", "#f59e0b"),
    "b1":       tk("border-l1", "#ffffff0f"),
    "b2":       tk("border-l2", "#ffffff1f"),
    "b4":       tk("border-l4", "#ffffff33"),
    "code":     tk("markdown-code-block", "#1b1b1c"),
    "codebar":  tk("markdown-code-block-banner", "#2c2c2e"),
    "icode":    tk("markdown-inline-code", "#292929"),
}


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def inline(s: str) -> str:
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r'<b>\1</b>', s)
    s = re.sub(r"`([^`]+)`", r'<code class="ic">\1</code>', s)
    return s


def body_html(text: str, streaming: bool) -> str:
    """段落 + 结尾光标。流式时最后一段挂光标。"""
    if not text:
        return ""
    parts = [p for p in text.split("\n\n") if p.strip()]
    out = []
    for i, p in enumerate(parts):
        last = (i == len(parts) - 1)
        cur = '<span class="caret"></span>' if (last and streaming) else ""
        out.append(f"<p>{inline(p)}{cur}</p>")
    return "".join(out)


KW_JS = r"\b(const|let|var|function|return|if|else|for|while|new)\b"
KW_PY = r"\b(def|return|import|for|in|if|else|print|lambda|with|as)\b"


def hl(line: str, lang: str) -> str:
    """单遍扫描的高亮器。

    不要用「多次正则替换」—— 先给数字套 <span class="n">，再给字符串套
    <span class="s"> 时，会把 span 属性里的引号也当成字符串定界符，
    渲染出 `RATE = "n">0.0031` 这种垃圾。
    正确做法是从左到右扫一遍，遇到注释/字符串就整段吃掉，绝不回头。
    """
    if not line.strip():
        return "&nbsp;"
    py = lang not in ("javascript", "js")
    com = "#" if py else "//"
    kws = (r"\b(def|return|import|for|in|if|else|elif|print|lambda|with|as|"
           r"int|str|float|True|False|None)\b" if py else
           r"\b(const|let|var|function|return|if|else|for|while|new|"
           r"true|false|null|undefined)\b")
    num = re.compile(r"\d[\d_,]*\.?\d*")

    out, i, n = [], 0, len(line)
    while i < n:
        # 注释：一直吃到行尾
        if line.startswith(com, i):
            out.append(f'<span class="c">{esc(line[i:])}</span>')
            break
        ch = line[i]
        # 字符串：处理 f"" / "" / ''
        if ch in "\"'":
            j = i + 1
            while j < n and line[j] != ch:
                if line[j] == "\\":
                    j += 1
                j += 1
            j = min(j + 1, n)
            out.append(f'<span class="s">{esc(line[i:j])}</span>')
            i = j
            continue
        # 关键字
        m = re.compile(kws).match(line, i)
        if m:
            out.append(f'<span class="k">{esc(m.group(0))}</span>')
            i = m.end()
            continue
        # 数字
        m = num.match(line, i)
        if m:
            out.append(f'<span class="n">{esc(m.group(0))}</span>')
            i = m.end()
            continue
        out.append(esc(ch))
        i += 1

    return "".join(out).replace("\n", "")


def code_block(lang: str, fname: str, lines, shown: int, p: float) -> str:
    if p <= 0.01:
        return ""
    rows = []
    for i, l in enumerate(lines):
        if i < shown:
            rows.append(hl(l, lang))
        elif i == shown:
            # 正在写的那一行：半个光标
            rows.append(hl(l, lang) + '<span class="caret"></span>')
            break
        else:
            break
    style = f"opacity:{p:.3f}"
    return f'''<div class="cb" style="{style}">
  <div class="cb-bar"><span class="cb-lang">{esc(lang)}</span>
    <span class="cb-file">{esc(fname)}</span>
    <span class="cb-copy">copy</span></div>
  <pre><code>{"".join(r + chr(10) for r in rows)}</code></pre>
</div>'''


def tool_block(tool: dict, shown: int, p: float) -> str:
    if p <= 0.01:
        return ""
    rows = []
    for i, l in enumerate(tool["lines"]):
        if i < shown:
            cls = ' class="rule"' if set(l) <= set("\u2500") else ""
            rows.append(f"<span{cls}>{esc(l)}</span>")
        elif i == shown:
            rows.append('<span class="caret"></span>')
            break
    style = f"opacity:{p:.3f}"
    return f'''<div class="tool" style="{style}">
  <div class="tool-bar"><span class="dot"></span>
    <span class="tname">{esc(tool["name"])}</span>
    <span class="tcmd">{esc(tool["cmd"])}</span></div>
  <pre>{"".join(r + chr(10) for r in rows)}</pre>
</div>'''


def ai_turn(tn: dict, item: dict, thinking_now: bool) -> str:
    style = f"opacity:{item['show']:.3f}"
    parts = [f'''<div class="a-head">
    <span class="avatar"></span><span class="aname">DeepSeek</span>
    <span class="atime">{item["time"]}</span></div>''']

    tp = item.get("think_p", 0)
    if tp > 0.01:
        live = ' live' if 0 < tp < 1 or thinking_now else ""
        parts.append(f'''<div class="think{live}" style="opacity:{tp:.3f}">
      <span class="ttag">thinking</span><span class="ttext">{esc(item["think"])}</span>
    </div>''')

    if item["text"]:
        end = item["n"] < len(tn.get("text", ""))
        parts.append(f'<div class="abody">{body_html(item["text"], end)}</div>')

    if "code" in tn:
        parts.append(code_block(tn["code"]["lang"], tn["code"]["file"],
                                tn["code"]["lines"], item["code_n"],
                                item.get("code_p", 0)))
    if "tool" in tn:
        parts.append(tool_block(tn["tool"], item["tool_n"], item.get("tool_p", 0)))

    return f'<div class="a" style="{style}">{"".join(parts)}</div>'


def build(t: float, caret_on: bool = True) -> str:
    st = scene.state_at(t)
    S = scene.SCRIPT
    sess = S["session"]

    # --- 侧栏：会话历史 + 账本
    hist = "".join(
        f'<div class="hrow{" on" if i == 0 else ""}">'
        f'<span class="ht">{esc(h[0])}</span><span class="hh">{h[1]}</span></div>'
        for i, h in enumerate(S["history"]))

    # --- 消息流
    blocks = []
    for tn, item in zip(S["turns"], st["turns"]):
        if item["role"] == "user":
            end = item["n"] < len(tn["text"])
            cur = '<span class="caret"></span>' if end else ""
            blocks.append(f'''<div class="u" style="opacity:{item["show"]:.3f}">
  <div class="ub">{inline(item["text"])}{cur}</div>
  <div class="ut">{item["time"]}</div></div>''')
        else:
            blocks.append(ai_turn(tn, item, st["thinking"]))

    # --- 状态栏
    if st["thinking"]:
        dot, txt = "warn", "思考中…"
    elif st["streaming"]:
        n = st["turns"][-1]["n"] if st["turns"] else 0
        dot, txt = "ok", f"生成中 · {n} 字"
    else:
        dot, txt = "idle", "空闲时段 · 单价 ×1"

    bal = st["balance"]
    cost = st["cost"]
    delta = f'<span class="delta">↓ {cost:.4f}</span>' if cost > 0 else ""

    # 滚动条：按「已读内容量」估一个近似进度（真实高度要跑 JS 才能量，
    # 而我们要的是观感，不是精确值）。比例落在 0.18–0.85 之间，
    # 太低会像空文档，太高会像卡住不动。
    filled = min(1.0, len(blocks) / 7.0)
    sbh = 22 + 46 * filled
    sbtop = (100 - sbh) * min(1.0, max(0.0, (len(blocks) - 3) / 6.0))

    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}px;height:{H}px;overflow:hidden}}
body{{background:{C['bg']};color:{C['fg']};
  font:400 13px/21px -apple-system,"Segoe UI","Microsoft YaHei",system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;display:flex}}
pre,code,.mono{{font-family:"Cascadia Mono",Consolas,"Courier New",monospace}}

/* ---------- 侧栏 ---------- */
.side{{width:{SIDEBAR}px;flex:0 0 {SIDEBAR}px;height:100%;background:{C['layer1']};
  border-right:1px solid {C['b1']};display:flex;flex-direction:column}}
.side-top{{padding:11px 12px 9px;border-bottom:1px solid {C['b1']}}}
.brand{{display:flex;align-items:center;gap:7px}}
.bmark{{width:15px;height:15px;border-radius:5px;background:{C['brand']};
  corner-shape:superellipse(1.5)}}
.bname{{font-size:12px;font-weight:600;color:{C['fg']};letter-spacing:.01em}}
.bnew{{margin-top:9px;height:26px;border:1px solid {C['b2']};border-radius:8px;
  display:flex;align-items:center;justify-content:center;gap:5px;
  font-size:11px;color:{C['fg3']};background:{C['layer2']};corner-shape:superellipse(1.6)}}
.hist{{flex:1;overflow:hidden;padding:6px 6px}}
.hgrp{{font-size:10px;color:{C['dim']};padding:7px 6px 4px;letter-spacing:.04em}}
.hrow{{display:flex;align-items:center;gap:5px;padding:5px 7px;border-radius:7px;
  corner-shape:superellipse(1.6);margin-bottom:1px}}
.hrow.on{{background:{C['layer3']}}}
.ht{{flex:1;font-size:11.5px;color:{C['fg3']};white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis}}
.hrow.on .ht{{color:{C['fg']}}}
.hh{{font-size:9.5px;color:{C['dim']};font-variant-numeric:tabular-nums}}
.side-bot{{border-top:1px solid {C['b1']};padding:9px 12px 11px}}
.balrow{{display:flex;align-items:baseline;gap:6px}}
.bal{{font-size:15px;font-weight:600;color:{C['warn']};
  font-variant-numeric:tabular-nums;letter-spacing:.01em}}
.delta{{font-size:10px;color:{C['err']};font-variant-numeric:tabular-nums}}
.balcap{{font-size:10px;color:{C['dim']};margin-top:2px}}

/* ---------- 主区 ---------- */
.main{{flex:1;display:flex;flex-direction:column;min-width:0}}
.top{{height:38px;flex:0 0 38px;display:flex;align-items:center;gap:7px;
  padding:0 13px;border-bottom:1px solid {C['b1']}}}
.title{{font-size:12.5px;font-weight:600;flex:1;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis}}
.chip{{font-size:10px;color:{C['fg3']};border:1px solid {C['b2']};border-radius:5px;
  padding:1px 6px;white-space:nowrap;corner-shape:superellipse(1.8)}}
.trn{{font-size:10px;color:{C['cap']};font-variant-numeric:tabular-nums}}

.scroll{{flex:1;overflow:hidden;padding:11px 13px 6px;position:relative;
  display:flex;flex-direction:column;justify-content:flex-end}}
/* 滚动区顶部的渐隐：告诉观众「上面还有」。真界面都有这一层。 */
.fade{{position:absolute;left:0;right:0;top:0;height:22px;pointer-events:none;
  background:linear-gradient(180deg,{C['bg']} 12%,transparent)}}
/* 滚动条：长度表示读到哪儿了 */
.sbar{{position:absolute;right:3px;top:26px;bottom:8px;width:3px;
  border-radius:2px;background:{C['b1']}}}
.sbar i{{position:absolute;left:0;width:3px;border-radius:2px;
  background:{C['b4']};display:block}}

/* 用户 */
.u{{display:flex;flex-direction:column;align-items:flex-end;margin:0 0 13px}}
.ub{{max-width:84%;background:{C['layer3']};border-radius:11px 11px 4px 11px;
  corner-shape:superellipse(1.5);padding:7px 11px;line-height:20px;font-size:13px}}
.ut{{font-size:10px;color:{C['dim']};margin-top:3px;
  font-variant-numeric:tabular-nums}}

/* AI */
.a{{margin:0 0 15px}}
.a-head{{display:flex;align-items:center;gap:6px;margin-bottom:6px}}
.avatar{{width:15px;height:15px;border-radius:5px;background:{C['brand']};
  corner-shape:superellipse(1.5)}}
.aname{{font-size:11.5px;font-weight:600;color:{C['fg2']}}}
.atime{{font-size:10px;color:{C['dim']};font-variant-numeric:tabular-nums}}
.abody p{{margin-bottom:7px;color:{C['fg']}}}
.abody p:last-child{{margin-bottom:0}}
.ic{{background:{C['icode']};border-radius:4px;padding:1px 5px;font-size:11.5px;
  color:{C['fg2']};font-family:"Cascadia Mono",Consolas,monospace}}

/* 思维链 */
.think{{border-left:2px solid {C['b4']};padding:1px 0 1px 9px;margin-bottom:9px;
  color:{C['fg3']};font-size:12px;line-height:19px}}
.think.live{{border-left-color:{C['warn']}}}
.ttag{{display:inline-block;font-size:9px;letter-spacing:.07em;text-transform:uppercase;
  color:{C['cap']};margin-right:6px;border:1px solid {C['b2']};border-radius:4px;
  padding:0 4px;line-height:14px;vertical-align:1px;
  corner-shape:superellipse(1.8)}}
.think.live .ttag{{color:{C['warn']};border-color:{C['warn']}}}

/* 代码块 */
.cb{{background:{C['code']};border:1px solid {C['b2']};border-radius:9px;
  overflow:hidden;margin:9px 0;corner-shape:superellipse(1.6)}}
.cb-bar{{display:flex;align-items:center;gap:7px;background:{C['codebar']};
  padding:4px 9px;font-size:10px;border-bottom:1px solid {C['b1']}}}
.cb-lang{{color:{C['cap']};text-transform:uppercase;letter-spacing:.05em}}
.cb-file{{color:{C['fg3']};flex:1;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis}}
.cb-copy{{color:{C['dim']}}}
.cb pre{{padding:9px 10px;overflow:hidden}}
.cb code{{font-size:11px;line-height:17.5px;color:#d4d4d8;white-space:pre;
  display:block}}
.cb .c{{color:#6a737d;font-style:italic}}
.cb .k{{color:#c586c0}}
.cb .n{{color:#b5cea8}}
.cb .s{{color:#ce9178}}

/* 工具调用 */
.tool{{background:{C['code']};border:1px solid {C['b2']};border-radius:9px;
  overflow:hidden;margin:9px 0;corner-shape:superellipse(1.6)}}
.tool-bar{{display:flex;align-items:center;gap:6px;padding:5px 9px;
  background:{C['codebar']};border-bottom:1px solid {C['b1']};font-size:10px}}
.dot{{width:5px;height:5px;border-radius:3px;background:{C['ok']};display:block}}
.tname{{color:{C['fg2']};font-weight:600}}
.tcmd{{color:{C['fg3']};font-family:"Cascadia Mono",Consolas,monospace}}
.tool pre{{padding:8px 9px;font-size:10px;line-height:16.5px;color:{C['fg3']};
  white-space:pre}}
.tool .rule{{color:{C['dim']}}}

/* 输入区 */
.composer{{flex:0 0 auto;border-top:1px solid {C['b1']};padding:9px 13px 11px;
  display:flex;flex-direction:column;gap:6px}}
.box{{border:1px solid {C['b2']};border-radius:11px;background:{C['layer1']};
  corner-shape:superellipse(1.6);padding:8px 11px;color:{C['dim']};font-size:12.5px;
  display:flex;align-items:center;justify-content:space-between}}
.box .send{{font-size:10px;color:{C['dim']};border:1px solid {C['b1']};
  border-radius:6px;padding:1px 7px;corner-shape:superellipse(1.8)}}
.status{{display:flex;align-items:center;gap:7px;font-size:10px;color:{C['cap']}}}
.sdot{{width:5px;height:5px;border-radius:3px;display:block;
  background:{C['ok'] if dot == "ok" else C['warn'] if dot == "warn" else C['dim']}}}
.status .cost{{margin-left:auto;color:{C['fg3']};
  font-variant-numeric:tabular-nums}}

/* 光标 */
.caret{{display:{'inline-block' if caret_on else 'none'};width:7px;height:13px;
  background:{C['fg']};vertical-align:-2px;margin-left:1px}}
</style></head><body>

<aside class="side">
  <div class="side-top">
    <div class="brand"><span class="bmark"></span><span class="bname">DeepSeek</span></div>
    <div class="bnew">＋ 新对话</div>
  </div>
  <div class="hist">
    <div class="hgrp">今天</div>
    {hist}
  </div>
  <div class="side-bot">
    <div class="balrow"><span class="bal">¥{bal:.4f}</span>{delta}</div>
    <div class="balcap">余额 · 高峰 ×2</div>
  </div>
</aside>

<main class="main">
  <div class="top">
    <span class="title">{esc(sess["title"])}</span>
    <span class="chip">{esc(sess["model"])}</span>
    <span class="trn">turn {sess["turn"]}</span>
  </div>
  <div class="scroll">
    <div class="fade"></div>
    <div class="sbar"><i style="top:{sbtop:.1f}%;height:{sbh:.1f}%"></i></div>
    {"".join(blocks)}
  </div>
  <div class="composer">
    <div class="box"><span>{esc(S["composer"]["placeholder"])}</span>
      <span class="send">⏎</span></div>
    <div class="status"><span class="sdot"></span><span>{txt}</span>
      <span class="cost">本轮 ¥{cost:.4f}</span></div>
  </div>
</main>

</body></html>'''

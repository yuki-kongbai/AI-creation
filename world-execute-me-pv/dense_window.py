"""dense_window.py —— 高密度版窗口。

相比 window_html.py 的三处结构性改动（都是为了信息密度）：
  1. 侧栏从「只有历史列表」变成「文件树 + 上下文配额条 + 统计」
  2. 新增 table 块（症状 → 根因 这种对应关系用表格，比散文密度高得多）
  3. 工具输出分风格：tree（目录树，带行数）/ log（日志，带状态标记）
  4. 高亮器补上 and/or/not 这类中缀关键字

时间轴仍是纯函数 state_at(t)，渲染仍走真浏览器截图。
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOKENS = json.loads((HERE / "assets/dsh/tokens_dark.json").read_text(encoding="utf-8"))


def tk(name, fb):
    return TOKENS.get(f"--dsw-alias-{name}", fb)


C = {
    "bg":      tk("bg-base", "#151517"),
    "l1":      tk("bg-layer-1", "#232324"),
    "l2":      tk("bg-layer-2", "#2c2c2e"),
    "l3":      tk("bg-layer-3", "#353638"),
    "fg":      tk("label-primary", "#f9fafb"),
    "fg2":     tk("label-secondary", "#cfd3d6"),
    "fg3":     tk("label-tertiary", "#adb2b8"),
    "cap":     tk("label-caption", "#81858c"),
    "dim":     tk("label-dimmed", "#43454a"),
    "link":    tk("link", "#7aaaff"),
    "brand":   tk("brand-primary-new-colorprimary-new-color", "#5686fe"),
    "ok":      tk("state-success-primary", "#22c55e"),
    "err":     tk("state-error-primary", "#f25a5a"),
    "warn":    tk("state-warn-primary", "#f59e0b"),
    "b1":      tk("border-l1", "#ffffff0f"),
    "b2":      tk("border-l2", "#ffffff1f"),
    "b4":      tk("border-l4", "#ffffff33"),
    "code":    tk("markdown-code-block", "#1b1b1c"),
    "cbar":    tk("markdown-code-block-banner", "#2c2c2e"),
    "icode":   tk("markdown-inline-code", "#292929"),
}

W, H = 420, 680          # 默认值；嵌片时由 build(win_w=...) 覆盖
SIDEBAR = 124            # 文件名要放得下；主区仍需 >=190px 卡片内宽


def esc(s):
    return html.escape(str(s), quote=False)


def inline(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", r'<code class="ic">\1</code>', s)
    # 流式打字时，闭合的 ** 还没出现，上面那条正则匹配不上，
    # 星号就会裸露在画面上（`**75 个 Python 文件，3`）。
    # 这里把落单的记号收掉 —— 它只是标记，不是内容。
    s = s.replace("**", "").replace("`", "")
    return s


# ---------------------------------------------------------------- 高亮
def hl(line: str, lang: str) -> str:
    if not line.strip():
        return "&nbsp;"
    py = lang not in ("javascript", "js")
    com = "#" if py else "//"
    kws = (r"\b(def|return|import|for|in|if|elif|else|print|lambda|with|as|"
           r"and|or|not|int|str|float|True|False|None|for|while)\b" if py else
           r"\b(const|let|var|function|return|if|else|for|while|new|true|false|null)\b")
    num = re.compile(r"\d[\d_,]*\.?\d*")
    out, i, n = [], 0, len(line)
    while i < n:
        if line.startswith(com, i):
            out.append(f'<span class="c">{esc(line[i:])}</span>')
            break
        ch = line[i]
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
        m = re.compile(kws).match(line, i)
        if m:
            out.append(f'<span class="k">{esc(m.group(0))}</span>')
            i = m.end()
            continue
        m = num.match(line, i)
        if m:
            out.append(f'<span class="n">{esc(m.group(0))}</span>')
            i = m.end()
            continue
        out.append(esc(ch))
        i += 1
    return "".join(out).replace("\n", "")


# ---------------------------------------------------------------- 块
def code_block(cb, shown, p):
    if p <= 0.01:
        return ""
    rows = []
    for i, l in enumerate(cb["lines"]):
        if i < shown:
            rows.append(hl(l, cb["lang"]))
        elif i == shown:
            rows.append(hl(l, cb["lang"]) + '<span class="caret"></span>')
            break
    return f'''<div class="cb" style="opacity:{p:.3f}">
  <div class="cb-bar"><span class="lang">{esc(cb["lang"])}</span>
    <span class="file">{esc(cb["file"])}</span><span class="cp">copy</span></div>
  <pre><code>{chr(10).join(rows)}</code></pre></div>'''


def tool_block(tl, shown, p):
    if p <= 0.01:
        return ""
    style = tl.get("style", "plain")
    rows = []
    for i, l in enumerate(tl["lines"]):
        if i < shown:
            cls = []
            if set(l) <= set("\u2500"):
                cls.append("rule")
            if style == "tree" and "\u2190" in l:
                cls.append("mark")
            if style == "log":
                if "do not match" in l or "\u62a4" in l and "\u52ab" in l:
                    cls.append("bad")
                if l.strip().startswith("\u2500"):
                    cls.append("rule")
                if "/" in l and "\u5e27" in l:
                    cls.append("bad")
            c = f' class="{" ".join(cls)}"' if cls else ""
            rows.append(f"<span{c}>{esc(l)}</span>")
        elif i == shown:
            rows.append('<span class="caret"></span>')
            break
    return f'''<div class="tool" style="opacity:{p:.3f}">
  <div class="tool-bar"><span class="dot"></span>
    <span class="tn">{esc(tl["name"])}</span>
    <span class="tc">{esc(tl["cmd"])}</span></div>
  <pre>{chr(10).join(rows)}</pre></div>'''


def table_block(tb, p):
    if p <= 0.01:
        return ""
    head = "".join(f"<th>{esc(h)}</th>" for h in tb["head"])
    body = ""
    for r in tb["rows"]:
        tds = "".join(f"<td>{inline(c)}</td>" for c in r)
        body += f"<tr>{tds}</tr>"
    return f'''<div class="tbl" style="opacity:{p:.3f}">
  <table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'''


# ---------------------------------------------------------------- 侧栏
def sidebar(sc):
    files = "".join(
        f'<div class="frow"><span class="fn">{esc(n)}</span>'
        f'<span class="fl">{esc(l)}</span></div>' for n, l in sc["files"])
    m = sc["meter"]
    pct = min(1.0, m["used"] / m["total"])
    stats = "".join(
        f'<div class="st"><span class="sk">{esc(k)}</span>'
        f'<span class="sv">{esc(v)}</span></div>' for k, v in sc["stats"])
    return f'''<aside class="side">
  <div class="side-top">
    <div class="brand"><span class="bmark"></span><span class="bn">DeepSeek</span></div>
    <div class="bnew">＋ 新对话</div>
  </div>
  <div class="sgroup">工作区</div>
  <div class="files">{files}</div>
  <div class="meter">
    <div class="mrow"><span>{esc(m["label"])}</span>
      <span class="mv">{m["used"]:,} / {m["total"]:,}</span></div>
    <div class="mbar"><i style="width:{pct*100:.1f}%"></i></div>
  </div>
  <div class="stats">{stats}</div>
</aside>'''


# ---------------------------------------------------------------- 页面



def tool_block(tl, shown, p):
    if p <= 0.01:
        return ""
    style = tl.get("style", "plain")
    rows = []
    for i, l in enumerate(tl["lines"]):
        if i < shown:
            cls = []
            if set(l) <= set("\u2500"):
                cls.append("rule")
            if style == "tree" and "\u2190" in l:
                cls.append("mark")
            if style == "log":
                if "do not match" in l or "\u62a4" in l and "\u52ab" in l:
                    cls.append("bad")
                if l.strip().startswith("\u2500"):
                    cls.append("rule")
                if "/" in l and "\u5e27" in l:
                    cls.append("bad")
            c = f' class="{" ".join(cls)}"' if cls else ""
            rows.append(f"<span{c}>{esc(l)}</span>")
        elif i == shown:
            rows.append('<span class="caret"></span>')
            break
    return f'''<div class="tool" style="opacity:{p:.3f}">
  <div class="tool-bar"><span class="dot"></span>
    <span class="tn">{esc(tl["name"])}</span>
    <span class="tc">{esc(tl["cmd"])}</span></div>
  <pre>{chr(10).join(rows)}</pre></div>'''


def table_block(tb, p):
    if p <= 0.01:
        return ""
    head = "".join(f"<th>{esc(h)}</th>" for h in tb["head"])
    body = ""
    for r in tb["rows"]:
        tds = "".join(f"<td>{inline(c)}</td>" for c in r)
        body += f"<tr>{tds}</tr>"
    return f'''<div class="tbl" style="opacity:{p:.3f}">
  <table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'''


# ---------------------------------------------------------------- 侧栏
def sidebar(sc):
    files = "".join(
        f'<div class="frow"><span class="fn">{esc(n)}</span>'
        f'<span class="fl">{esc(l)}</span></div>' for n, l in sc["files"])
    m = sc["meter"]
    pct = min(1.0, m["used"] / m["total"])
    stats = "".join(
        f'<div class="st"><span class="sk">{esc(k)}</span>'
        f'<span class="sv">{esc(v)}</span></div>' for k, v in sc["stats"])
    return f'''<aside class="side">
  <div class="side-top">
    <div class="brand"><span class="bmark"></span><span class="bn">DeepSeek</span></div>
    <div class="bnew">＋ 新对话</div>
  </div>
  <div class="sgroup">工作区</div>
  <div class="files">{files}</div>
  <div class="meter">
    <div class="mrow"><span>{esc(m["label"])}</span>
      <span class="mv">{m["used"]:,} / {m["total"]:,}</span></div>
    <div class="mbar"><i style="width:{pct*100:.1f}%"></i></div>
  </div>
  <div class="stats">{stats}</div>
</aside>'''


# ---------------------------------------------------------------- 页面
def css(w: int, h: int) -> str:
    return f'''
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{w}px;height:{h}px;overflow:hidden}}
body{{background:{C['bg']};color:{C['fg']};
  font:400 13px/21px -apple-system,"Segoe UI","Microsoft YaHei",system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;display:flex}}
pre,code{{font-family:"Cascadia Mono",Consolas,"Courier New",monospace}}

/* ---- 侧栏 ---- */
.side{{width:{SIDEBAR}px;flex:0 0 {SIDEBAR}px;background:{C['l1']};
  border-right:1px solid {C['b1']};display:flex;flex-direction:column;overflow:hidden}}
.side-top{{padding:9px 9px 7px;border-bottom:1px solid {C['b1']}}}
.brand{{display:flex;align-items:center;gap:6px}}
.bmark{{width:14px;height:14px;border-radius:4px;background:{C['brand']}}}
.bn{{font-size:12px;font-weight:600}}
.bnew{{margin-top:8px;height:25px;border:1px solid {C['b2']};border-radius:7px;
  display:flex;align-items:center;justify-content:center;font-size:11px;
  color:{C['fg3']};background:{C['l2']}}}
.sgroup{{font-size:9.5px;color:{C['dim']};padding:8px 11px 4px;letter-spacing:.05em}}
.files{{padding:0 4px;overflow:hidden}}
.frow{{display:flex;align-items:center;gap:3px;padding:2.5px 5px;border-radius:5px}}
.frow:nth-child(2){{background:{C['l3']}}}
.fn{{flex:1;font-size:10px;color:{C['fg3']};white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;font-family:"Cascadia Mono",Consolas,monospace}}
.frow:nth-child(2) .fn{{color:{C['fg']}}}
.fl{{font-size:9.5px;color:{C['dim']};font-variant-numeric:tabular-nums}}
.meter{{margin-top:auto;padding:8px 9px 5px;border-top:1px solid {C['b1']}}}
.mrow{{font-size:9.5px;color:{C['cap']};margin-bottom:4px}}
.mrow .mv{{display:block;margin-top:2px}}
.mv{{color:{C['fg3']};font-variant-numeric:tabular-nums}}
.mbar{{height:3px;border-radius:2px;background:{C['b2']};overflow:hidden}}
.mbar i{{display:block;height:3px;background:{C['warn']};border-radius:2px}}
.stats{{padding:2px 9px 8px}}
.st{{display:flex;justify-content:space-between;font-size:9.5px;
  color:{C['cap']};line-height:15px}}
.sv{{color:{C['fg3']};font-variant-numeric:tabular-nums}}

/* ---- 主区 ---- */
.main{{flex:1;display:flex;flex-direction:column;min-width:0}}
.top{{height:36px;flex:0 0 36px;display:flex;align-items:center;gap:6px;
  padding:0 12px;border-bottom:1px solid {C['b1']}}}
.title{{font-size:11.5px;font-weight:600;flex:1;min-width:0;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis}}
.chip{{font-size:9.5px;color:{C['fg3']};border:1px solid {C['b2']};border-radius:5px;
  padding:1px 5px;white-space:nowrap}}
.trn{{font-size:9.5px;color:{C['cap']};font-variant-numeric:tabular-nums}}
.scroll{{flex:1;overflow:hidden;padding:10px 12px 4px;position:relative;
  display:flex;flex-direction:column;justify-content:flex-end}}
.fade{{position:absolute;left:0;right:0;top:0;height:18px;pointer-events:none;
  background:linear-gradient(180deg,{C['bg']} 10%,transparent)}}
.sbar{{position:absolute;right:2px;top:20px;bottom:6px;width:3px;border-radius:2px;
  background:{C['b1']}}}
.sbar i{{position:absolute;left:0;width:3px;border-radius:2px;background:{C['b4']}}}

.u{{display:flex;flex-direction:column;align-items:flex-end;margin:0 0 11px}}
.ub{{max-width:86%;background:{C['l3']};border-radius:10px 10px 4px 10px;
  padding:6px 10px;line-height:19px;font-size:12.5px}}
.ut{{font-size:9.5px;color:{C['dim']};margin-top:2px;
  font-variant-numeric:tabular-nums}}

.a{{margin:0 0 13px}}
.a-head{{display:flex;align-items:center;gap:5px;margin-bottom:5px}}
.avatar{{width:14px;height:14px;border-radius:4px;background:{C['brand']}}}
.an{{font-size:11px;font-weight:600;color:{C['fg2']}}}
.at{{font-size:9.5px;color:{C['dim']};font-variant-numeric:tabular-nums}}
.ab p{{margin-bottom:6px;font-size:12.5px;line-height:20px}}
.ab p:last-child{{margin-bottom:0}}
.ic{{background:{C['icode']};border-radius:3px;padding:0 4px;font-size:11px;
  color:{C['fg2']};font-family:"Cascadia Mono",Consolas,monospace}}

.think{{border-left:2px solid {C['b4']};padding:0 0 0 8px;margin-bottom:8px;
  color:{C['fg3']};font-size:11.5px;line-height:18px}}
.think.live{{border-left-color:{C['warn']}}}
.tt{{display:inline-block;font-size:8.5px;letter-spacing:.06em;text-transform:uppercase;
  color:{C['cap']};margin-right:5px;border:1px solid {C['b2']};border-radius:3px;
  padding:0 4px;line-height:13px;vertical-align:1px}}
.think.live .tt{{color:{C['warn']};border-color:{C['warn']}}}

.cb{{background:{C['code']};border:1px solid {C['b2']};border-radius:8px;
  overflow:hidden;margin:8px 0}}
.cb-bar{{display:flex;align-items:center;gap:6px;background:{C['cbar']};
  padding:4px 8px;font-size:9.5px;border-bottom:1px solid {C['b1']}}}
.lang{{color:{C['cap']};text-transform:uppercase;letter-spacing:.05em}}
.file{{color:{C['fg3']};flex:1;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;font-family:"Cascadia Mono",Consolas,monospace}}
.cp{{color:{C['dim']}}}
.cb pre{{padding:8px 9px;overflow:hidden}}
.cb code{{font-size:9.6px;line-height:15.4px;color:#d4d4d8;white-space:pre;display:block}}
.cb .c{{color:#6a737d;font-style:italic}}
.cb .k{{color:#c586c0}}
.cb .n{{color:#b5cea8}}
.cb .s{{color:#ce9178}}

.tool{{background:{C['code']};border:1px solid {C['b2']};border-radius:8px;
  overflow:hidden;margin:8px 0}}
.tool-bar{{display:flex;align-items:center;gap:5px;padding:4px 8px;
  background:{C['cbar']};border-bottom:1px solid {C['b1']};font-size:9.5px}}
.dot{{width:5px;height:5px;border-radius:3px;background:{C['ok']};display:block}}
.tn{{color:{C['fg2']};font-weight:600}}
.tc{{color:{C['fg3']};font-family:"Cascadia Mono",Consolas,monospace}}
.tool pre{{padding:7px 8px;font-size:8.8px;line-height:14.4px;color:{C['fg3']};
  white-space:pre}}
.tool .rule{{color:{C['dim']}}}
.tool .mark{{color:{C['link']}}}
.tool .bad{{color:{C['err']}}}

.tbl{{margin:8px 0;border:1px solid {C['b2']};border-radius:8px;overflow:hidden}}
.tbl table{{width:100%;border-collapse:collapse;font-size:9.6px}}
.tbl th{{text-align:left;padding:5px 9px;background:{C['cbar']};
  color:{C['cap']};font-weight:500;font-size:9.5px;letter-spacing:.04em;
  border-bottom:1px solid {C['b1']}}}
.tbl td{{padding:5px 9px;color:{C['fg3']};border-bottom:1px solid {C['b1']};
  line-height:16px;vertical-align:top}}
.tbl tr:last-child td{{border-bottom:none}}
.tbl td:first-child{{color:{C['err']};font-family:"Cascadia Mono",Consolas,monospace;
  font-size:9px;white-space:nowrap}}
.tbl td:last-child{{color:{C['fg2']};white-space:normal}}
.tbl td:first-child{{vertical-align:top}}

.composer{{flex:0 0 auto;border-top:1px solid {C['b1']};padding:8px 12px 10px;
  display:flex;flex-direction:column;gap:5px}}
.box{{border:1px solid {C['b2']};border-radius:10px;background:{C['l1']};
  padding:7px 10px;color:{C['dim']};font-size:12px;display:flex;
  align-items:center;justify-content:space-between}}
.send{{font-size:9.5px;color:{C['dim']};border:1px solid {C['b1']};
  border-radius:5px;padding:0 6px}}
.status{{display:flex;align-items:center;gap:6px;font-size:9.5px;color:{C['cap']}}}
.sdot{{width:5px;height:5px;border-radius:3px;display:block}}
.cost{{margin-left:auto;color:{C['fg3']};font-variant-numeric:tabular-nums}}
.caret{{display:{{CARET}};width:7px;height:12px;background:{C['fg']};
  vertical-align:-2px;margin-left:1px}}
'''


def build(scene: dict, st: dict, caret_on: bool = True,
          win_w: int | None = None, win_h: int | None = None) -> str:
    _w = win_w or W
    _h = win_h or H
    sc = scene["session"]
    blocks = []
    for tn, item in zip(scene["turns"], st["turns"]):
        if item["role"] == "user":
            cur = '<span class="caret"></span>' if item["n"] < len(tn["text"]) else ""
            blocks.append(f'''<div class="u" style="opacity:{item["show"]:.3f}">
  <div class="ub">{inline(item["text"])}{cur}</div>
  <div class="ut">{item["time"]}</div></div>''')
            continue

        hd = "" if tn["role"] == "ai_cont" else f'''<div class="a-head">
    <span class="avatar"></span><span class="an">DeepSeek</span>
    <span class="at">{item["time"]}</span></div>'''
        inner = [hd]
        tp = item.get("think_p", 0)
        if tp > 0.01:
            live = " live" if st["thinking"] else ""
            inner.append(f'''<div class="think{live}" style="opacity:{tp:.3f}">
      <span class="tt">thinking</span>{esc(item["think"])}</div>''')
        if item["text"]:
            end = item["n"] < len(tn["text"])
            parts = [p for p in item["text"].split("\n\n") if p.strip()]
            ps = "".join(
                f'<p>{inline(p)}'
                + ('<span class="caret"></span>' if (k == len(parts) - 1 and end) else "")
                + "</p>" for k, p in enumerate(parts))
            inner.append(f'<div class="ab">{ps}</div>')
        if "code" in tn:
            inner.append(code_block(tn["code"], item["code_n"], item.get("code_p", 0)))
        if "tool" in tn:
            inner.append(tool_block(tn["tool"], item["tool_n"], item.get("tool_p", 0)))
        if "table" in tn:
            inner.append(table_block(tn["table"], item.get("table_p", 0)))
        blocks.append(f'<div class="a" style="opacity:{item["show"]:.3f}">'
                      f'{"".join(inner)}</div>')

    if st["thinking"]:
        dot, txt, col = C["warn"], "思考中…", C["warn"]
    elif st["streaming"]:
        dot, txt, col = C["ok"], f"生成中 · {st['turns'][-1]['n']} 字", C["ok"]
    else:
        dot, txt, col = C["dim"], "空闲时段 · 单价 ×1", C["dim"]

    filled = min(1.0, len(blocks) / 6.0)
    sbh = 22 + 46 * filled
    sbtop = (100 - sbh) * min(1.0, max(0.0, (len(blocks) - 2) / 5.0))

    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<style>{css(_w, _h).replace("{CARET}", "inline-block" if caret_on else "none")}</style>
</head><body>
{sidebar(scene["sidebar"])}
<main class="main">
  <div class="top"><span class="title">{esc(sc["title"])}</span>
    <span class="chip">{esc(sc["model"])}</span>
    <span class="trn">turn {sc["turn"]}</span></div>
  <div class="scroll">
    <div class="fade"></div>
    <div class="sbar"><i style="top:{sbtop:.1f}%;height:{sbh:.1f}%"></i></div>
    {"".join(blocks)}
  </div>
  <div class="composer">
    <div class="box"><span>{esc(scene["composer"]["placeholder"]) if not st.get("kbd") else ""}{"<span class='caret'></span>" if st.get("kbd") else ""}</span>
      {"" if st.get("kbd") else "<span class='send'>⏎</span>"}</div>
    <div class="status"><span class="sdot" style="background:{col}"></span>
      <span>{txt}</span>
      <span class="cost">本轮 ¥{st["cost"]:.4f}</span></div>
  </div>
</main></body></html>'''

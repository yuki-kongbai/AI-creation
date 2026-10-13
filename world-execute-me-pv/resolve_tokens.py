"""resolve_tokens.py —— 精确解出 DSH 暗色主题的设计令牌真值。

上一版失败的原因：同一令牌在文件里有两次赋值（亮/暗），我用「往前找 4000 字符里
有没有 dark」来判定属于哪套主题 —— 这个判据是错的，导致代码块背景取到了亮色值
（白色），渲染出来是一块白板。

正确做法：按赋值**在文件中的先后**配对。每套主题是一个连续的赋值块，
块内的选择器带 `[data-ds-dark-theme]`。所以：
  1. 扫出所有「选择器 { 声明 }」块
  2. 看块的选择器里有没有 dark
  3. 块内的 --dsw-* 归入对应主题
  4. 静态色板全局共享，单独收

输出：assets/dsh/tokens_dark.json（最终十六进制值）
"""
from __future__ import annotations

import json
import re
from pathlib import Path

D = Path(__file__).resolve().parent / "assets" / "dsh"
JS = D / "theme-client.js"
OUT = D / "tokens_dark.json"

# 静态色板
STATIC = re.compile(r"(--dsw-static-[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})")
# 选择器 + 声明块
BLOCK = re.compile(r"([^{}]{1,400}?)\{([^{}]{1,20000}?)\}", re.S)
DECL = re.compile(r"(--dsw-[a-z0-9-]+)\s*:\s*([^;]{1,120})")
VARREF = re.compile(r"var\(\s*(--dsw-[a-z0-9-]+)")


def main():
    js = JS.read_text(encoding="utf-8", errors="replace")

    static = dict(STATIC.findall(js))
    print(f"静态色板 {len(static)} 个")

    theme = {"light": {}, "dark": {}}
    for sel, body in BLOCK.findall(js):
        s = sel.strip().lower()
        # 只看真正的主题块，避免把组件样式误当主题
        is_dark = "dark-theme" in s or "data-ds-dark" in s
        is_light = (":root" in s or "data-ds-light" in s) and not is_dark
        if not (is_dark or is_light):
            continue
        which = "dark" if is_dark else "light"
        for k, v in DECL.findall(body):
            theme[which].setdefault(k, v.strip())

    print(f"亮色块 {len(theme['light'])} 个令牌 / 暗色块 {len(theme['dark'])} 个令牌")

    def resolve(table, key, depth=0):
        if depth > 8:
            return None
        v = table.get(key)
        if v is None:
            return static.get(key)
        m = VARREF.fullmatch(v.strip()) or VARREF.match(v.strip())
        if m:
            nxt = m[1]
            return resolve(table, nxt, depth + 1) or static.get(nxt)
        v = v.strip()
        if v.startswith("#"):
            return v
        h = re.search(r"#[0-9a-fA-F]{3,8}", v)
        return h.group(0) if h else v

    # 暗色为基，缺的用亮色补（有些令牌只定义一次，两套共用）
    dark = {}
    for k in set(theme["dark"]) | set(theme["light"]):
        val = resolve(theme["dark"], k)
        if val is None or not str(val).startswith("#"):
            val = resolve(theme["light"], k)
        if val is not None:
            dark[k] = val

    colors = {k: v for k, v in dark.items() if str(v).startswith("#")}
    print(f"\n解出 {len(colors)} 个颜色真值\n")

    print("=== 界面骨架色 ===")
    for k in ("--dsw-alias-bg-base", "--dsw-alias-bg-layer-1", "--dsw-alias-bg-layer-2",
              "--dsw-alias-bg-layer-3", "--dsw-alias-bg-module-platform",
              "--dsw-alias-label-primary", "--dsw-alias-label-secondary",
              "--dsw-alias-label-tertiary", "--dsw-alias-label-caption",
              "--dsw-alias-label-dimmed"):
        if k in colors:
            print(f"  {k:52s} {colors[k]}")

    print("\n=== 代码与 markdown ===")
    for k in sorted(colors):
        if "markdown" in k or "code" in k:
            print(f"  {k:52s} {colors[k]}")

    print("\n=== 语义色 ===")
    for k in sorted(colors):
        if "state" in k or "link" in k or "brand" in k:
            print(f"  {k:52s} {colors[k]}")

    print("\n=== 边框与交互 ===")
    for k in sorted(colors):
        if "border" in k or "interactive" in k:
            print(f"  {k:52s} {colors[k]}")

    OUT.write_text(json.dumps(colors, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()

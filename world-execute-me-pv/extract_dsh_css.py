#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 app.asar 里取出 DSH 前端资源。

原片左侧那扇窗口的质感，来自它用的是**真前端**：真的 CSS、真的类名。
这里把需要的那几份抽出来，放到 assets/dsh/ 下，供每帧截图时引用。

只取 CSS 与必要的字体声明，不取 JS —— 我们要的是"长什么样"，不是"能跑"。
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

ASAR = Path(r"D:\Programs\DeepSeek Harness\resources\app.asar")
OUT = Path(__file__).resolve().parent / "assets" / "dsh"

WANTED = [
    "dsh-web-frontend/dist/assets/index-BPHePDI_.css",
    "dsh-web-frontend/dist/assets/vendor-BNsW4eBh.css",
    "dsh-client-ui-primitives/lib/markdown/MarkdownText.module.css",
    "dsh-client-ui-primitives/lib/markdown/CodeBlock.module.css",
    "dsh-client-ui-primitives/lib/TerminalBlock.module.css",
    "dsh-client-ui-primitives/lib/StateDot.module.css",
]


def read_index(f):
    """读 asar 目录树。asar 格式：4×uint32 头 + JSON 目录 + 文件数据。"""
    f.seek(0)
    _, _, _, size = struct.unpack("<IIII", f.read(16))
    blob = f.read(size).decode("utf-8", "replace")
    start = blob.index("{")
    depth = 0
    for i in range(start, len(blob)):
        if blob[i] == "{":
            depth += 1
        elif blob[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(blob[start:i + 1]), 16 + size
    raise ValueError("asar 头解析失败")


def walk(node, path=""):
    for name, v in node.get("files", {}).items():
        if "files" in v:
            yield from walk(v, path + "/" + name)
        else:
            yield path + "/" + name, v


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    f = open(ASAR, "rb")
    tree, base = read_index(f)
    entries = dict(walk(tree))

    got = []
    for want in WANTED:
        hit = None
        for path, meta in entries.items():
            if path.endswith("/" + want.split("/")[-1]) and want.split("/")[-2] in path:
                hit = (path, meta)
                break
        if not hit:
            print(f"  ✗ 没找到 {want}")
            continue
        path, meta = hit
        f.seek(base + int(meta["offset"]))
        data = f.read(int(meta["size"]))
        dest = OUT / Path(want).name
        dest.write_bytes(data)
        got.append((dest.name, len(data)))
        print(f"  ✓ {dest.name:32s} {len(data):8,d} B   <- {path}")

    # 附一份说明，讲清这些文件的来路与授权
    (OUT / "SOURCE.md").write_text(
        "# 这些文件的来源\n\n"
        f"从本机安装的 DeepSeek Harness 里抽出：\n\n```\n{ASAR}\n```\n\n"
        "只取 CSS（界面长什么样），不含任何 JS 逻辑、不含源码。\n"
        "用途：PV 里那扇聊天窗口按这些真实样式渲染，所以它看起来是真的界面而不是仿的。\n\n"
        "**这些样式属于 DeepSeek Harness，不是本项目的代码。**"
        "若本 PV 要公开发布，请先确认这样使用的授权；否则改用等效的自写样式。\n\n"
        "## 文件\n\n" + "".join(f"- `{n}` ({s:,} B)\n" for n, s in got),
        encoding="utf-8")

    print(f"\n共 {len(got)} 份 -> {OUT}")
    print(f"总 {sum(s for _, s in got):,} B")


if __name__ == "__main__":
    main()

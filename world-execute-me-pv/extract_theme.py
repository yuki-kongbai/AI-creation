#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""取出 DSH 主题包，解析设计令牌的真值。

CSS 里只有 `var(--dsw-alias-label-primary)` 这样的引用，值在主题包里。
拿到真值才能让 PV 里的界面用**正确的颜色**，而不是我猜的。
"""
from __future__ import annotations

import json
import re
import struct
from pathlib import Path

ASAR = Path(r"D:\Programs\DeepSeek Harness\resources\app.asar")
OUT = Path(__file__).resolve().parent / "assets" / "dsh"
TARGET = "dsh-client-ui-theme/lib/client.js"


def read_index(f):
    f.seek(0)
    _, _, _, size = struct.unpack("<IIII", f.read(16))
    blob = f.read(size).decode("utf-8", "replace")
    s = blob.index("{")
    depth = 0
    for i in range(s, len(blob)):
        if blob[i] == "{":
            depth += 1
        elif blob[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(blob[s:i + 1]), 16 + size
    raise ValueError("asar 头解析失败")


def walk(node, path=""):
    for name, v in node.get("files", {}).items():
        if "files" in v:
            yield from walk(v, path + "/" + name)
        else:
            yield path + "/" + name, v


def main():
    f = open(ASAR, "rb")
    tree, base = read_index(f)
    entries = dict(walk(tree))
    path = next((p for p in entries if p.endswith(TARGET)), None)
    if not path:
        print("没找到主题包")
        return
    meta = entries[path]
    f.seek(base + int(meta["offset"]))
    js = f.read(int(meta["size"])).decode("utf-8", "replace")
    (OUT / "theme-client.js").write_text(js, encoding="utf-8")
    print(f"✓ theme-client.js  {len(js):,} B")

    # 找令牌定义：--dsw-xxx: 值
    pairs = re.findall(r"(--dsw-[a-z0-9-]+)\s*:\s*([^;\"'`}]{1,60})", js)
    seen = {}
    for k, v in pairs:
        v = v.strip()
        if k not in seen:
            seen[k] = v
    print(f"\n从主题包里解析出 {len(seen)} 个令牌真值：\n")

    groups = {}
    for k, v in sorted(seen.items()):
        parts = k.split("-")
        g = "-".join(parts[2:4]) if len(parts) > 4 else "-".join(parts[2:])
        groups.setdefault(g, []).append((k, v))

    for g in sorted(groups):
        print(f"[--dsw-{g}-*]")
        for k, v in groups[g][:12]:
            print(f"    {k:52s} {v}")
        if len(groups[g]) > 12:
            print(f"    … 还有 {len(groups[g]) - 12} 个")
        print()

    (OUT / "tokens.json").write_text(json.dumps(seen, indent=1, ensure_ascii=False),
                                     encoding="utf-8")
    print(f"完整令牌表 -> assets/dsh/tokens.json")


if __name__ == "__main__":
    main()

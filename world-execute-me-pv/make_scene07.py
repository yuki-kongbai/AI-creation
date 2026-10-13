#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成 scene07.json —— 展开 + 稳定 + 收回的完整剧本。

和 scene05/06 的区别：时间轴是**连续**的，0–24 秒一路走完，
这样"展开段"和"收回段"可以用同一根时间轴渲染，不必做时间映射。

   0.3–6.7    展开期的内容（打字→思考→回答→工具→代码）
   8.2–16.4   稳定期（第二轮问答 + 表格）
  19.2–23.6   收尾（谢谢 → 最后一句 → 逐条褪去）
"""
import json
from pathlib import Path

D = Path(r"D:\大肥鱼（deepseek）\pvw")
src = json.loads((D / "content" / "scene06.json").read_text(encoding="utf-8"))

# 第三、四轮往前挪，让表格在稳定期里就写完（不要拖到收回才开始）
retime = {
    3: dict(at=8.20),                                   # 用户「它哪里出错了」
    4: dict(at=9.00, think_at=9.06, text_at=9.30, tool_at=10.30),
    5: dict(at=13.40, think_at=13.46, text_at=13.64, table_at=14.60),
}
for idx, p in retime.items():
    tn = src["turns"][idx]
    for k, v in p.items():
        if k == "tool_at":
            tn["tool"]["at"] = v
        elif k == "table_at":
            tn["table"]["at"] = v
        else:
            tn[k] = v

src["_note"] = "展开+稳定+收回的完整剧本，时间轴连续。收回段由 _clear 驱动。"
src["_clear"] = {"at": 19.90, "hold": 2.40}

out = D / "content" / "scene07.json"
out.write_text(json.dumps(src, ensure_ascii=False, indent=1), encoding="utf-8")

print(f"-> {out}")
for i, tn in enumerate(src["turns"]):
    keys = {k: tn[k] for k in ("at", "think_at", "text_at") if k in tn}
    for k in ("tool", "code", "table"):
        if k in tn:
            keys[k] = tn[k]["at"]
    print(f"  {i} {tn['role']:<10} {keys}")
print(f"  _clear {src['_clear']}")

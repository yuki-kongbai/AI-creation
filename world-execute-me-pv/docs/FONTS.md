# 字体

画面里的字全部由 Python（Pillow）渲染，用的是 **Windows 自带的字体**。
这些字体**不可再分发**，所以本仓库不含任何字体文件。

| 变量 | 默认（Windows 自带，不在仓库里） | 用途 | 没有时的替代建议 |
|---|---|---|---|
| （等宽正文） | `C:/Windows/Fonts/consola.ttf` | 代码栏、状态行、歌词英文 | Cascadia Mono、JetBrains Mono |
| （等宽粗体） | `C:/Windows/Fonts/consolab.ttf` | 标题、大字 | 同上的 Bold |
| （中文） | `C:/Windows/Fonts/msyh.ttc` | 中文歌词、思考过程 | Noto Sans SC、Source Han Sans SC |
| （符号） | `C:/Windows/Fonts/seguisym.ttf` | ♂ ♀ 等符号 | Noto Sans Math、DejaVu Sans |
| （粗黑） | `C:/Windows/Fonts/ariblk.ttf` | S / M 字母 | Arial Black、Anton |

字体路径**写死在几个模块的字体助手里**（`res.px()` 负责按分辨率放大字号）：

- `render_final.py` 的 `font()` / `cjk()`
- `panels.py`、`think_panel.py`、`code_panel.py` 的 `_mono()` / `_cjk()`
- `shapes3.py` 的 `SYM_FONTS` 与字母字体列表

换字体：改上面这些地方的路径即可。
**换了字体，字宽不同，部分排版会轻微错位**（代码栏的行宽和行号列是按 Consolas 的字宽算的）。

## 左窗里的字

左窗是真实 DSH 前端在 Chromium 里渲染的，用系统界面字体。
原片在 Windows 上渲染，中文是微软雅黑。

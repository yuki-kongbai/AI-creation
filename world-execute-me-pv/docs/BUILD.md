# 构建

## 0. 环境

```bash
pip install -r requirements.txt
# 需要一个 Chromium 内核的浏览器。本机 Edge 即可，不用下载：
#   C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe
```

`requirements.txt` 里 `playwright-core` 是给 Node 用的（渲染左窗），
Python 侧只需要 Pillow 和 numpy。

## 1. 放好输入

```
input/song.mp3          # 自备音频
input/lyrics_en.txt     # 英文歌词，一行一句
input/lyrics_zh.json    # 中文对照，129 行
```

歌词的文件格式见 `input/README.md`。

## 2. 合成时间表

```bash
python build.py lyrics
```

把 `data/lyrics_timed_notext.json`（不含文字的时刻）和你的歌词合起来，
产出 `cache/lyrics_timed.json`。

## 3. 渲染

```bash
python build.py render
```

约 5088 帧，2560×1440，本机（无 GPU 加速）约 25 分钟。
中途可以中断，帧是逐张写盘的；重跑时 `--reuse-win` 会复用已渲好的窗口帧。

**左窗会分两段渲染**：133.5s 之前是完整对话，之后是一个只有两句的新场景
（历史被删掉的那一刻）。这是设计，不是 bug。

## 4. 编码

```bash
python build.py encode
```

产出 `out/world_execute_me_final.mp4`。

## 参数

```bash
PVW_SCALE=1 python build.py render     # 出 1280×720 而不是 2560×1440
```

`PVW_SCALE` 默认 2。所有几何和字号都会按它缩放。
**注意**：`1` 和 `2` 之间切换要清掉 `out/_win_final/` 的窗口帧缓存，
否则尺寸不符。

## 踩过的坑（省得你再踩）

1. **坐标被缩放两次** —— `res.SDraw` 按 1× 设计坐标工作。
   从 `img.size` / `CW` 拿到的是输出像素，交进去会被再乘一次 `S`。
   内存条、footer、署名都因此溢出过画面。
2. **`f.getlength()` 也要除回 1×** —— 字体已经是 `S` 倍大，
   返回的宽度也是 `S` 倍，再被 `SDraw` 乘一次就成了 `S²`，
   代码栏的字距会翻倍。
3. **`range()` / `Image.new()` 收到浮点会炸** —— 整除结果要 `int()`。
4. **扁平形状不要按包围盒归一化** —— `gone`（一条平线）会被纵向拉满，
   变成一条大正弦波。要按设计框等比缩放。
5. **字形的点不能连线** —— ♂♀ / S / M / EXECUTION 的点是从笔画边缘随机采样的，
   点序没有几何意义，一连就是乱麻。见 `field.NO_LINK`。
6. **别用 PowerShell 传含引号的多行 Python** —— 这一路被坑了十几次。
   写文件再执行。

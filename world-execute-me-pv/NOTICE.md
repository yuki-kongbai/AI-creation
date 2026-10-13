# NOTICE：第三方素材与许可

本仓库的代码按 [LICENSE](LICENSE)（MIT）发布。
下面这些**不属于**那份许可，各自保留原来的许可和权利。

## 鲸鱼娘立绘及其派生画面（CC BY-NC-SA 4.0）

- **文件**：本仓库**不包含**立绘原图。构建时从 https://github.com/dsh-deep-whale
  获取 `maid-atelier/assets/maid-right-v7.webp` 等。
- **由这些图生成的画面**：`data/her_points.npy`、`data/her_segid.npy`
  （她的轮廓点云），以及成片里所有她的形象和从轮廓派生的形状。
- **署名链**（按 CC BY-NC-SA 4.0 保留完整创作链）：
  1. 角色原作：溟月 © 上善无形
  2. 女仆版设计：ZipZipPipe
  3. 立绘：Small-tailqwq / dsh-deep-whale
- **本项目的改动**：裁切、轮廓跟踪、按弧长重采样成 1400 个点、点云连线、
  沿歌词逐点变形。
- **含义**：
  - 使用、改编时保留上面的署名链；
  - **不得商用**；
  - 改编作品按同一许可分享。
- 许可全文：[LICENSES/CC-BY-NC-SA-4.0.txt](LICENSES/CC-BY-NC-SA-4.0.txt)

## dsh 前端文件（MIT，Copyright (c) 2026 DeepSeek）

- **文件**：`assets/dsh/` —— 从 `@deepseek-ai/dsh-client-ui-*` 各包里取出的
  CSS、主题 JS 和解析出的设计 token。
- 这些文件按各包的 MIT 许可分发。
- MIT 不包括商标：DeepSeek 的名称和标识归其权利人所有。

## 字体（SIL Open Font License 1.1 / 系统字体）

- 代码用到 Windows 自带的 **Consolas、微软雅黑、Segoe UI Symbol、Arial Black**。
- 这些字体**不在本仓库里**，也不可再分发。见 [docs/FONTS.md](docs/FONTS.md)。
- 本仓库**没有**收录任何字体文件。

## 不在本仓库里的

| 东西 | 权利人 | 怎么获得 |
|---|---|---|
| 歌曲 world.execute(me); | Mili | 自备，放到 `input/song.mp3` |
| 歌词原文 | 词作者（Mili） | 自备，放到 `input/lyrics_en.txt` 和 `input/lyrics_zh.json` |
| 成片 | 本项目 | 构建产物，见 README 的成片链接 |
| 鲸鱼娘立绘原图 | 见上方署名链 | 从 dsh-deep-whale 获取 |

音乐按 [Mili 官方使用指引](https://projectmili.com/copyright-guidelines)处理：
个人非商业二创可按指引使用；**含 AI 的同人内容须明确标注**。
本仓库不授予音乐或歌词的再许可。

## 上游数据

`data/lyrics_timed_notext.json` 的时间来自
[world-execute-me-dsh-pv](https://github.com/MisakaZentai/world-execute-me-dsh-pv)
的逐词对齐（MIT，Copyright (c) 2026 MisakaZentai），
本项目只保存**不含文字**的时刻，并用词长签名重新对齐到本项目的行。

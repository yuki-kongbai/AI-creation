# 素材来源

| 素材 | 来源 | 许可 |
|---|---|---|
| 鲸鱼娘立绘 | https://github.com/dsh-deep-whale 的 `maid-atelier/assets/maid-right-v7.webp` | CC BY-NC-SA 4.0 |
| dsh 前端 CSS / 主题 | `@deepseek-ai/dsh-client-ui-*` 各包（从本机 `app.asar` 取出） | MIT © 2026 DeepSeek |
| 逐词时间 | https://github.com/MisakaZentai/world-execute-me-dsh-pv 的 `data/timing/` | MIT © 2026 MisakaZentai |
| 歌曲 | Mili - world.execute(me);（用户自备） | 版权保留 |
| 歌词原文 | 用户自备 | 版权保留 |

## 关于逐词时间的一个发现

上游那个文件里 `audio_sha256` 是 `79c4e536…`，本机音频是 `8fe5a15c…` —— 不是同一个文件。
但用**人声频带包络互相关**测出偏移只有 **+0.023s**，
分段复核（40–80s / 80–120s / 160–200s）也都给 +0.023s。
所以是同一个演奏的不同编码，时间可以直接用。

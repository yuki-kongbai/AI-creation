# input/ —— 你要自备的东西

这个目录里的东西**都不进仓库**（`.gitignore` 排除），因为它们的权利不属于本项目。

| 文件 | 是什么 | 上哪弄 |
|---|---|---|
| `song.mp3` | Mili - world.execute(me); 的音频 | 自购 / 自备。不要提交 |
| `lyrics_en.txt` | 英文歌词，一行一句 | 自备。仓库只存时间，不存歌词正文 |
| `lyrics_zh.json` | 中文对照，129 行，按行号 | 自备 |

## 为什么歌词也不进仓库

歌词的文字版权属于词作者。本仓库只保存**每行的起止时间**（`data/lyrics_timed_notext.json`，
不含任何文字），构建时用 `tools/build_lyrics.py` 把它和你本机的歌词合起来。

这和原仓库 `world-execute-me-dsh-pv` 的 `lyrics_synced_notext.json` 是同一个思路。

## 时间表是怎么来的

`data/lyrics_timed_notext.json` 是用**词长签名**对齐出来的：把每一行的每个词的
字符长度当作指纹，去匹配上游给的逐词时间。129 行里 122 行逐词长度完全吻合。

详见 `docs/HOW_IT_WORKS.md`。

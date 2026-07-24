# TTS Golden Evaluation

本项目把朗读优化控制在可回归、可试听的轻量规则内，暂不引入多角色模型。

## 黄金数据

- `samples/sentence_splitter_golden/cases.json`：句子边界唯一事实源。
- `samples/tts_golden/cases.json`：试听文本、自动音色、语速、rate 和 pitch 唯一事实源。
- `samples/tts_golden/*.txt`：按场景浏览文本的辅助文件，不参与自动断言。

任何切句、音色选择或韵律规则变更，都应先修改黄金期望并说明原因，再运行测试。

## 生成试听

仅校验夹具和当前规则，不联网、不写文件：

```powershell
cd D:\Projects\listen_book
.venv\Scripts\python.exe scripts\generate_tts_golden.py --dry-run
```

生成全部真实 Edge TTS 样本：

```powershell
.venv\Scripts\python.exe scripts\generate_tts_golden.py --force
```

只重建指定样例：

```powershell
.venv\Scripts\python.exe scripts\generate_tts_golden.py `
  --case zh-dialogue-soft `
  --case en-dialogue-soft `
  --force
```

输出目录为 `storage/audio/tts_golden/<suite_version>/`：

- `<case-id>.mp3`：确定命名的试听音频。
- `report.json`：模型规则版本、音色、韵律参数、文件大小和 SHA-256。
- `index.html`：可直接打开的桌面/移动端试听索引。

MP3 由外部 Edge TTS 服务生成，字节哈希可能随服务端变化；黄金测试固定的是输入、音色和本地推导参数。

## 评分记录

每项按 1-5 分记录，3 分表示可接受，低于 3 分必须备注具体时间点和问题。

| 样例 | 自然度 | 断句 | 对白感 | 速度 | 奇怪停顿 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| zh-dialogue-plain |  |  |  |  |  |  |
| zh-dialogue-question |  |  |  |  |  |  |
| zh-dialogue-soft |  |  |  |  |  |  |
| zh-dialogue-strong |  |  |  |  |  |  |
| zh-narration-long |  |  |  |  |  |  |
| zh-narration-ellipsis |  |  |  |  |  |  |
| en-narration |  |  |  |  |  |  |
| en-dialogue-question |  |  |  |  |  |  |
| en-dialogue-soft |  |  |  |  |  |  |
| en-dialogue-strong |  |  |  |  |  |  |
| mixed-narration |  |  |  |  |  |  |

评分口径：

- 自然度：是否像稳定的真人朗读，而不是机械地忽快忽慢。
- 断句：句子边界和停顿是否符合文本。
- 对白感：对白与旁白是否有轻微区分，但不过度夸张。
- 速度：是否过快或过慢，长句是否有足够缓冲。
- 奇怪停顿：缩写、引号、省略号和破折号附近是否出现异常停顿。

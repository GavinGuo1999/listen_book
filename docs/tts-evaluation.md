# TTS Golden Evaluation

本项目先把朗读优化控制在“可评测的自然朗读”，暂不追求复杂多角色模型。

固定样例位于 `samples/tts_golden/`：

- `chinese_dialogue.txt`
- `chinese_narration.txt`
- `english_narration.txt`
- `mixed_symbols.txt`

每次调整 `backend/app/services/tts.py` 或切句规则后，抽样生成音频并按 1-5 分记录：

| 样例 | 自然度 | 断句 | 对白感 | 速度 | 奇怪停顿 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| chinese_dialogue |  |  |  |  |  |  |
| chinese_narration |  |  |  |  |  |  |
| english_narration |  |  |  |  |  |  |
| mixed_symbols |  |  |  |  |  |  |

评分口径：

- 自然度：是否像稳定的真人朗读，而不是机械地忽快忽慢。
- 断句：句子边界和停顿是否符合文本。
- 对白感：对白是否与旁白有轻微区分，但不过度夸张。
- 速度：是否过快、过慢，长句是否有足够缓冲。
- 奇怪停顿：是否在缩写、引号、省略号、破折号附近出现明显异常。

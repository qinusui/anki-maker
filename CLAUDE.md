
---

## Anki 卡片生成器 — 完整方案（DeepSeek 版）

### 一、整体架构

```
视频文件 + 字幕文件(.srt)
        ↓
  [1] 字幕解析 & AI处理（DeepSeek API）
        ↓ 翻译、注释、合并破碎句
  [2] ffmpeg 批量处理
        ↓ 按时间轴切音频 + 截截图
  [3] 打包 .apkg（SQLite + zip）
        ↓
  导入 Anki
```

---

### 二、技术选型

| 模块 | 工具 | 说明 |
|------|------|------|
| 字幕解析 | `pysrt` / 手写 parser | 读取 .srt 时间轴和文本 |
| AI 处理 | DeepSeek API（兼容 OpenAI 格式） | 翻译、注释、合并破碎句 |
| 音频切割 | `ffmpeg`（subprocess） | 按时间码精确切割，输出 mp3 |
| 视频截图 | `ffmpeg` | 取每句对话中间帧截图 |
| Anki 打包 | `genanki` 库 | 生成标准 .apkg 文件 |
| 可选前端 | Gradio 或 Streamlit | 做成 Web UI，不想用命令行时用 |

---

### 三、目录结构

```
anki_maker/
├── main.py
├── parse_srt.py
├── ai_process.py
├── media_cut.py
├── pack_apkg.py
├── input/
│   ├── video.mp4
│   └── subtitle.srt
└── output/
    ├── audio/
    ├── screenshots/
    └── deck.apkg
```

---

### 四、各模块实现思路

#### 1. 字幕解析（parse_srt.py）

同前，解析 `.srt` 得到每条的开始时间、结束时间（转成秒）、文本，注意把同一条字幕的多行文本拼成一句。

---

#### 2. AI 批量处理（ai_process.py）

用 `openai` 库对接 DeepSeek，改两个参数即可：

```python
from openai import OpenAI
import json

client = OpenAI(
    api_key="你的 DeepSeek API Key",
    base_url="https://api.deepseek.com",
)

def process_batch(batch: list[dict]) -> list[dict]:
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": (
                    "你是语言学习助手。对输入的字幕列表，每条返回："
                    "translation（中文翻译）、notes（1-3个重点词汇及释义）、"
                    "skip（句子过短/无意义则为true）。只返回 JSON，不要其他内容。"
                )
            },
            {
                "role": "user",
                "content": json.dumps(batch, ensure_ascii=False)
            }
        ],
        response_format={"type": "json_object"},  # 强制 JSON 输出
        temperature=0.2,
    )
    return json.loads(response.choices[0].message.content)
```

每批 30 条，用 `asyncio` 并发跑多批，速度快、成本极低（100 条不到 1 分钱）。

---

#### 3. ffmpeg 处理（media_cut.py）

**切音频：**

```bash
ffmpeg -i video.mp4 \
  -ss 83.456 -to 85.789 \
  -vn -acodec mp3 -q:a 2 \
  output/audio/card_001.mp3
```

`-ss` 放在 `-i` 之后保证精准，`-vn` 只取音频轨。

**截图**（取中间帧）：

```bash
ffmpeg -i video.mp4 \
  -ss 84.6 \
  -vframes 1 -q:v 2 \
  output/screenshots/card_001.jpg
```

`84.6 = (83.456 + 85.789) / 2`，中间帧画面最稳定。

用 `ThreadPoolExecutor` 8 条并发，100 条字幕约 10~20 秒处理完。

---

#### 4. 打包 .apkg（pack_apkg.py）

同前，用 `genanki`：

```python
import genanki

model = genanki.Model(
    model_id=固定随机整数,
    name='电影字幕卡',
    fields=[
        {'name': 'Screenshot'},
        {'name': 'Audio'},
        {'name': 'Sentence'},
        {'name': 'Translation'},
        {'name': 'Notes'},
    ],
    templates=[{
        'name': 'Card 1',
        'qfmt': '{{Screenshot}}<br>{{Audio}}',
        'afmt': '{{FrontSide}}<hr>{{Sentence}}<br>{{Translation}}<br>{{Notes}}',
    }]
)

note = genanki.Note(
    model=model,
    fields=[
        '<img src="card_001.jpg">',
        '[sound:card_001.mp3]',
        'Hello, how are you?',
        '你好，你还好吗？',
        'how are you: 常见问候语',
    ]
)
```

---

### 五、卡片正背面设计

**正面：** 截图 + 音频（不显示文字，考察听力）

**背面：**
```
[正面内容]
───────────
Hello, how are you?
你好，你还好吗？

📌 how are you — 常见问候语
```

---

### 六、可选功能扩展

**Whisper 自动转录**（没有字幕时）：用 `whisper` 库转录，`word_timestamps=True` 做到词级精度，直接替代 .srt。

**Gradio Web UI**：上传视频+字幕 → 预览字幕表格 → 勾选句子 → 导出，30 行代码搞定。

**人声分离**：`demucs` 库分离背景音乐，让音频更干净。

---

### 七、依赖安装

```bash
pip install openai genanki pysrt
# ffmpeg 系统级安装
# Windows: scoop install ffmpeg
# Mac:     brew install ffmpeg
# Linux:   apt install ffmpeg
```

---

### 八、执行流程

```
1. 解析 .srt → 字幕列表
2. 过滤过短句子（< 1秒）
3. 分批调用 DeepSeek API → 翻译 + 注释
4. 过滤 skip: true 的句子
5. 并行 ffmpeg → 切音频 + 截图
6. genanki 打包 → deck.apkg
7. 打印完成报告
```

---

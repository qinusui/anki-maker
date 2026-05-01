# Anki 卡片生成器

将视频 + 字幕文件自动转换为可导入 Anki 的牌组。

## 功能

- 解析 `.srt` 字幕文件，提取时间轴和文本
- 调用 DeepSeek API 批量翻译并生成词汇注释
- 使用 ffmpeg 按时间轴切割音频片段
- 自动截取每句对话的中间帧作为截图
- 生成标准 `.apkg` 文件，可直接导入 Anki

## 目录结构

```
anki_maker/
├── main.py           # 主程序入口
├── parse_srt.py      # 字幕解析
├── ai_process.py     # AI 批量处理
├── media_cut.py      # ffmpeg 媒体切割
├── pack_apkg.py      # Anki 打包
├── requirements.txt   # 依赖
├── input/            # 放置视频和字幕文件
└── output/           # 生成的牌组输出
```

## 安装依赖

```bash
pip install openai genanki pysrt
```

需要提前安装 ffmpeg（添加到 PATH）。

## 配置

复制 `.env.example` 为 `.env`，填入你的 API Key：
```bash
cp .env.example .env
```

编辑 `.env` 文件：
```
DEEPSEEK_API_KEY=your-api-key-here
```

## 使用方法

### 命令行

```bash
python main.py <视频文件> <字幕文件> [输出目录]
```

示例：
```bash
python main.py input/video.mp4 input/subtitle.srt output
```

## 流程

```
视频 + 字幕
    ↓
1. 解析字幕 → 字幕列表（开始/结束时间 + 文本）
    ↓
2. DeepSeek API → 翻译 + 词汇注释
    ↓
3. ffmpeg → 切音频 + 截中间帧
    ↓
4. genanki → 打包 .apkg
    ↓
导入 Anki 使用
```

## 卡片格式

- **正面**：截图 + 音频（考察听力）
- **背面**：原文 + 中文翻译 + 词汇注释

## 示例输出

```
[正面]
┌──────────┐
│  截图    │
└──────────┘
🔊 [音频]

[背面]
─────────────
Hello, how are you?
你好，你还好吗？

📌 how are you — 常见问候语
```

## 依赖

- Python 3.8+
- ffmpeg（系统级安装）
- DeepSeek API Key
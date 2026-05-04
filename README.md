<p align="center">
  <img src="docs/logo.svg" width="120" />
</p>

<h1 align="center">ClipLingo</h1>

将视频 + 字幕文件自动转换为可导入 Anki 的牌组。

**定位：辅助学习英语的软件** — 无需 AI 即可使用基础功能，配置 AI 后可智能筛选有学习价值的句子。

## 功能

### 基础功能（无需 AI）

- 解析 `.srt` 字幕文件，提取时间轴和文本
- **字幕生成方案链**：自动检测内嵌软字幕 → Whisper 转录
- 使用 ffmpeg 按时间轴切割音频片段（可自定义头尾 padding）
- 自动截取每句对话的中间帧作为截图
- 生成标准 `.apkg` 文件，可直接导入 Anki

### AI 进阶功能（可选）

- **AI 智能筛选**：自动筛选有学习价值的句子，过滤无意义对话（如 ok, yeah, uh-huh 等）
- **AI 翻译注释**：调用 AI API（DeepSeek / OpenAI / Ollama 等兼容接口）批量翻译并生成词汇注释
- **Web 配置持久化**：API 地址、模型名称、Key 自动保存到浏览器

## 目录结构

```
ClipLingo/
├── core/                # 核心处理模块
│   ├── __init__.py
│   ├── parse_srt.py     # 字幕解析
│   ├── ai_process.py    # AI 批量处理
│   ├── media_cut.py     # ffmpeg 媒体切割
│   ├── pack_apkg.py     # Anki 打包
│   └── whisper_transcribe.py  # Whisper 自动转录
├── backend/             # FastAPI 后端（Web 界面）
│   ├── main.py          # 后端入口
│   ├── api/             # API 路由
│   │   ├── subtitles.py # 字幕 / AI推荐 / 转录
│   │   ├── process.py   # 处理流程
│   │   └── cards.py     # 卡片管理
│   ├── models/          # 数据模型（Pydantic）
│   └── output/          # 生成的牌组输出
├── frontend/            # React 前端（Web 界面）
│   └── src/
│       ├── components/  # UI 组件
│       ├── services/    # API 调用
│       └── App.tsx      # 主应用
├── scripts/             # 启动脚本
│   ├── start-all.py     # 一键启动脚本
│   ├── start.bat        # Windows 启动脚本
│   └── start.sh         # Linux/Mac 启动脚本
├── docs/                # 文档
├── main.py              # CLI 主程序入口
├── Dockerfile           # Docker 构建配置
├── docker-compose.yml   # Docker 运行配置
├── requirements.txt     # Python 依赖
└── README.md
```

## 快速开始（Docker）

**一键启动，无需安装任何依赖：**

```bash
# 克隆项目
git clone https://github.com/qinusui/ClipLingo.git
cd ClipLingo

# 启动服务
docker-compose up -d

# 打开浏览器访问
# http://localhost:8000
```

**停止服务：**

```bash
docker-compose down
```

> 需要先安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)

---

## 手动安装

### Web 界面

**后端依赖：**

```bash
pip install -r requirements.txt
cd backend
pip install -r requirements.txt
```

**前端依赖：**

```bash
cd frontend
npm install
```

**系统依赖：**

- ffmpeg（添加到 PATH）
- Node.js 18+（用于前端开发）

### 命令行

```bash
pip install -r requirements.txt
```

需要提前安装 ffmpeg（添加到 PATH）。

## 配置

### AI 配置（可选）

如需使用 AI 翻译和智能筛选功能：

**Web 界面：** 在右侧「AI 配置」栏填写，自动保存到浏览器：

- **API 地址**：支持 OpenAI 兼容接口（DeepSeek / OpenAI / Ollama 等）
- **模型名称**：自定义模型
- **API Key**：自动持久化到 localStorage
- **测试连接** / **获取模型列表**：一键验证配置

> **隐私安全**：API Key 仅存储在浏览器本地（localStorage），不会上传到任何服务器，仅在本机与 localhost 后端通信时使用。电脑共用时注意清理浏览器数据。

**命令行：** 复制 `.env.example` 为 `.env`，填入你的 API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```
DEEPSEEK_API_KEY=your-api-key-here
```

### 字幕处理配置

左侧「字幕处理配置」栏可调整：

- **最短时长**：过滤过短的字幕（默认 1.0 秒）
- **开头提前**：音频切割时的头部 padding（默认 200ms）
- **结尾延后**：音频切割时的尾部 padding（默认 200ms）

## 使用方法

### Web 界面（推荐）

**一键启动（最简单）：**

Windows:

```bash
scripts\start.bat
```

或使用 Python 脚本：

```bash
python scripts/start-all.py
```

Linux/Mac:

```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

启动后会自动打开浏览器，访问 `http://localhost:5173`

---

**手动启动：**

**1. 启动后端服务：**

Windows:

```bash
.\scripts\start-backend.bat
```

或手动启动：

```bash
cd backend
pip install -r requirements.txt
python main.py
```

后端将在 `http://localhost:8000` 启动，API 文档：`http://localhost:8000/docs`

**2. 启动前端界面：**

需要先安装 [Node.js](https://nodejs.org/)，然后：

```bash
cd frontend
npm install
npm run dev
```

前端将在 `http://localhost:5173` 启动

**3. 使用 Web 界面：**

界面采用三步纵向布局，视线和操作直线向下：

1. **准备素材**：上传视频和字幕文件，调整字幕处理配置
2. **筛选内容**：手动勾选字幕，或使用「AI 推荐」智能筛选（需配置 AI）
3. **生成卡片**：点击「开始处理」生成并下载 Anki 牌组

**两种使用模式：**

- **基础模式**（无需 AI）：上传文件 → 手动勾选字幕 → 生成卡片（卡片包含原文、音频、截图）
- **AI 模式**（可选）：配置 AI → 使用「AI 推荐」筛选 → 生成卡片（额外包含翻译和注释）

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
Video file
    ↓
┌─ Subtitle Source (auto fallback) ──────┐
│ 1. Extract soft subtitle (ffmpeg, <1s) │
│ 2. Whisper transcription (fallback)    │
└────────────────────────────────────────┘
    ↓
1. Parse subtitles → list (start/end time + text)
    ↓
2. [Optional] AI → filter + translate + annotate
    ↓
3. ffmpeg → cut audio + extract frame
    ↓
4. genanki → pack .apkg
    ↓
Import to Anki
```

## 卡片格式

**基础模式（无 AI）：**

- **正面**：截图 + 音频（考察听力）
- **背面**：原文

**AI 模式（可选）：**

- **正面**：截图 + 音频（考察听力）
- **背面**：原文 + 中文翻译 + 词汇注释

## 示例输出

```
[Front]
┌───────────┐
│ Screenshot│
└───────────┘
🔊 [Audio]

[Back]
─────────────
Hello, how are you?
你好，你还好吗？

📌 how are you — 常见问候语
```

## 依赖

- Python 3.10+
- ffmpeg（系统级安装，需在 PATH 中）
- Node.js 18+（前端开发）
- AI API Key（可选，DeepSeek / OpenAI / Ollama 等兼容接口）

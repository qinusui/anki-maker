<p align="center">
  <img src="docs/logo.svg" width="120" />
</p>

<h1 align="center">ClipLingo</h1>

将视频 + 字幕文件自动转换为可导入 Anki 的牌组。

**定位：辅助学习英语的软件** — 无需 AI 即可使用基础功能，配置 AI 后可智能筛选有学习价值的句子。

## 下载与安装

**安装版（推荐）：**

- `ClipLingo_Setup.exe` — 主程序安装包（~230MB）
- `ClipLingo_Whisper_Setup.exe` — Whisper 转录插件安装包，可选（~53MB）

安装后启动 `ClipLingo.exe`，浏览器访问 `http://localhost:8000`。转录插件需安装到同一目录。

**免安装版：**

- `ClipLingo_portable.zip` — 完整版，内置 Whisper（~700MB）

解压后运行 `ClipLingo.exe`，浏览器访问 `http://localhost:8000`。

**Docker：**

```bash
git clone https://github.com/qinusui/ClipLingo.git
cd ClipLingo
docker-compose up -d
# 浏览器访问 http://localhost:8000
```

> 需要先安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)

**开发环境：**

```bash
pip install -r requirements.txt && cd backend && pip install -r requirements.txt && cd ../frontend && npm install && cd ..
scripts\start.bat  # Windows
# 或
./scripts/start.sh  # Linux/Mac
```

需要 Python 3.10+、ffmpeg（PATH 中）、Node.js 18+。

## 配置

### AI 配置（可选）

如需使用 AI 翻译和智能筛选功能，在界面右侧「AI 配置」栏填写：

- **API 地址**：支持 OpenAI 兼容接口（DeepSeek / OpenAI / Ollama 等）
- **模型名称**：自定义模型
- **API Key**：自动持久化到 localStorage
- **测试连接** / **获取模型列表**：一键验证配置

> **隐私安全**：API Key 仅存储在浏览器本地（localStorage），不会上传到任何服务器，仅在本机与 localhost 后端通信时使用。电脑共用时注意清理浏览器数据。

### 字幕处理配置

左侧「字幕处理配置」栏可调整：

- **最短时长**：过滤过短的字幕（默认 1.0 秒）
- **开头提前**：音频切割时的头部 padding（默认 200ms）
- **结尾延后**：音频切割时的尾部 padding（默认 200ms）

## 使用流程

界面采用三步纵向布局：

1. **准备素材**：上传视频和字幕文件（或自动生成字幕），调整处理配置
2. **筛选内容**：手动勾选字幕，或使用「AI 推荐」智能筛选（需配置 AI）
3. **生成卡片**：点击「开始处理」生成并下载 Anki 牌组

**两种使用模式：**

- **基础模式**（无需 AI）：上传文件 → 手动勾选字幕 → 生成卡片（卡片包含原文、音频、截图）
- **AI 模式**（可选）：配置 AI → 使用「AI 推荐」筛选 → 生成卡片（额外包含翻译和注释）

## 卡片格式

**基础模式（无 AI）：**

- **正面**：截图 + 音频（考察听力）
- **背面**：原文

**AI 模式（可选）：**

- **正面**：截图 + 音频（考察听力）
- **背面**：原文 + 中文翻译 + 词汇注释


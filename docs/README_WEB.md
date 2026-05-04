# ClipLingo - Web 版

一个现代化的 Web 界面，用于将视频和字幕转换为 Anki 学习卡片。

## 技术栈

- **前端**: React + TypeScript + Vite + Tailwind CSS
- **后端**: FastAPI + Python
- **AI**: DeepSeek API
- **媒体处理**: ffmpeg

## 项目结构

```
ClipLingo/
├── backend/              # FastAPI 后端
│   ├── main.py          # 主应用入口
│   ├── api/             # API 路由
│   │   ├── subtitles.py # 字幕相关 API
│   │   ├── process.py   # 处理相关 API
│   │   └── cards.py     # 卡片相关 API
│   └── models/          # Pydantic 模型
│
├── frontend/            # React 前端
│   ├── src/
│   │   ├── components/  # UI 组件
│   │   ├── services/    # API 服务
│   │   ├── types/       # TypeScript 类型
│   │   └── utils/       # 工具函数
│   └── package.json
│
└── 现有的 Python 模块...
```

## 快速开始

### 前置要求

- Python 3.8+
- Node.js 18+
- ffmpeg（系统级安装）

### 1. 安装后端依赖

```bash
# 进入后端目录
cd backend

# 创建虚拟环境（可选）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
pip install -r ../requirements.txt  # 安装主项目依赖
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```
DEEPSEEK_API_KEY=your-api-key-here
```

### 3. 启动后端服务

```bash
cd backend
python main.py
```

后端将在 `http://localhost:8000` 启动

API 文档：`http://localhost:8000/docs`

### 4. 安装前端依赖

```bash
cd frontend

# 安装依赖
npm install

# 或使用其他包管理器
# yarn install
# pnpm install
```

### 5. 启动前端开发服务器

```bash
npm run dev
```

前端将在 `http://localhost:5173` 启动

### 6. 访问应用

打开浏览器访问 `http://localhost:5173`

## 使用方法

1. 配置 DeepSeek API Key
2. 上传视频文件（.mp4, .mkv, .avi）
3. 上传对应的字幕文件（.srt）
4. 调整最短时长过滤条件
5. 点击"加载字幕"预览内容
6. 勾选需要生成卡片的句子
7. 点击"开始处理"生成卡片
8. 预览卡片后下载 .apkg 文件
9. 将 .apkg 文件导入 Anki

## API 端点

### 字幕相关

- `POST /api/subtitles/upload` - 上传并解析字幕文件
- `GET /api/subtitles/example` - 获取示例字幕数据

### 处理相关

- `POST /api/process/start` - 开始处理视频和字幕
- `GET /api/process/progress/{task_id}` - 获取处理进度
- `POST /api/process/validate-api-key` - 验证 API Key

### 卡片相关

- `GET /api/cards/list` - 列出 .apkg 文件中的卡片
- `POST /api/cards/preview` - 预览卡片

### 其他

- `GET /health` - 健康检查
- `GET /download/{filename}` - 下载生成的文件

## 开发

### 后端开发

```bash
cd backend
python main.py
```

### 前端开发

```bash
cd frontend
npm run dev
```

### 构建生产版本

```bash
cd frontend
npm run build
```

构建产物将输出到 `frontend/dist/` 目录

## 部署

### 后端部署

使用 gunicorn + uvicorn：

```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

或使用 Docker：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 前端部署

构建后部署到任何静态文件服务器：

```bash
npm run build
# 部署 dist/ 目录
```

## 常见问题

### Q: npm 命令不可用？

A: 需要先安装 Node.js。从 https://nodejs.org/ 下载并安装。

### Q: 后端启动失败？

A: 检查：
1. Python 版本是否 >= 3.8
2. 是否安装了所有依赖
3. 是否正确配置了 .env 文件
4. ffmpeg 是否已安装并添加到 PATH

### Q: 前端无法连接后端？

A: 检查：
1. 后端服务是否正常运行
2. 前端 .env 文件中的 VITE_API_BASE_URL 是否正确
3. CORS 配置是否正确

## 许可证

MIT

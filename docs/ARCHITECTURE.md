# 项目架构

```mermaid
graph TD
    subgraph Frontend["前端 (React + TypeScript)"]
        App["App.tsx<br/>主页面"]
        API["api.ts<br/>API 客户端"]
        App -->|"subtitleAPI / processAPI"| API
    end

    subgraph Backend["后端 (FastAPI)"]
        BMain["backend/main.py<br/>FastAPI 入口"]
        SubAPI["api/subtitles.py<br/>字幕 / AI推荐 / 转录 / OCR"]
        ProcAPI["api/process.py<br/>处理流程 / 测试连接"]
        CardAPI["api/cards.py<br/>卡片列表 / 预览"]
        Schema["models/schemas.py<br/>Pydantic 数据模型"]
        BMain --> SubAPI
        BMain --> ProcAPI
        BMain --> CardAPI
        SubAPI --> Schema
        ProcAPI --> Schema
        CardAPI --> Schema
    end

    subgraph Pipeline["核心处理流水线"]
        Main["main.py<br/>run() 编排器"]
        Parse["parse_srt.py<br/>SRT 解析"]
        AI["ai_process.py<br/>AI 注释"]
        Media["media_cut.py<br/>音频切片 / 截图"]
        Pack["pack_apkg.py<br/>打包 .apkg"]
        Whisper["whisper_transcribe.py<br/>Whisper 转录"]
        OCR["ocr_subtitle.py<br/>OCR 硬字幕"]
        Main --> Parse
        Main --> AI
        Main --> Media
        Main --> Pack
        Main -.->|"懒加载"| Whisper
    end

    API -->|"HTTP"| BMain
    ProcAPI -->|"importlib 加载 run()"| Main
    SubAPI --> Parse
    SubAPI --> OCR
    SubAPI -.->|"懒加载 save_as_srt()"| Whisper

    subgraph Legacy["旧版 UI"]
        Gradio["ui_gradio.py<br/>Gradio 界面"]
        Gradio --> Parse
        Gradio --> Main
    end
```

## 模块依赖链

```
前端 App.tsx ──► api.ts ──HTTP──► FastAPI ──importlib──► main.run()
                                                              │
                                              ┌────────────────┼────────────────┐
                                              ▼                ▼                ▼
                                         parse_srt.py    ai_process.py    media_cut.py
                                         (解析字幕)       (AI 注释)        (音频+截图)
                                                                              │
                                                                              ▼
                                                                        pack_apkg.py
                                                                        (打包牌组)
```

## API 端点清单

| 端点 | 说明 |
|------|------|
| `POST /api/subtitles/upload` | 上传 SRT 字幕 |
| `POST /api/subtitles/extract-embedded-subs` | 提取内嵌软字幕 |
| `POST /api/subtitles/detect-visible-subs` | 检测硬字幕 |
| `POST /api/subtitles/ocr-extract` | OCR 识别硬字幕 |
| `POST /api/subtitles/transcribe` | Whisper 转录 |
| `POST /api/subtitles/ai-recommend` | AI 筛选推荐句子 |
| `POST /api/process/upload-and-process` | 上传视频+字幕，生成卡片 |
| `POST /api/process/test-connection` | 测试 AI API 连接 |
| `POST /api/process/list-models` | 获取 AI 模型列表 |
| `GET /api/cards/list` | 列出卡片 |
| `POST /api/cards/preview` | 预览卡片 HTML |

## 字幕生成方案链

```
用户点击「生成字幕」
        │
        ▼
  ┌─ 方案一：提取软字幕 (ffmpeg, <1s) ──► 成功 → 返回
  │
  ├─ 方案二：OCR 识别硬字幕 (PaddleOCR) ──► 成功 → 返回
  │
  └─ 方案三：Whisper 转录 (备选) ──► 弹出模型选择器
```

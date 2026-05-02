"""
Anki 卡片生成器 - FastAPI 后端服务
提供 RESTful API 供前端调用
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from typing import List, Optional
import uvicorn
import shutil
import os
from datetime import datetime
from dotenv import load_dotenv

from api.subtitles import router as subtitles_router
from api.process import router as process_router
from api.cards import router as cards_router

load_dotenv()

app = FastAPI(
    title="Anki Card Generator API",
    description="智能提取视频学习内容，生成 Anki 卡片",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite 默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 挂载输出目录供下载 - 与 process.py 中的 ./output 保持一致
# 因为服务从 backend/ 目录启动，CWD 就是 backend/
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

# 注册路由
app.include_router(subtitles_router, prefix="/api/subtitles", tags=["subtitles"])
app.include_router(process_router, prefix="/api/process", tags=["process"])
app.include_router(cards_router, prefix="/api/cards", tags=["cards"])


@app.get("/")
async def root():
    return {
        "message": "Anki Card Generator API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/download/{filename}")
async def download_file(filename: str):
    """下载生成的文件"""
    file_path = output_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

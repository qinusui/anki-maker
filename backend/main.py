"""
Anki 卡片生成器 - FastAPI 后端服务
提供 RESTful API 供前端调用
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from typing import List, Optional
import uvicorn
import shutil
import os
import json
import signal
import logging
import threading
import time
from datetime import datetime
from dotenv import load_dotenv

# 静默心跳日志
class HeartbeatFilter(logging.Filter):
    def filter(self, record):
        return '/api/heartbeat' not in record.getMessage()

logging.getLogger("uvicorn.access").addFilter(HeartbeatFilter())

from api.subtitles import router as subtitles_router
from api.process import router as process_router
from api.cards import router as cards_router

load_dotenv()

# ---- 自动关闭机制 ----
_last_heartbeat = time.time() + 120
_shutdown_lock = threading.Lock()
HEARTBEAT_TIMEOUT = 20  # 20 秒无心跳才判定关闭，避免处理高负载时误杀


def _kill_processes():
    """读取 PID 文件并关闭前后端进程"""
    pid_file = Path(__file__).parent / 'pids.json'
    if not pid_file.exists():
        return
    try:
        pids = json.loads(pid_file.read_text())
    except Exception:
        return

    for key in ('frontend_pid', 'backend_pid'):
        pid = pids.get(key)
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass

    pid_file.unlink(missing_ok=True)


def _shutdown_watcher():
    """后台线程：20 秒无心跳则自动关闭所有服务"""
    while True:
        time.sleep(5)
        with _shutdown_lock:
            if time.time() - _last_heartbeat > HEARTBEAT_TIMEOUT:
                print(f"[自动关闭] 检测到页面已关闭 ({HEARTBEAT_TIMEOUT}s 无心跳)，正在停止所有服务...")
                _kill_processes()
                os._exit(0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 仅在 start-all.py 启动时（存在 PID 文件）且在真正服务进程（非 reloader）中启用
    _pid_file = Path(__file__).parent / 'pids.json'
    if _pid_file.exists():
        _watcher_thread = threading.Thread(target=_shutdown_watcher, daemon=True)
        _watcher_thread.start()
    yield


app = FastAPI(
    title="Anki Card Generator API",
    description="智能提取视频学习内容，生成 Anki 卡片",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 挂载输出目录供下载和预览
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")

# 注册路由
app.include_router(subtitles_router, prefix="/api/subtitles", tags=["subtitles"])
app.include_router(process_router, prefix="/api/process", tags=["process"])
app.include_router(cards_router, prefix="/api/cards", tags=["cards"])


@app.post("/api/heartbeat")
async def heartbeat():
    global _last_heartbeat
    with _shutdown_lock:
        _last_heartbeat = time.time()
    return {"status": "ok"}


@app.post("/api/shutdown")
async def shutdown():
    """立即关闭所有服务"""
    _kill_processes()
    return {"message": "Shutting down..."}


# ---- 业务路由 ----

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

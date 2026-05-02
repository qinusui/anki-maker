"""
处理相关 API - 处理字幕并生成卡片
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pathlib import Path
from typing import List, Optional
import asyncio
import json
import os
import shutil
import threading
import uuid
from datetime import datetime

from models.schemas import ProcessRequest, ProcessResult, ProcessedCard, ProcessProgress

# 导入现有模块
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
import importlib.util
spec = importlib.util.spec_from_file_location("main", str(Path(__file__).parent.parent.parent / "main.py"))
main_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_module)
process_cards = main_module.run

router = APIRouter()

# 临时文件存储目录
TEMP_DIR = Path(__file__).parent.parent.parent / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# 任务进度存储 (task_id -> progress dict)
task_store: dict = {}
task_store_lock = threading.Lock()


def _build_cards(processed_data):
    """将处理数据转为 ProcessedCard 列表，文件路径转为 HTTP URL"""
    cards = []
    for item in processed_data:
        audio_path = item.get("audio_path")
        screenshot_path = item.get("screenshot_path")
        cards.append(ProcessedCard(
            sentence=item.get("text", ""),
            translation=item.get("translation", ""),
            notes=item.get("notes", ""),
            start_sec=item.get("start_sec", 0),
            end_sec=item.get("end_sec", 0),
            audio_path="/" + Path(audio_path).as_posix() if audio_path else None,
            screenshot_path="/" + Path(screenshot_path).as_posix() if screenshot_path else None
        ))
    return cards


@router.post("/upload-and-process")
async def upload_and_process(
    video: UploadFile = File(...),
    subtitle: UploadFile = File(...),
    min_duration: float = Form(1.0),
    output_dir: str = Form("./output"),
    api_key: Optional[str] = Form(None)
):
    """
    上传视频和字幕文件，后台异步处理
    返回 task_id，前端通过 /progress/{task_id} 轮询进度
    """
    task_id = str(uuid.uuid4())
    task_dir = TEMP_DIR / task_id
    task_dir.mkdir(exist_ok=True)

    # 保存上传的文件
    video_path = task_dir / video.filename
    subtitle_path = task_dir / subtitle.filename

    with open(video_path, "wb") as f:
        shutil.copyfileobj(video.file, f)
    with open(subtitle_path, "wb") as f:
        shutil.copyfileobj(subtitle.file, f)

    if api_key:
        os.environ["DEEPSEEK_API_KEY"] = api_key

    # 初始化任务进度
    with task_store_lock:
        task_store[task_id] = {
            "status": "preparing",
            "step": 0,
            "total_steps": 5,
            "message": "准备处理...",
            "details": None,
            "result": None,
            "error": None
        }

    def progress_callback(step, total_steps, message, details=None):
        with task_store_lock:
            task_store[task_id].update({
                "status": "processing",
                "step": step,
                "total_steps": total_steps,
                "message": message,
                "details": details
            })

    def run_processing():
        try:
            with task_store_lock:
                task_store[task_id]["status"] = "processing"
                task_store[task_id]["message"] = "开始处理..."

            result = process_cards(
                video_path=str(video_path),
                subtitle_path=str(subtitle_path),
                output_dir=output_dir,
                min_duration=min_duration,
                progress_callback=progress_callback
            )

            apkg_filename = Path(result["apkg_path"]).name
            cards = _build_cards(result.get("processed", []))

            with task_store_lock:
                task_store[task_id].update({
                    "status": "completed",
                    "step": 5,
                    "message": f"处理完成，生成了 {result['cards_count']} 张卡片",
                    "result": {
                        "success": True,
                        "message": f"处理完成，生成了 {result['cards_count']} 张卡片",
                        "cards_count": result["cards_count"],
                        "apkg_path": apkg_filename,
                        "cards": [c.model_dump() for c in cards]
                    }
                })

        except Exception as e:
            import traceback
            traceback.print_exc()
            with task_store_lock:
                task_store[task_id].update({
                    "status": "error",
                    "message": f"处理失败: {str(e)}",
                    "error": str(e)
                })

    # 在后台线程中执行
    thread = threading.Thread(target=run_processing, daemon=True)
    thread.start()

    return {"task_id": task_id, "status": "started"}


@router.get("/progress/{task_id}")
async def get_progress(task_id: str):
    """
    获取处理进度

    Args:
        task_id: 任务ID

    Returns:
        ProcessProgress: 当前处理进度
    """
    with task_store_lock:
        task = task_store.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    response = {
        "task_id": task_id,
        "status": task["status"],
        "step": task["step"],
        "total_steps": task["total_steps"],
        "message": task["message"],
        "details": task["details"],
        "error": task.get("error")
    }

    # 如果已完成，附带结果
    if task["status"] == "completed" and task["result"]:
        response["result"] = task["result"]
    elif task["status"] == "error":
        response["error"] = task.get("error")

    return response


@router.post("/start", response_model=ProcessResult)
async def start_processing(
    video_file_path: str,
    subtitle_file_path: str,
    min_duration: float = 1.0,
    output_dir: str = "./output",
    api_key: Optional[str] = None
):
    """
    开始处理视频和字幕，生成 Anki 卡片

    Args:
        video_file_path: 视频文件路径
        subtitle_file_path: 字幕文件路径
        min_duration: 最短字幕时长
        output_dir: 输出目录
        api_key: DeepSeek API Key

    Returns:
        ProcessResult: 处理结果
    """
    # 验证文件存在
    video_path = Path(video_file_path)
    subtitle_path = Path(subtitle_file_path)

    if not video_path.exists():
        raise HTTPException(status_code=404, detail="视频文件不存在")

    if not subtitle_path.exists():
        raise HTTPException(status_code=404, detail="字幕文件不存在")

    # 设置 API Key
    if api_key:
        os.environ["DEEPSEEK_API_KEY"] = api_key

    try:
        # 调用处理函数
        result = process_cards(
            video_path=str(video_path),
            subtitle_path=str(subtitle_path),
            output_dir=output_dir,
            min_duration=min_duration
        )

        apkg_path = result["apkg_path"]
        cards_count = result["cards_count"]
        processed_data = result.get("processed", [])
        cards = _build_cards(processed_data)

        return ProcessResult(
            success=True,
            message=f"处理完成，生成了 {cards_count} 张卡片",
            cards_count=cards_count,
            apkg_path=apkg_path,
            cards=cards
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.post("/validate-api-key")
async def validate_api_key(api_key: str):
    """
    验证 API Key 是否有效
    """
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=10
        )

        return {"valid": True, "message": "API Key 有效"}

    except Exception as e:
        return {"valid": False, "message": f"API Key 无效: {str(e)}"}

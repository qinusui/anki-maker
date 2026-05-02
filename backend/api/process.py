"""
处理相关 API - 处理字幕并生成卡片
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pathlib import Path
from typing import List, Optional
import os
import shutil
import uuid
from datetime import datetime

from models.schemas import ProcessRequest, ProcessResult, ProcessedCard, ProcessProgress

# 导入现有模块
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
# 导入项目根目录的 main 模块（避免循环导入）
import importlib.util
spec = importlib.util.spec_from_file_location("main", str(Path(__file__).parent.parent.parent / "main.py"))
main_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_module)
process_cards = main_module.run

router = APIRouter()

# 临时文件存储目录
TEMP_DIR = Path(__file__).parent.parent.parent / "temp"
TEMP_DIR.mkdir(exist_ok=True)


@router.post("/upload-and-process", response_model=ProcessResult)
async def upload_and_process(
    video: UploadFile = File(...),
    subtitle: UploadFile = File(...),
    min_duration: float = Form(1.0),
    output_dir: str = Form("./output"),
    api_key: Optional[str] = Form(None)
):
    """
    上传视频和字幕文件，并立即开始处理

    Args:
        video: 视频文件
        subtitle: 字幕文件
        min_duration: 最短字幕时长
        output_dir: 输出目录
        api_key: DeepSeek API Key

    Returns:
        ProcessResult: 处理结果
    """
    # 生成唯一的任务 ID
    task_id = str(uuid.uuid4())
    task_dir = TEMP_DIR / task_id
    task_dir.mkdir(exist_ok=True)

    # 保存上传的文件
    video_path = task_dir / video.filename
    subtitle_path = task_dir / subtitle.filename

    try:
        # 保存视频文件
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video.file, f)

        # 保存字幕文件
        with open(subtitle_path, "wb") as f:
            shutil.copyfileobj(subtitle.file, f)

        # 设置 API Key
        if api_key:
            os.environ["DEEPSEEK_API_KEY"] = api_key

        # 调用处理函数
        result = process_cards(
            video_path=str(video_path),
            subtitle_path=str(subtitle_path),
            output_dir=output_dir,
            min_duration=min_duration
        )

        # 从返回结果中获取信息
        apkg_path = result["apkg_path"]
        cards_count = result["cards_count"]
        processed_data = result.get("processed", [])

        # 将相对路径转为绝对路径，用于下载
        output_dir_path = Path(output_dir)
        if not output_dir_path.is_absolute():
            output_dir_path = Path.cwd() / output_dir_path

        apkg_full_path = output_dir_path / apkg_path
        apkg_filename = Path(apkg_path).name

        # 将 processed 数据转换为 ProcessedCard 格式（文件路径转为 HTTP URL）
        cards = []
        for item in processed_data:
            audio_path = item.get("audio_path")
            screenshot_path = item.get("screenshot_path")
            cards.append(ProcessedCard(
                sentence=item.get("sentence", ""),
                translation=item.get("translation", ""),
                notes=item.get("notes", ""),
                start_sec=item.get("start_sec", 0),
                end_sec=item.get("end_sec", 0),
                audio_path="/" + Path(audio_path).as_posix() if audio_path else None,
                screenshot_path="/" + Path(screenshot_path).as_posix() if screenshot_path else None
            ))
        ]

        return ProcessResult(
            success=True,
            message=f"处理完成，生成了 {cards_count} 张卡片",
            cards_count=cards_count,
            apkg_path=apkg_filename,
            cards=cards
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


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

        # 从返回结果中获取信息
        apkg_path = result["apkg_path"]
        cards_count = result["cards_count"]
        processed_data = result.get("processed", [])

        # 将 processed 数据转换为 ProcessedCard 格式（文件路径转为 HTTP URL）
        cards = []
        for item in processed_data:
            audio_path = item.get("audio_path")
            screenshot_path = item.get("screenshot_path")
            cards.append(ProcessedCard(
                sentence=item.get("sentence", ""),
                translation=item.get("translation", ""),
                notes=item.get("notes", ""),
                start_sec=item.get("start_sec", 0),
                end_sec=item.get("end_sec", 0),
                audio_path="/" + Path(audio_path).as_posix() if audio_path else None,
                screenshot_path="/" + Path(screenshot_path).as_posix() if screenshot_path else None
            ))
        ]

        return ProcessResult(
            success=True,
            message=f"处理完成，生成了 {cards_count} 张卡片",
            cards_count=cards_count,
            apkg_path=apkg_path,
            cards=cards
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/progress/{task_id}")
async def get_progress(task_id: str):
    """
    获取处理进度（暂未实现）

    Args:
        task_id: 任务ID

    Returns:
        ProcessProgress: 当前处理进度
    """
    # TODO: 实现真正的进度跟踪
    return {
        "step": "processing",
        "message": "处理中...",
        "progress": 50,
        "total_steps": 5,
        "current_step": 3
    }


@router.post("/validate-api-key")
async def validate_api_key(api_key: str):
    """
    验证 API Key 是否有效

    Args:
        api_key: DeepSeek API Key

    Returns:
        验证结果
    """
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )

        # 发送一个简单的测试请求
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=10
        )

        return {"valid": True, "message": "API Key 有效"}

    except Exception as e:
        return {"valid": False, "message": f"API Key 无效: {str(e)}"}

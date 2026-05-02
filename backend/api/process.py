"""
处理相关 API - 处理字幕并生成卡片
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
from typing import List, Optional
import os
import asyncio
from datetime import datetime

from models.schemas import ProcessRequest, ProcessResult, ProcessedCard, ProcessProgress

# 导入现有模块
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from main import run as process_cards

router = APIRouter()

# 全局变量存储处理状态
processing_status = {}


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
        apkg_path = process_cards(
            video_path=str(video_path),
            subtitle_path=str(subtitle_path),
            output_dir=output_dir,
            min_duration=min_duration
        )

        # 这里简化处理，实际应该从处理结果中读取卡片数据
        # 可以通过修改 process_cards 返回更多信息来实现

        return ProcessResult(
            success=True,
            message="处理完成",
            cards_count=0,  # 需要从实际处理结果获取
            apkg_path=str(apkg_path),
            cards=[]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/progress/{task_id}")
async def get_progress(task_id: str):
    """
    获取处理进度

    Args:
        task_id: 任务ID

    Returns:
        ProcessProgress: 当前处理进度
    """
    if task_id not in processing_status:
        raise HTTPException(status_code=404, detail="任务不存在")

    return processing_status[task_id]


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

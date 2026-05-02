"""
字幕相关 API
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import tempfile
import shutil
from typing import List

from models.schemas import SubtitleItem, SubtitleListResponse

# 导入现有的字幕解析模块
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from parse_srt import parse_srt, filter_short_subtitles

router = APIRouter()


@router.post("/upload", response_model=SubtitleListResponse)
async def upload_subtitle(
    file: UploadFile = File(...),
    min_duration: float = 1.0
):
    """
    上传并解析字幕文件

    Args:
        file: SRT 字幕文件
        min_duration: 最短字幕时长（秒），过滤掉过短的对话

    Returns:
        SubtitleListResponse: 解析后的字幕列表
    """
    if not file.filename.endswith('.srt'):
        raise HTTPException(status_code=400, detail="只支持 .srt 格式的字幕文件")

    # 保存临时文件
    temp_dir = Path(__file__).parent.parent.parent / "temp"
    temp_dir.mkdir(exist_ok=True)

    temp_path = temp_dir / f"temp_{file.filename}"

    try:
        # 保存上传的文件
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 解析字幕
        subtitles = parse_srt(str(temp_path))

        # 过滤过短字幕
        original_count = len(subtitles)
        subtitles = filter_short_subtitles(subtitles, min_duration)

        # 转换为响应格式
        subtitle_items = [
            SubtitleItem(
                index=sub.index,
                start_sec=round(sub.start_sec, 3),
                end_sec=round(sub.end_sec, 3),
                text=sub.text,
                duration=round(sub.end_sec - sub.start_sec, 3)
            )
            for sub in subtitles
        ]

        return SubtitleListResponse(
            subtitles=subtitle_items,
            total=original_count,
            filtered=len(subtitle_items)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析字幕失败: {str(e)}")

    finally:
        # 清理临时文件
        if temp_path.exists():
            temp_path.unlink()


@router.get("/example", response_model=SubtitleListResponse)
async def get_example_subtitles():
    """
    获取示例字幕数据（用于前端演示）
    """
    example_data = [
        SubtitleItem(
            index=1,
            start_sec=83.456,
            end_sec=85.789,
            text="Hello, how are you?",
            duration=2.333
        ),
        SubtitleItem(
            index=2,
            start_sec=86.123,
            end_sec=89.456,
            text="I'm doing great, thanks for asking!",
            duration=3.333
        ),
        SubtitleItem(
            index=3,
            start_sec=90.123,
            end_sec=94.567,
            text="What have you been up to lately?",
            duration=4.444
        )
    ]

    return SubtitleListResponse(
        subtitles=example_data,
        total=3,
        filtered=3
    )

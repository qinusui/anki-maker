"""
字幕相关 API
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import tempfile
import shutil
import json
import os
import asyncio
from typing import List

from models.schemas import SubtitleItem, SubtitleListResponse, AIRecommendRequest, AIRecommendItem, AIRecommendResponse

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


DEFAULT_RECOMMEND_PROMPT = """你是英语学习教材编写专家。对输入的字幕列表，每条判断是否值得作为学习材料：

判断标准：
- 有明确的语法知识点（如时态、从句、虚拟语气等）
- 有实用表达或固定搭配
- 对话内容有意义（非简单寒暄如'okay', 'yeah', 'uh-huh'等）
- 有文化背景或情境意义

返回格式（JSON数组）：
[{"include": true/false, "reason": "简短原因", "translation": "中文翻译", "notes": "重点词汇-释义"}, ...]

注意：
- include=true 表示值得加入学习
- include=false 时 reason 说明原因（如：纯简单应答、无知识价值）
- 只对 include=true 的句子提供 translation 和 notes
- 保持原文顺序输出"""


def _run_ai_recommend(subtitle_dicts: list, api_key: str, system_prompt: str) -> list:
    """同步执行 AI 推荐（在线程池中运行）"""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    results = []
    batch_size = 30
    total_batches = (len(subtitle_dicts) + batch_size - 1) // batch_size

    for i in range(0, len(subtitle_dicts), batch_size):
        batch = subtitle_dicts[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"  AI 推荐：处理第 {batch_num}/{total_batches} 批 ({len(batch)} 条)...")

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(batch, ensure_ascii=False)}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )

            content = response.choices[0].message.content
            parsed = json.loads(content)

            if isinstance(parsed, dict):
                for v in parsed.values():
                    if isinstance(v, list):
                        results.extend(v)
                        break
            elif isinstance(parsed, list):
                results.extend(parsed)

        except Exception as e:
            print(f"    批次处理失败: {e}")
            for item in batch:
                results.append({"index": item["index"], "include": False, "reason": f"处理失败: {e}"})

    return results


@router.post("/ai-recommend", response_model=AIRecommendResponse)
async def ai_recommend(request: AIRecommendRequest):
    """
    AI 分析字幕，推荐值得学习的句子

    Args:
        request: 包含字幕列表、API Key 和可选的自定义提示词
    """
    import asyncio

    api_key = request.api_key or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="需要提供 API Key")

    system_prompt = request.custom_prompt or DEFAULT_RECOMMEND_PROMPT

    subtitle_dicts = [
        {"index": s.index, "start_sec": s.start_sec, "end_sec": s.end_sec, "text": s.text}
        for s in request.subtitles
    ]

    # 在线程池中执行，避免阻塞事件循环
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(
        None,
        _run_ai_recommend,
        subtitle_dicts,
        api_key,
        system_prompt
    )

    recommendations = []
    for item in results:
        recommendations.append(AIRecommendItem(
            index=item.get("index", 0),
            include=item.get("include", False),
            reason=item.get("reason", ""),
            translation=item.get("translation") if item.get("include") else None,
            notes=item.get("notes") if item.get("include") else None
        ))

    return AIRecommendResponse(recommendations=recommendations)


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

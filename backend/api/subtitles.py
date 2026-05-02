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
from typing import List, Optional

from models.schemas import (
    SubtitleItem, SubtitleListResponse, AIRecommendRequest,
    AIRecommendItem, AIRecommendResponse, EmbeddedSubtitleStream, ExtractEmbeddedResponse
)

# 导入现有的字幕解析模块
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from parse_srt import parse_srt, filter_short_subtitles
from ocr_subtitle import detect_visible_subtitles, extract_hard_subtitles

router = APIRouter()

# 常见 API 错误信息的中文翻译
_API_ERROR_TRANSLATE = [
    ("model does not exist", "模型不存在，请检查模型名称"),
    ("invalid api key", "API Key 无效"),
    ("insufficient", "API 余额不足"),
    ("rate limit", "请求太频繁，请稍后重试"),
    ("timeout", "请求超时"),
    ("connection", "无法连接 API 服务器"),
]


def _tr(msg: str) -> str:
    """将 API 错误信息翻译为中文"""
    lower = msg.lower()
    for keyword, chinese in _API_ERROR_TRANSLATE:
        if keyword in lower:
            return chinese
    return msg


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


# 可从视频提取的文本字幕编码
_TEXT_SUBTITLE_CODECS = {"subrip", "mov_text", "webvtt", "ass", "ssa", "srt", "sami", "microdvd", "text", "stl", "eia_608", "eia_708"}


@router.post("/extract-embedded-subs")
async def extract_embedded_subtitles(
    video: UploadFile = File(...),
    stream_index: int = 0,
    min_duration: float = 1.0
):
    """
    检测并提取视频内嵌字幕（优先于 Whisper 转录）

    Args:
        video: 视频文件
        stream_index: 要提取的字幕流序号（默认第一个）
        min_duration: 最短字幕时长

    Returns:
        ExtractEmbeddedResponse: 字幕流列表及提取结果
    """
    import subprocess

    if not video.filename:
        raise HTTPException(status_code=400, detail="未提供视频文件")

    temp_dir = Path(__file__).parent.parent.parent / "temp"
    temp_dir.mkdir(exist_ok=True)

    video_path = temp_dir / f"extract_{video.filename}"

    try:
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video.file, f)

        # 1. 用 ffprobe 检测字幕流
        probe_result = subprocess.run([
            "ffprobe", "-v", "error",
            "-select_streams", "s",
            "-show_entries", "stream=index:codec_name:stream_tags=language,title",
            "-of", "json",
            str(video_path)
        ], capture_output=True, text=True, timeout=30)

        if probe_result.returncode != 0:
            raise HTTPException(status_code=500, detail="ffprobe 检测失败，请确认已安装 ffmpeg")

        probe_data = json.loads(probe_result.stdout)
        streams = probe_data.get("streams", [])

        if not streams:
            return {"found": False, "streams": [], "extracted": None,
                    "message": "视频中没有内嵌字幕，请使用 Whisper 转录"}

        # 分类字幕流
        subtitle_streams = []
        for s in streams:
            codec = s.get("codec_name", "unknown")
            tags = s.get("tags", {})
            subtitle_streams.append({
                "index": s.get("index", 0),
                "codec": codec,
                "language": tags.get("language", "unknown"),
                "title": tags.get("title", ""),
                "text_based": codec in _TEXT_SUBTITLE_CODECS
            })

        text_streams = [s for s in subtitle_streams if s["text_based"]]
        image_streams = [s for s in subtitle_streams if not s["text_based"]]

        if not text_streams:
            image_names = ", ".join(s["codec"] for s in image_streams)
            return {
                "found": True, "streams": subtitle_streams, "extracted": None,
                "message": f"内嵌字幕为图像格式（{image_names}），无法直接提取文本，请使用 Whisper 转录"
            }

        # 2. 选择字幕流并提取
        if stream_index >= len(text_streams):
            stream_index = 0
        target = text_streams[stream_index]

        srt_path = temp_dir / f"extracted_{video.filename}.srt"
        extract_cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-map", f"0:s:{stream_index}",
            "-f", "srt",
            str(srt_path)
        ]
        subprocess.run(extract_cmd, capture_output=True, text=True, timeout=60)

        if not srt_path.exists() or srt_path.stat().st_size == 0:
            return {
                "found": True, "streams": subtitle_streams, "extracted": None,
                "message": "提取字幕失败，请尝试 Whisper 转录"
            }

        # 3. 解析字幕
        import_subtitles = parse_srt(str(srt_path))
        original_count = len(import_subtitles)
        import_subtitles = filter_short_subtitles(import_subtitles, min_duration)

        subtitle_items = [
            SubtitleItem(
                index=sub.index,
                start_sec=round(sub.start_sec, 3),
                end_sec=round(sub.end_sec, 3),
                text=sub.text,
                duration=round(sub.end_sec - sub.start_sec, 3)
            )
            for sub in import_subtitles
        ]

        return {
            "found": True,
            "streams": subtitle_streams,
            "extracted": {
                "stream_index": target["index"],
                "codec": target["codec"],
                "language": target["language"],
                "subtitles": [s.model_dump() for s in subtitle_items],
                "total": original_count,
                "filtered": len(subtitle_items)
            },
            "message": f"已从视频提取 {len(subtitle_items)} 条内嵌字幕"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提取字幕失败: {str(e)}")

    finally:
        if video_path.exists():
            video_path.unlink()
        srt_temp = temp_dir / f"extracted_{video.filename}.srt"
        if srt_temp.exists():
            srt_temp.unlink(missing_ok=True)


# ── OCR 硬字幕识别 ──────────────────────────────────────────────

import threading as _ocr_threading
import uuid as _ocr_uuid

_ocr_store: dict = {}
_ocr_lock = _ocr_threading.Lock()


@router.post("/detect-visible-subs")
async def detect_visible_subs_endpoint(video: UploadFile = File(...)):
    """
    快速检测视频是否有可见硬字幕（取若干帧底部区域做 OCR）
    """
    if not video.filename:
        raise HTTPException(status_code=400, detail="未提供视频文件")

    temp_dir = Path(__file__).parent.parent.parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    video_path = temp_dir / f"detect_{video.filename}"

    try:
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video.file, f)

        has_subs = detect_visible_subtitles(str(video_path))
        return {"has_visible_subtitles": has_subs}

    except ImportError:
        return {"has_visible_subtitles": False, "message": "PaddleOCR 未安装"}
    except Exception as e:
        return {"has_visible_subtitles": False, "message": f"检测失败: {str(e)}"}

    finally:
        if video_path.exists():
            video_path.unlink()


def _run_ocr_extract(task_id: str, video_path_str: str, lang: str,
                     min_duration: float, conf_threshold: float):
    """后台执行 OCR 硬字幕提取"""

    def update(status, step, message):
        with _ocr_lock:
            _ocr_store[task_id] = {"status": status, "step": step, "total_steps": 3, "message": message}

    srt_path_str = str(Path(video_path_str).with_suffix(".ocr.srt"))

    try:
        update("processing", 0, "检测视频是否有可见字幕...")

        if not detect_visible_subtitles(video_path_str):
            update("error", 0, "未检测到可见字幕，请使用 Whisper 转录")
            return

        def progress(step, total, message):
            pct = min(step / max(total, 1), 1.0)
            s = int(pct * 2) + 1  # map to step 1-2
            update("processing", s, message)

        update("processing", 1, "OCR 识别硬字幕中...")
        segments = extract_hard_subtitles(
            video_path_str, lang=lang,
            conf_threshold=conf_threshold,
            progress_callback=progress
        )

        if not segments:
            update("error", 0, "OCR 未识别到字幕文字")
            return

        # 转为标准 SRT 并解析
        from whisper_transcribe import save_as_srt
        save_as_srt(segments, srt_path_str)

        subtitles = parse_srt(srt_path_str)
        original_count = len(subtitles)
        subtitles = filter_short_subtitles(subtitles, min_duration)

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

        with _ocr_lock:
            _ocr_store[task_id] = {
                "status": "completed",
                "step": 3,
                "total_steps": 3,
                "message": f"OCR 完成，识别 {len(subtitle_items)} 条字幕",
                "result": {
                    "subtitles": [s.model_dump() for s in subtitle_items],
                    "total": original_count,
                    "filtered": len(subtitle_items),
                    "source": "ocr"
                }
            }

    except ImportError:
        with _ocr_lock:
            _ocr_store[task_id] = {
                "status": "error", "step": 0, "total_steps": 3,
                "message": "PaddleOCR 未安装", "error": "PaddleOCR 未安装"
            }
    except Exception as e:
        with _ocr_lock:
            _ocr_store[task_id] = {
                "status": "error", "step": 0, "total_steps": 3,
                "message": f"OCR 提取失败: {str(e)}", "error": str(e)
            }

    finally:
        if Path(video_path_str).exists():
            Path(video_path_str).unlink(missing_ok=True)
        if Path(srt_path_str).exists():
            Path(srt_path_str).unlink(missing_ok=True)


@router.post("/ocr-extract")
async def ocr_extract_endpoint(
    video: UploadFile = File(...),
    min_duration: float = 1.0,
    lang: str = "ch",
    conf_threshold: float = 1.0
):
    """
    OCR 识别视频硬字幕（后台异步，通过 progress 端点轮询）
    """
    if not video.filename:
        raise HTTPException(status_code=400, detail="未提供视频文件")

    temp_dir = Path(__file__).parent.parent.parent / "temp"
    temp_dir.mkdir(exist_ok=True)

    video_path = temp_dir / f"ocr_{video.filename}"
    with open(video_path, "wb") as f:
        shutil.copyfileobj(video.file, f)

    task_id = str(_ocr_uuid.uuid4())

    with _ocr_lock:
        _ocr_store[task_id] = {
            "status": "preparing", "step": 0, "total_steps": 3,
            "message": "准备 OCR 识别..."
        }

    thread = _ocr_threading.Thread(
        target=_run_ocr_extract,
        args=(task_id, str(video_path), lang, min_duration, conf_threshold),
        daemon=True
    )
    thread.start()

    return {"task_id": task_id, "status": "started"}


@router.get("/ocr-extract/progress/{task_id}")
async def ocr_extract_progress(task_id: str):
    """获取 OCR 识别的实时进度"""
    with _ocr_lock:
        task = _ocr_store.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return task


DEFAULT_CRITERIA = """你是英语学习教材编写专家。对输入的字幕列表，每条判断是否值得作为学习材料：

判断标准：
- 有明确的语法知识点（如时态、从句、虚拟语气等）
- 有实用表达或固定搭配
- 对话内容有意义（非简单寒暄如'okay', 'yeah', 'uh-huh'等）
- 有文化背景或情境意义"""

RETURN_FORMAT = """

返回格式（严格遵守）：
{"items": [{"index": 数字, "include": true/false, "reason": "简短原因", "translation": "中文翻译", "notes": "重点词汇-释义"}, ...]}

注意：
- 必须返回一个 JSON 对象，items 是数组
- include=true 表示值得加入学习
- include=false 时 reason 说明原因（如：纯简单应答、无知识价值）
- 只对 include=true 的句子提供 translation 和 notes
- 保持原文顺序输出，每条都必须有 index 字段"""


def _build_system_prompt(custom_prompt: str = None) -> str:
    """组合用户自定义的判断标准与固定的返回格式"""
    criteria = custom_prompt or DEFAULT_CRITERIA
    return criteria + RETURN_FORMAT


# AI 推荐任务进度存储
import threading as _threading
import uuid as _uuid

_recommend_store: dict = {}
_recommend_lock = _threading.Lock()


def _run_ai_recommend(task_id: str, subtitle_dicts: list, api_key: str, system_prompt: str,
                      batch_size: int = 30, api_base: str = "https://api.deepseek.com",
                      model_name: str = "deepseek-chat"):
    """同步执行 AI 推荐（后台线程，带重试机制）"""
    import time as _time
    from openai import OpenAI

    MAX_RETRIES = 3
    RETRY_DELAYS = [2, 5, 10]  # 秒

    # 瞬时错误关键词（可重试）
    _TRANSIENT_KW = ("connection", "timeout", "rate limit", "server error",
                     "503", "502", "500", "429", "unreachable", "refused",
                     "reset by peer", "too many requests")

    def _is_transient(err_msg: str) -> bool:
        lower = err_msg.lower()
        return any(kw in lower for kw in _TRANSIENT_KW)

    client = OpenAI(api_key=api_key, base_url=api_base)
    results = []
    batch_size = max(1, min(100, batch_size))
    total_batches = (len(subtitle_dicts) + batch_size - 1) // batch_size
    failed_batches = 0

    with _recommend_lock:
        _recommend_store[task_id] = {
            "status": "processing",
            "batch": 0,
            "total_batches": total_batches,
            "message": "开始分析..."
        }

    for i in range(0, len(subtitle_dicts), batch_size):
        batch = subtitle_dicts[i:i + batch_size]
        batch_num = i // batch_size + 1
        msg = f"处理第 {batch_num}/{total_batches} 批 ({len(batch)} 条)..."
        print(f"  AI 推荐：{msg}")

        with _recommend_lock:
            _recommend_store[task_id].update({
                "batch": batch_num,
                "total_batches": total_batches,
                "message": msg
            })

        batch_ok = False
        last_error = ""

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": json.dumps(batch, ensure_ascii=False)}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2,
                )

                content = response.choices[0].message.content
                print(f"    AI 响应: {content[:200]}...")
                parsed = json.loads(content)

                if isinstance(parsed, dict):
                    items = parsed.get("items") or parsed.get("results")
                    if items and isinstance(items, list):
                        results.extend(items)
                    else:
                        for v in parsed.values():
                            if isinstance(v, list):
                                results.extend(v)
                                break
                elif isinstance(parsed, list):
                    results.extend(parsed)

                batch_ok = True
                break  # 成功，退出重试循环

            except Exception as e:
                last_error = _tr(str(e))
                is_transient = _is_transient(str(e))

                if is_transient and attempt < MAX_RETRIES:
                    delay = RETRY_DELAYS[attempt]
                    print(f"    批次 {batch_num} 失败（{last_error}），{delay}s 后重试 ({attempt+1}/{MAX_RETRIES})...")
                    _time.sleep(delay)
                else:
                    break  # 非瞬时错误或重试耗尽

        if not batch_ok:
            failed_batches += 1
            reason = f"处理失败: {last_error}"
            print(f"    批次 {batch_num} 最终失败: {last_error}")
            for item in batch:
                results.append({"index": item["index"], "include": False, "reason": reason})

    # 构建最终推荐结果
    recommendations = []
    for item in results:
        recommendations.append(AIRecommendItem(
            index=item.get("index", 0),
            include=item.get("include", False),
            reason=item.get("reason", ""),
            translation=item.get("translation") if item.get("include") else None,
            notes=item.get("notes") if item.get("include") else None
        ))

    finish_msg = f"分析完成，共 {len(recommendations)} 条"
    if failed_batches > 0:
        finish_msg += f"（{failed_batches} 批失败）"

    with _recommend_lock:
        _recommend_store[task_id].update({
            "status": "completed",
            "batch": total_batches,
            "message": finish_msg,
            "result": AIRecommendResponse(recommendations=recommendations).model_dump()
        })


@router.post("/ai-recommend")
async def ai_recommend(request: AIRecommendRequest):
    """
    AI 分析字幕，推荐值得学习的句子（后台异步，通过 progress 端点轮询）
    """
    api_key = request.api_key or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="需要提供 API Key")

    system_prompt = _build_system_prompt(request.custom_prompt)

    subtitle_dicts = [
        {"index": s.index, "start_sec": s.start_sec, "end_sec": s.end_sec, "text": s.text}
        for s in request.subtitles
    ]

    api_base = request.api_base or "https://api.deepseek.com"
    model_name = request.model_name or "deepseek-chat"

    task_id = str(_uuid.uuid4())

    # 在后台线程中执行
    thread = _threading.Thread(
        target=_run_ai_recommend,
        args=(task_id, subtitle_dicts, api_key, system_prompt, request.batch_size,
              api_base, model_name),
        daemon=True
    )
    thread.start()

    return {"task_id": task_id, "status": "started"}


@router.get("/ai-recommend/progress/{task_id}")
async def ai_recommend_progress(task_id: str):
    """获取 AI 推荐的实时处理进度"""
    with _recommend_lock:
        task = _recommend_store.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return task


# 转录任务进度存储
_transcribe_store: dict = {}
_transcribe_lock = _threading.Lock()

# 项目根目录（用于子进程设置 sys.path）
_PROJECT_ROOT = str(Path(__file__).parent.parent.parent)


def _whisper_subprocess(video_path: str, srt_path: str, model_name: str, language: str,
                        result_path: str, progress_pipe):
    """在独立进程中运行 Whisper 转录，通过 Pipe 报告进度"""
    import sys as _sys
    _sys.path.append(_PROJECT_ROOT)

    import whisper
    from whisper_transcribe import save_as_srt

    progress_pipe.send({"step": "loading", "message": f"加载 {model_name} 模型..."})
    model = whisper.load_model(model_name)

    progress_pipe.send({"step": "transcribing", "message": "转录中..."})
    result = model.transcribe(
        video_path,
        language=language,
        word_timestamps=True,
        verbose=False
    )

    segments = [{"start": s["start"], "end": s["end"], "text": s["text"].strip()}
                for s in result.get("segments", [])]
    save_as_srt(segments, srt_path)

    progress_pipe.send({"step": "done", "segment_count": len(segments)})

    # 保存转录元信息到临时 JSON，供主进程读取
    import json as _json
    with open(result_path, "w", encoding="utf-8") as f:
        _json.dump({"segment_count": len(segments)}, f)


def _run_transcribe_task(task_id: str, video_path_str: str, srt_path_str: str,
                         model_name: str, language: str, min_duration: float):
    """后台执行转录，Whisper 放入独立进程避免 GIL 阻塞事件循环"""
    import multiprocessing
    import time as _time

    def update(status, step, message):
        with _transcribe_lock:
            _transcribe_store[task_id] = {"status": status, "step": step, "total_steps": 4, "message": message}

    result_json_path = str(Path(video_path_str).with_suffix(".result.json"))

    try:
        update("processing", 1, "准备转录...")

        # 用 Pipe 从子进程接收进度
        parent_conn, child_conn = multiprocessing.Pipe(duplex=False)

        proc = multiprocessing.Process(
            target=_whisper_subprocess,
            args=(str(video_path_str), str(srt_path_str), model_name, language,
                  result_json_path, child_conn),
            daemon=True
        )
        proc.start()
        child_conn.close()  # 父端不写，关闭子端引用

        transcribe_start = 0
        while proc.is_alive():
            if parent_conn.poll(1):
                try:
                    msg = parent_conn.recv()
                    step = msg.get("step")
                    if step == "loading":
                        update("processing", 1, msg.get("message", "加载模型中..."))
                    elif step == "transcribing":
                        transcribe_start = _time.time()
                        update("processing", 2, "转录中，请耐心等待...")
                    elif step == "done":
                        break
                except (EOFError, OSError):
                    break
            else:
                # 无进度消息时显示已用时间
                if transcribe_start:
                    elapsed = int(_time.time() - transcribe_start)
                    mins, secs = elapsed // 60, elapsed % 60
                    update("processing", 2, f"转录中... 已用时 {mins}分{secs}秒")

        proc.join()

        if proc.exitcode != 0:
            raise RuntimeError(f"Whisper 进程异常退出 (code={proc.exitcode})")

        update("processing", 3, "解析生成的字幕...")

        subtitles = parse_srt(str(srt_path_str))
        original_count = len(subtitles)
        subtitles = filter_short_subtitles(subtitles, min_duration)

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

        with _transcribe_lock:
            _transcribe_store[task_id] = {
                "status": "completed",
                "step": 4,
                "total_steps": 4,
                "message": f"转录完成，共 {len(subtitle_items)} 条字幕",
                "result": {
                    "subtitles": [s.model_dump() for s in subtitle_items],
                    "total": original_count,
                    "filtered": len(subtitle_items)
                }
            }

    except Exception as e:
        with _transcribe_lock:
            _transcribe_store[task_id] = {
                "status": "error",
                "step": 0,
                "total_steps": 4,
                "message": f"转录失败: {str(e)}",
                "error": str(e)
            }

    finally:
        # 清理临时文件
        if Path(video_path_str).exists():
            Path(video_path_str).unlink(missing_ok=True)
        if Path(srt_path_str).exists():
            Path(srt_path_str).unlink(missing_ok=True)
        if Path(result_json_path).exists():
            Path(result_json_path).unlink(missing_ok=True)


@router.post("/transcribe")
async def transcribe_video_endpoint(
    video: UploadFile = File(...),
    min_duration: float = 1.0,
    language: Optional[str] = None,
    model_name: str = "base"
):
    """
    使用 Whisper 将视频转录为字幕（后台异步，通过 progress 端点轮询）
    """
    if not video.filename:
        raise HTTPException(status_code=400, detail="未提供视频文件")

    temp_dir = Path(__file__).parent.parent.parent / "temp"
    temp_dir.mkdir(exist_ok=True)

    video_path = temp_dir / f"transcribe_{video.filename}"
    srt_path = temp_dir / f"transcribe_{video.filename}.srt"

    with open(video_path, "wb") as f:
        shutil.copyfileobj(video.file, f)

    task_id = str(_uuid.uuid4())

    with _transcribe_lock:
        _transcribe_store[task_id] = {
            "status": "preparing",
            "step": 0,
            "total_steps": 4,
            "message": "准备转录..."
        }

    thread = _threading.Thread(
        target=_run_transcribe_task,
        args=(task_id, str(video_path), str(srt_path), model_name, language, min_duration),
        daemon=True
    )
    thread.start()

    return {"task_id": task_id, "status": "started"}


@router.get("/transcribe/progress/{task_id}")
async def transcribe_progress(task_id: str):
    """获取转录实时进度"""
    with _transcribe_lock:
        task = _transcribe_store.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return task


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

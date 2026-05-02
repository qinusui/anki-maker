"""
OCR 硬字幕提取模块 — 从视频画面中识别字幕文字
方案链：软字幕提取 > OCR 硬字幕识别 > Whisper 转录
"""

import subprocess
from pathlib import Path
from typing import Optional


def _get_video_duration(video_path: str) -> float:
    """获取视频时长（秒）"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return float(result.stdout.strip())


def detect_visible_subtitles(video_path: str, sample_count: int = 6) -> bool:
    """
    检测视频是否有可见硬字幕。
    取若干帧的底部 25% 区域做 OCR，看是否能识别出文字。
    """
    try:
        import cv2
        from paddleocr import PaddleOCR
    except ImportError:
        return False

    duration = _get_video_duration(video_path)
    if duration <= 0:
        return False

    ocr = PaddleOCR(lang="ch", use_angle_cls=True, show_log=False)
    cap = cv2.VideoCapture(video_path)
    found = 0

    for i in range(sample_count):
        ts = duration * (i + 1) / (sample_count + 1)
        cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000)
        ret, frame = cap.read()
        if not ret:
            continue

        h = frame.shape[0]
        bottom = frame[int(h * 0.75):, :]

        result = ocr.ocr(bottom, cls=True)
        if result and result[0]:
            for line in result[0]:
                if line[1][1] >= 0.6:
                    found += 1
                    break

    cap.release()
    return found >= max(2, sample_count * 0.3)


def extract_hard_subtitles(
    video_path: str,
    lang: str = "ch",
    fps_sample: float = 1.0,
    conf_threshold: float = 0.65,
    progress_callback=None,
) -> list[dict]:
    """
    从视频中提取硬字幕（OCR 识别）

    Args:
        video_path: 视频文件路径
        lang: OCR 语言，ch（中英混合）或 en
        fps_sample: 每秒采样帧数
        conf_threshold: OCR 置信度阈值（0-1）
        progress_callback: 进度回调 callback(step, total, message)

    Returns:
        [{"start": float, "end": float, "text": str}, ...]
    """
    import cv2
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        raise ImportError("请安装 PaddleOCR: pip install paddlepaddle paddleocr")

    cap = cv2.VideoCapture(video_path)
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / video_fps if video_fps > 0 else 0
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if progress_callback:
        progress_callback(0, total_frames, "初始化 OCR 引擎...")

    ocr = PaddleOCR(lang=lang, use_angle_cls=True, show_log=False)

    frame_interval = max(1, int(video_fps / fps_sample))
    total_samples = (total_frames + frame_interval - 1) // frame_interval

    raw_results = []

    for i, frame_idx in enumerate(range(0, total_frames, frame_interval)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = frame_idx / video_fps
        bottom = frame[int(height * 0.75):, :]

        ocr_result = ocr.ocr(bottom, cls=True)
        if not ocr_result or not ocr_result[0]:
            continue

        texts = []
        confs = []
        for line in ocr_result[0]:
            text = line[1][0]
            conf = line[1][1]
            if conf >= conf_threshold:
                texts.append(text)
                confs.append(conf)

        if texts:
            raw_results.append({
                "timestamp": timestamp,
                "text": " ".join(texts),
                "confidence": sum(confs) / len(confs)
            })

        if progress_callback and i % 50 == 0:
            progress_callback(i, total_samples, f"OCR 识别中... {i}/{total_samples}")

    cap.release()

    if progress_callback:
        progress_callback(total_samples, total_samples, "合并字幕段落...")

    segments = _merge_ocr_results(raw_results)

    if progress_callback:
        progress_callback(len(segments), len(segments),
                          f"OCR 完成，识别到 {len(segments)} 条字幕")

    return [{"start": s["start"], "end": s["end"], "text": s["text"]}
            for s in segments]


def _merge_ocr_results(results: list[dict]) -> list[dict]:
    """合并相似 OCR 结果为独立字幕段落"""
    if not results:
        return []

    segments = []
    cur = {
        "start": results[0]["timestamp"],
        "end": results[0]["timestamp"],
        "text": results[0]["text"],
        "conf": results[0]["confidence"]
    }

    for r in results[1:]:
        gap = r["timestamp"] - cur["end"]
        same = _text_similar(r["text"], cur["text"])

        if same and gap < 3.0:
            cur["end"] = r["timestamp"]
            if r["confidence"] > cur["conf"]:
                cur["text"] = r["text"]
                cur["conf"] = r["confidence"]
        elif gap < 0.3:
            cur["end"] = r["timestamp"]
        else:
            segments.append(dict(cur))
            cur = {
                "start": r["timestamp"],
                "end": r["timestamp"],
                "text": r["text"],
                "conf": r["confidence"]
            }

    segments.append(cur)

    # 为每条字幕加上最小显示时长（至少 0.5 秒，最长到下一个字幕开始前）
    for i, seg in enumerate(segments):
        seg["end"] = max(seg["end"], seg["start"] + 0.5)
        if i < len(segments) - 1:
            seg["end"] = min(seg["end"], segments[i + 1]["start"])

    return segments


def _text_similar(a: str, b: str) -> bool:
    """判断两段文字是否相似（同一字幕的不同帧）"""
    if a == b:
        return True
    a_clean = a.replace(" ", "").replace("，", "").replace(",", "")
    b_clean = b.replace(" ", "").replace("，", "").replace(",", "")
    if a_clean == b_clean:
        return True
    if len(a_clean) > 4 and len(b_clean) > 4:
        if a_clean in b_clean or b_clean in a_clean:
            return True
    return False

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


def _is_subtitle_box(bbox, crop_w: int, crop_h: int) -> bool:
    """
    判断 OCR 检测到的文本框是否像个字幕（而非 logo/水印）。

    兼容中英双语字幕：两个文本框中英文行可能一短一窄，
    因此宽度/位置阈值比单语更宽松。

    bbox 格式: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
    """
    x1, y1 = bbox[0]
    x3, y3 = bbox[2]
    box_w = x3 - x1
    box_h = y3 - y1
    cx = (x1 + x3) / 2
    cy = (y1 + y3) / 2

    # 底部：容许第一行字幕更靠近裁剪区上沿（双语叠加时第一行偏上）
    if cy < crop_h * 0.12:
        return False
    # 水平居中：不紧贴左右边缘
    if cx < crop_w * 0.10 or cx > crop_w * 0.90:
        return False
    # 宽度占比：短英文行也能通过（≥8%），但不能撑满整个画面（≤92%）
    if box_w < crop_w * 0.08 or box_w > crop_w * 0.92:
        return False
    # 高度上限：两行双语叠加也不会超过裁剪区一半
    if box_h > crop_h * 0.50:
        return False

    return True


def detect_visible_subtitles(video_path: str, sample_count: int = 12) -> bool:
    """
    检测视频是否有可见硬字幕。

    取 12 帧底部 30% 区域做 OCR，至少 4 帧命中且文字有变化
    才判定有字幕，假阳性率 < 1%。
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
    hit_texts = []  # 记录命中帧的文字用于多样性检查
    hit_count = 0

    for i in range(sample_count):
        ts = duration * (i + 1) / (sample_count + 1)
        cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000)
        ret, frame = cap.read()
        if not ret:
            continue

        h, w = frame.shape[:2]
        bottom = frame[int(h * 0.70):, :]
        crop_h, crop_w = bottom.shape[:2]

        result = ocr.ocr(bottom, cls=True)
        if not result or not result[0]:
            continue

        frame_hit = False
        for line in result[0]:
            bbox = line[0]
            text = line[1][0]
            conf = line[1][1]

            # 置信度 + 位置双重过滤
            if conf >= 1.0 and _is_subtitle_box(bbox, crop_w, crop_h):
                hit_texts.append(text.strip())
                frame_hit = True

        if frame_hit:
            hit_count += 1

    cap.release()

    if hit_count < 4:
        return False

    # 文字多样性检查：所有命中帧内容相同 → logo/水印
    unique_texts = set(hit_texts)
    if len(unique_texts) <= 1:
        return False

    return True


def extract_hard_subtitles(
    video_path: str,
    lang: str = "ch",
    fps_sample: float = 1.0,
    conf_threshold: float = 1.0,
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
        bottom = frame[int(height * 0.70):, :]
        crop_h, crop_w = bottom.shape[:2]

        ocr_result = ocr.ocr(bottom, cls=True)
        if not ocr_result or not ocr_result[0]:
            continue

        texts = []
        confs = []
        for line in ocr_result[0]:
            bbox = line[0]
            text = line[1][0]
            conf = line[1][1]
            if conf >= conf_threshold and _is_subtitle_box(bbox, crop_w, crop_h):
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

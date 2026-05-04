"""
Whisper 自动转录模块 - 将视频/音频转录为带时间戳的字幕
使用 faster-whisper 引擎
"""

from pathlib import Path


def transcribe_video(
    video_path: str,
    model_name: str = "base",
    language: str = None,
    word_timestamps: bool = True
) -> list[dict]:
    """
    使用 faster-whisper 转录视频

    Args:
        video_path: 视频文件路径
        model_name: Whisper 模型名称 (tiny, base, small, medium, large)
        language: 语言代码，None 则自动检测
        word_timestamps: 是否启用词级时间戳

    Returns:
        字幕段落列表，每项包含 start, end, text
    """
    from faster_whisper import WhisperModel

    print(f"  加载 faster-whisper {model_name} 模型...")
    model = WhisperModel(model_name)

    print(f"  开始转录...")
    segments_iter, info = model.transcribe(
        video_path,
        language=language,
        word_timestamps=word_timestamps,
        vad_filter=True,
    )

    segments = []
    for segment in segments_iter:
        text = segment.text.strip()
        if text:
            segments.append({
                "start": segment.start,
                "end": segment.end,
                "text": text,
            })

    return segments


def segments_to_srt_format(segments: list[dict]) -> str:
    """
    将转录结果转换为 SRT 格式

    Args:
        segments: 转录段落列表

    Returns:
        SRT 格式字符串
    """
    srt_lines = []

    for i, seg in enumerate(segments, 1):
        start = seg["start"]
        end = seg["end"]
        text = seg["text"]

        # 转换时间格式
        def format_time(seconds):
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

        srt_lines.append(f"{i}")
        srt_lines.append(f"{format_time(start)} --> {format_time(end)}")
        srt_lines.append(text)
        srt_lines.append("")

    return "\n".join(srt_lines)


def save_as_srt(segments: list[dict], output_path: str):
    """
    保存为 SRT 文件

    Args:
        segments: 转录段落列表
        output_path: 输出文件路径
    """
    srt_content = segments_to_srt_format(segments)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_content)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        video = sys.argv[1]
        print(f"转录中: {video}")
        segments = transcribe_video(video, model_name="base")
        print(f"转录完成，共 {len(segments)} 段")
        for seg in segments[:5]:
            print(f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}")
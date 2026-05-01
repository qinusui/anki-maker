"""
媒体切割模块 - 使用 ffmpeg 切割音频和截取视频截图
"""

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from dataclasses import dataclass


@dataclass
class MediaItem:
    """媒体条目"""
    index: int
    start_sec: float
    end_sec: float
    audio_path: str
    screenshot_path: str


def get_ffmpeg_path() -> str:
    """获取 ffmpeg 路径"""
    return "ffmpeg"  # 假设 ffmpeg 在 PATH 中


def cut_audio(
    video_path: str,
    start_sec: float,
    end_sec: float,
    output_path: str,
    quality: int = 2
) -> bool:
    """
    切割音频片段

    Args:
        video_path: 视频文件路径
        start_sec: 开始时间（秒）
        end_sec: 结束时间（秒）
        output_path: 输出路径
        quality: 音频质量 (0-9, 越小越好)

    Returns:
        是否成功
    """
    duration = end_sec - start_sec
    cmd = [
        get_ffmpeg_path(),
        "-y",  # 覆盖输出
        "-i", video_path,
        "-ss", f"{start_sec:.3f}",
        "-t", f"{duration:.3f}",
        "-vn",  # 不要视频
        "-acodec", "libmp3lame",
        "-q:a", str(quality),
        "-ar", "44100",  # 采样率
        output_path
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(30, duration * 2)
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def capture_screenshot(
    video_path: str,
    timestamp: float,
    output_path: str,
    quality: int = 2
) -> bool:
    """
    截取视频中间帧

    Args:
        video_path: 视频文件路径
        timestamp: 时间戳（秒）
        output_path: 输出路径
        quality: 图像质量 (1-31, 越小越好)

    Returns:
        是否成功
    """
    cmd = [
        get_ffmpeg_path(),
        "-y",
        "-i", video_path,
        "-ss", f"{timestamp:.3f}",
        "-vframes", "1",
        "-q:v", str(quality),
        "-update", "1",  # 覆盖输出
        output_path
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def process_media_items(
    video_path: str,
    items: list[dict],
    output_dir: str,
    num_workers: int = 8
) -> list[MediaItem]:
    """
    批量处理媒体条目

    Args:
        video_path: 视频文件路径
        items: 字幕数据列表，每项包含 start_sec, end_sec
        output_dir: 输出目录
        num_workers: 并行数

    Returns:
        MediaItem 列表
    """
    output_path = Path(output_dir)
    audio_dir = output_path / "audio"
    screenshot_dir = output_path / "screenshots"

    audio_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    results = []

    def process_single(item: dict) -> MediaItem | None:
        idx = item.get("index", 0)
        start = item["start_sec"]
        end = item["end_sec"]
        mid = (start + end) / 2  # 取中间帧

        audio_name = f"card_{idx:04d}.mp3"
        screenshot_name = f"card_{idx:04d}.jpg"

        audio_path = str(audio_dir / audio_name)
        screenshot_path = str(screenshot_dir / screenshot_name)

        # 切音频和截图可以并行
        audio_ok = cut_audio(video_path, start, end, audio_path)
        screenshot_ok = capture_screenshot(video_path, mid, screenshot_path)

        if audio_ok:
            return MediaItem(
                index=idx,
                start_sec=start,
                end_sec=end,
                audio_path=audio_path,
                screenshot_path=screenshot_path if screenshot_ok else ""
            )
        return None

    print(f"开始媒体处理，{len(items)} 条，{num_workers} 并发...")
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(process_single, item): item for item in items}

        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            if result:
                results.append(result)

            # 进度显示
            if i % 10 == 0 or i == len(items):
                print(f"  进度: {i}/{len(items)}")

    # 按 index 排序
    results.sort(key=lambda x: x.index)
    print(f"媒体处理完成，{len(results)} 条成功")

    return results


if __name__ == '__main__':
    # 测试
    import sys
    if len(sys.argv) > 1:
        video = sys.argv[1]
        print(f"测试截图: {capture_screenshot(video, 10.0, 'test.jpg')}")
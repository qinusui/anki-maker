"""
媒体切割模块 - 使用 ffmpeg 切割音频和截取视频截图
"""

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from dataclasses import dataclass

# Windows 命令行最大长度约 8191，保守取 7000 给其他参数留空间
_CMD_MAX_CHARS = 7000


@dataclass
class MediaItem:
    """媒体条目"""
    index: int
    start_sec: float
    end_sec: float
    audio_path: str
    screenshot_path: str


PADDING_START = 0.2  # 开头提前秒数
PADDING_END   = 0.2  # 结尾延后秒数


def get_ffmpeg_path() -> str:
    """获取 ffmpeg 路径"""
    return "ffmpeg"


def get_video_duration(video_path: str) -> float:
    """使用 ffprobe 获取视频时长（秒）"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return float(result.stdout.strip())


def apply_padding(items: list[dict], video_duration: float) -> list[dict]:
    """
    为每条字幕的音频切割添加头尾 Padding，避免开头结尾太突兀。
    保持原始 start_sec/end_sec 不变（用于卡片显示），
    新增 cut_start/cut_end 表示实际切割范围。
    """
    for i, item in enumerate(items):
        start = item["start_sec"]
        end = item["end_sec"]

        pad_start = start - PADDING_START
        pad_end   = end   + PADDING_END

        # 不超出视频边界
        pad_start = max(0.0, pad_start)
        pad_end   = min(video_duration, pad_end)

        # 不侵入前一句
        if i > 0:
            prev_end = items[i - 1]["end_sec"]
            pad_start = max(pad_start, prev_end)

        # 不侵入后一句
        if i < len(items) - 1:
            next_start = items[i + 1]["start_sec"]
            pad_end = min(pad_end, next_start)

        item["cut_start"] = pad_start
        item["cut_end"]   = pad_end
        # 截图取原始时间中点
        item["snapshot_time"] = (start + end) / 2

    return items


def extract_full_audio(video_path: str, output_path: str, quality: int = 2) -> bool:
    """从视频提取完整音轨（MP3），仅解码一次视频"""
    cmd = [
        get_ffmpeg_path(), "-y",
        "-i", video_path,
        "-vn", "-acodec", "libmp3lame",
        "-q:a", str(quality), "-ar", "44100",
        output_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def cut_audio(
    source_path: str,
    start_sec: float,
    end_sec: float,
    output_path: str,
    quality: int = 2
) -> bool:
    """
    从音/视频文件切割片段（-ss 在 -i 前，输入seek，速度快）

    Args:
        source_path: 音频或视频文件路径
        start_sec: 开始时间（秒）
        end_sec: 结束时间（秒）
        output_path: 输出路径
        quality: 音频质量 (0-9, 越小越好)
    """
    duration = end_sec - start_sec
    cmd = [
        get_ffmpeg_path(), "-y",
        "-ss", f"{start_sec:.3f}", "-t", f"{duration:.3f}",
        "-i", source_path,
        "-vn", "-acodec", "libmp3lame",
        "-q:a", str(quality), "-ar", "44100",
        output_path
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
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


def capture_screenshots_batch(
    video_path: str,
    timestamps: list[tuple[int, float]],  # [(index, timestamp), ...]
    output_dir: str,
    quality: int = 2
) -> dict[int, str]:
    """
    批量截取视频帧，使用 ffmpeg select filter 一次处理多帧。
    超长命令行自动分批。

    Args:
        video_path: 视频文件路径
        timestamps: (index, timestamp) 列表
        output_dir: 输出目录
        quality: 图像质量 (1-31, 越小越好)

    Returns:
        {index: screenshot_path} 字典
    """
    results = {}

    # 按时戳排序
    items = sorted(timestamps, key=lambda x: x[1])
    remaining = list(items)

    batch_idx = 0

    while remaining:
        # 构建 select 表达式，控制在命令行长度以内
        expr_parts = []
        batch = []

        for idx, ts in remaining:
            # 每个条件 ~25 字符，预留给其他参数的空间
            part = f"lt(abs(t-{ts:.3f}),0.05)"
            if sum(len(p) for p in expr_parts) + len(part) + len(expr_parts) + 500 > _CMD_MAX_CHARS:
                break
            expr_parts.append(part)
            batch.append((idx, ts))

        if not batch:
            break

        select_expr = "+".join(expr_parts)
        output_pattern = str(Path(output_dir) / f"_batch{batch_idx}_%03d.jpg")

        cmd = [
            get_ffmpeg_path(), "-y",
            "-i", video_path,
            "-vf", f"select='{select_expr}',setpts=N/FRAME_RATE/TB",
            "-vsync", "vfr",
            "-q:v", str(quality),
            output_pattern
        ]

        subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        # 匹配输出文件到 index
        for i, (idx, _ts) in enumerate(batch):
            src = Path(output_dir) / f"_batch{batch_idx}_{i+1:03d}.jpg"
            dst = Path(output_dir) / f"card_{idx:04d}.jpg"
            if src.exists():
                dst.unlink(missing_ok=True)
                src.rename(dst)
                results[idx] = str(dst)

        remaining = remaining[len(batch):]
        batch_idx += 1

    # 未成功截到图的，回退逐条截
    missing = [(idx, ts) for idx, ts in items if idx not in results]
    if missing:
        for idx, ts in missing:
            path = str(Path(output_dir) / f"card_{idx:04d}.jpg")
            if capture_screenshot(video_path, ts, path, quality):
                results[idx] = path

    return results


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

    # 获取视频时长并计算 padding
    video_duration = get_video_duration(video_path)
    items = apply_padding(items, video_duration)

    # Step 1: 提取完整音轨（视频只解码一次）
    full_audio_path = str(audio_dir / "_full.mp3")
    print(f"提取完整音轨...")
    if not extract_full_audio(video_path, full_audio_path):
        raise RuntimeError("提取音轨失败")

    # Step 2: 截图（≤100 条逐条并行，>100 条批量 select filter）
    BATCH_SS_THRESHOLD = 100
    ss_map = {}

    if len(items) > BATCH_SS_THRESHOLD:
        print(f"批量截图 {len(items)} 帧...")
        ts_list = [(item["index"], item["snapshot_time"]) for item in items]
        ss_map = capture_screenshots_batch(video_path, ts_list, str(screenshot_dir))
    else:
        print(f"逐条截图 {len(items)} 帧，{num_workers} 并发...")
        def _ss_single(item):
            idx = item["index"]
            path = str(screenshot_dir / f"card_{idx:04d}.jpg")
            ok = capture_screenshot(video_path, item["snapshot_time"], path)
            return (idx, path) if ok else (idx, "")
        with ThreadPoolExecutor(max_workers=num_workers) as ss_executor:
            for idx, path in ss_executor.map(_ss_single, items):
                if path:
                    ss_map[idx] = path
    print(f"截图完成: {len(ss_map)}/{len(items)}")

    # Step 3: 并行切音频
    print(f"开始音频切片，{len(items)} 条，{num_workers} 并发...")
    results = []

    def process_single(item: dict) -> MediaItem | None:
        idx = item.get("index", 0)
        cut_start = item["cut_start"]
        cut_end = item["cut_end"]

        audio_path = str(audio_dir / f"card_{idx:04d}.mp3")
        screenshot_path = ss_map.get(idx, "")

        if cut_audio(full_audio_path, cut_start, cut_end, audio_path):
            return MediaItem(
                index=idx,
                start_sec=item["start_sec"],
                end_sec=item["end_sec"],
                audio_path=audio_path,
                screenshot_path=screenshot_path
            )
        return None

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(process_single, item): item for item in items}

        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            if result:
                results.append(result)

            if i % 10 == 0 or i == len(items):
                print(f"  进度: {i}/{len(items)}")

    results.sort(key=lambda x: x.index)
    print(f"媒体处理完成，{len(results)} 条成功")

    return results


if __name__ == '__main__':
    # 测试
    import sys
    if len(sys.argv) > 1:
        video = sys.argv[1]
        print(f"测试截图: {capture_screenshot(video, 10.0, 'test.jpg')}")
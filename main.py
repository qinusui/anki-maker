"""
Anki 卡片生成器 - 主程序
将视频和字幕文件转换为可导入 Anki 的牌组
"""

import os
import sys
from pathlib import Path

from parse_srt import parse_srt, filter_short_subtitles, Subtitle
from ai_process import process_subtitles_with_ai
from media_cut import process_media_items
from pack_apkg import create_apkg


def run(
    video_path: str,
    subtitle_path: str = None,
    output_dir: str = "./output",
    api_key: str = None,
    min_duration: float = 1.0,
    num_workers: int = 8,
    whisper_model: str = "base",
    language: str = None,
    force_transcribe: bool = False
) -> dict:
    """
    运行完整流程

    Args:
        video_path: 视频文件路径
        subtitle_path: 字幕文件路径（可选，不提供则自动转录）
        output_dir: 输出目录
        api_key: DeepSeek API Key
        min_duration: 最短字幕时长（秒）
        num_workers: 并行处理数
        whisper_model: Whisper 模型 (tiny, base, small, medium, large)
        language: 视频语言代码，None 则自动检测
        force_transcribe: 强制使用 Whisper 转录（忽略已有字幕文件）

    Returns:
        dict: 包含 apkg_path, cards_count, processed 等信息
    """
    video_path = Path(video_path)
    subtitle_path = Path(subtitle_path) if subtitle_path else None
    output_dir = Path(output_dir)

    print("=" * 50)
    print("Anki 卡片生成器")
    print("=" * 50)
    print(f"视频: {video_path.name}")
    print(f"字幕: {subtitle_path.name if subtitle_path else '无（将自动转录）'}")
    print(f"输出: {output_dir}")
    print()

    # Step 0: 检查是否需要转录
    need_transcribe = force_transcribe or (subtitle_path is None or not subtitle_path.exists())

    if need_transcribe:
        print("[0/5] Whisper 自动转录...")
        from whisper_transcribe import transcribe_video, save_as_srt

        segments = transcribe_video(
            str(video_path),
            model_name=whisper_model,
            language=language
        )
        print(f"  转录完成，共 {len(segments)} 段")

        # 保存为 SRT 供后续使用
        temp_srt = output_dir / "temp_transcribed.srt"
        temp_srt.parent.mkdir(parents=True, exist_ok=True)
        save_as_srt(segments, str(temp_srt))
        subtitle_path = temp_srt

    # Step 1: 解析字幕
    print("[1/5] 解析字幕文件...")
    subtitles = parse_srt(subtitle_path)
    print(f"  共 {len(subtitles)} 条字幕")

    # 过滤过短字幕
    subtitles = filter_short_subtitles(subtitles, min_duration)
    print(f"  时长 >= {min_duration}s 的有 {len(subtitles)} 条")

    if not subtitles:
        raise ValueError("没有符合条件的字幕")

    # Step 2: AI 处理
    print("\n[2/5] 调用 DeepSeek AI 处理...")
    api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("需要设置 DEEPSEEK_API_KEY 环境变量或传入 api_key")

    processed = process_subtitles_with_ai(subtitles, api_key)

    if not processed:
        raise ValueError("AI 处理后没有保留的字幕")

    # Step 3: 媒体处理
    print("\n[3/5] 切割音频和截图...")
    media_items = process_media_items(
        str(video_path),
        processed,
        str(output_dir),
        num_workers=num_workers
    )

    # 合并数据
    for p, m in zip(processed, media_items):
        p["audio_path"] = m.audio_path
        p["screenshot_path"] = m.screenshot_path

    # Step 4: 打包
    print("\n[4/5] 打包 Anki 牌组...")
    audio_dir = output_dir / "audio"
    screenshot_dir = output_dir / "screenshots"

    apkg_path = create_apkg(
        video_path.stem,
        processed,
        str(output_dir),
        str(audio_dir),
        str(screenshot_dir)
    )

    # 完成
    print("\n[5/5] 完成!")
    print(f"牌组文件: {apkg_path}")
    print(f"卡片数量: {len(processed)}")

    return {
        "apkg_path": str(apkg_path),
        "cards_count": len(processed),
        "processed": processed
    }


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="Anki 卡片生成器")
    parser.add_argument("video", help="视频文件路径")
    parser.add_argument("subtitle", nargs="?", default=None, help="字幕文件路径（不提供则自动用 Whisper 转录）")
    parser.add_argument("output", nargs="?", default="./output", help="输出目录")
    parser.add_argument("--model", "-m", default="base", choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper 模型大小 (默认: base)")
    parser.add_argument("--language", "-l", default=None, help="视频语言代码，如 en, zh")
    parser.add_argument("--force-transcribe", "-t", action="store_true",
                        help="强制使用 Whisper 转录，忽略已有字幕")

    args = parser.parse_args()

    try:
        run(
            args.video,
            args.subtitle,
            args.output,
            whisper_model=args.model,
            language=args.language,
            force_transcribe=args.force_transcribe
        )
    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
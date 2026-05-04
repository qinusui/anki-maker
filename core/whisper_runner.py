"""
Whisper 独立转录脚本 - 供打包环境通过子进程调用系统 Python 运行
用法: python whisper_runner.py <video_path> <srt_path> <model_name> [language]
"""
import sys
import json
from pathlib import Path

# 确保能导入项目模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.whisper_transcribe import transcribe_video, save_as_srt


def main():
    if len(sys.argv) < 4:
        print("Usage: python whisper_runner.py <video_path> <srt_path> <model_name> [language]")
        sys.exit(1)

    video_path = sys.argv[1]
    srt_path = sys.argv[2]
    model_name = sys.argv[3]
    language = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "None" else None

    print(json.dumps({"step": "loading", "message": f"加载 {model_name} 模型..."}))
    sys.stdout.flush()

    segments = transcribe_video(video_path, model_name=model_name, language=language)

    save_as_srt(segments, srt_path)

    print(json.dumps({"step": "done", "segment_count": len(segments)}))
    sys.stdout.flush()


if __name__ == "__main__":
    main()

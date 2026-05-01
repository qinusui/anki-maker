"""
Gradio Web UI - 可视化选择要导出的句子
"""

import gradio as gr
from pathlib import Path

from parse_srt import parse_srt, filter_short_subtitles
from main import run as process_cards

_subtitles_cache = []


def load_subtitles(video_path, subtitle_path, min_duration):
    """加载字幕"""
    global _subtitles_cache
    _subtitles_cache = []

    if not subtitle_path:
        return None, "请提供字幕文件"

    if not Path(subtitle_path).exists():
        return None, f"文件不存在"

    try:
        subtitles = parse_srt(subtitle_path)
        subtitles = filter_short_subtitles(subtitles, min_duration)
        _subtitles_cache = subtitles

        # 返回 list of [checked, text, start, end]
        rows = [[True, sub.text, round(sub.start_sec, 2), round(sub.end_sec, 2)] for sub in subtitles]

        return rows, f"加载了 {len(rows)} 条字幕 (默认全选)"

    except Exception as e:
        return None, f"加载失败: {e}"


def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def do_process(table_data, video_path, subtitle_path, output_dir):
    """处理选中的句子"""
    global _subtitles_cache

    print(f"[DEBUG] video_path: {video_path}")
    print(f"[DEBUG] subtitle_path: {subtitle_path}")
    print(f"[DEBUG] output_dir: {output_dir}")
    print(f"[DEBUG] table_data: {table_data}")
    print(f"[DEBUG] _subtitles_cache: {len(_subtitles_cache)} items")

    if not video_path:
        yield "请上传视频文件"
        return

    if not subtitle_path:
        yield "请上传字幕文件"
        return

    if table_data is None:
        yield "请先加载字幕"
        return

    try:
        # 解析 table_data（可能是 list of lists 或 list of dicts）
        selected_texts = []
        if isinstance(table_data, list):
            for item in table_data:
                if isinstance(item, list) and len(item) >= 2:
                    if item[0]:  # checkbox
                        selected_texts.append(item[1])  # text
                elif isinstance(item, dict):
                    if item.get("选择", item.get("checked", True)):
                        selected_texts.append(item.get("原文", item.get("text", "")))

        print(f"[DEBUG] selected_texts: {len(selected_texts)}")

        if not selected_texts:
            yield "没有选中的句子"
            return

        yield f"正在处理 {len(selected_texts)} 条..."

        # 通过原文匹配字幕
        selected_indices = set()
        for text in selected_texts:
            for sub in _subtitles_cache:
                if sub.text == text:
                    selected_indices.add(sub.index)
                    break

        print(f"[DEBUG] matched indices: {selected_indices}")

        if not selected_indices:
            yield "匹配失败，没有选中句子"
            return

        all_subs = parse_srt(subtitle_path)
        selected = [s for s in all_subs if s.index in selected_indices]

        print(f"[DEBUG] selected subtitles: {len(selected)}")

        yield f"已选择 {len(selected)} 条..."

        output_path = Path(output_dir) if output_dir else Path("./output")
        output_path.mkdir(parents=True, exist_ok=True)

        temp_srt = output_path / "temp_selected.srt"
        with open(temp_srt, "w", encoding="utf-8") as f:
            for sub in selected:
                f.write(f"{sub.index}\n{format_time(sub.start_sec)} --> {format_time(sub.end_sec)}\n{sub.text}\n\n")

        yield "正在 AI 筛选..."
        yield "正在切割媒体..."
        yield "正在打包..."

        result = process_cards(video_path, str(temp_srt), str(output_path))
        yield f"完成: {result}"

    except Exception as e:
        import traceback
        traceback.print_exc()
        yield f"失败: {e}"


def build_ui():
    with gr.Blocks(title="Anki 卡片生成器") as app:

        gr.Markdown("# Anki 卡片生成器\n辅助学习英语")

        with gr.Row():
            video_file = gr.File(label="视频", file_types=[".mp4", ".mkv", ".avi"])
            subtitle_file = gr.File(label="字幕", file_types=[".srt"])

        with gr.Row():
            min_dur = gr.Slider(0.5, 5, value=1.0, step=0.5, label="最短时长(秒)")
            load_btn = gr.Button("加载", variant="primary")

        status = gr.Textbox(label="状态", lines=1)

        table = gr.DataFrame(
            headers=["选择", "原文", "开始(s)", "结束(s)"],
            datatype=["bool", "str", "number", "number"],
            interactive=True,
            visible=False
        )

        output_path = gr.Textbox(value="./output", label="输出目录")
        process_btn = gr.Button("处理选中", variant="primary", size="lg")
        result = gr.Textbox(label="结果", lines=5, visible=False)

        # 事件绑定
        load_btn.click(
            load_subtitles,
            [video_file, subtitle_file, min_dur],
            [table, status]
        ).then(
            lambda: gr.update(visible=True),
            outputs=[table]
        )

        process_btn.click(
            do_process,
            [table, video_file, subtitle_file, output_path],
            [result]
        )

    return app


if __name__ == "__main__":
    build_ui().launch(server_name="0.0.0.0", server_port=7860, inbrowser=True)
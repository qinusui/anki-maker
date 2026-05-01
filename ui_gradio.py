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
        return None, "请提供字幕文件", ""

    if not Path(subtitle_path).exists():
        return None, f"文件不存在: {subtitle_path}", ""

    try:
        subtitles = parse_srt(subtitle_path)
        subtitles = filter_short_subtitles(subtitles, min_duration)
        _subtitles_cache = subtitles

        rows = [[True, sub.text, round(sub.start_sec, 2), round(sub.end_sec, 2)] for sub in subtitles]

        return rows, f"加载了 {len(rows)} 条字幕", f"已选择: {len(rows)} 条"

    except Exception as e:
        return None, f"加载失败: {e}", ""


def select_all(table_data):
    if table_data is None:
        return None
    return [[True] + row[1:] for row in table_data]


def deselect_all(table_data):
    if table_data is None:
        return None
    return [[False] + row[1:] for row in table_data]


def count_selected(table_data):
    if table_data is None:
        return "已选择: 0 条"
    return f"已选择: {sum(1 for row in table_data if row[0])} 条"


def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def do_process(table_data, video_path, subtitle_path, output_dir):
    """处理选中的句子"""
    global _subtitles_cache

    if not video_path:
        yield "请上传视频文件"
        return

    if not subtitle_path or not Path(subtitle_path).exists():
        yield "请上传字幕文件"
        return

    if table_data is None or len(table_data) == 0:
        yield "请先加载字幕"
        return

    try:
        # 获取选中的字幕索引
        selected_indices = set()
        for i, row in enumerate(table_data):
            if row[0] and i < len(_subtitles_cache):
                selected_indices.add(_subtitles_cache[i].index)

        if not selected_indices:
            yield "没有选中的句子"
            return

        all_subs = parse_srt(subtitle_path)
        selected = [s for s in all_subs if s.index in selected_indices]

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
        selected_count = gr.Textbox(label="已选择", lines=1)

        table = gr.DataFrame(
            headers=["选择", "原文", "开始(s)", "结束(s)"],
            datatype=["bool", "str", "number", "number"],
            interactive=True,
            visible=False
        )

        with gr.Row():
            all_btn = gr.Button("全选")
            none_btn = gr.Button("取消全选")

        output_path = gr.Textbox(value="./output", label="输出目录")
        process_btn = gr.Button("处理选中", variant="primary", size="lg")
        result = gr.Textbox(label="结果", lines=3, visible=False)

        # 事件绑定
        load_btn.click(
            load_subtitles,
            [video_file, subtitle_file, min_dur],
            [table, status, selected_count]
        ).then(
            lambda: gr.update(visible=True),
            outputs=[table]
        )

        all_btn.click(select_all, [table], [table])
        none_btn.click(deselect_all, [table], [table])
        table.change(count_selected, [table], [selected_count])

        process_btn.click(
            do_process,
            [table, video_file, subtitle_file, output_path],
            [result]
        )

    return app


if __name__ == "__main__":
    build_ui().launch(server_name="0.0.0.0", server_port=7860, inbrowser=True)
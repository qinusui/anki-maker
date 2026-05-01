"""
Gradio Web UI - 可视化选择要导出的句子
"""

import gradio as gr
from pathlib import Path
import json
import os

from parse_srt import parse_srt, filter_short_subtitles, Subtitle
from main import run as process_cards


def load_subtitles(video_path: str, subtitle_path: str, min_duration: float = 1.0):
    """加载字幕并在表格中显示"""
    if not subtitle_path:
        return None, "请提供字幕文件路径"

    if not Path(subtitle_path).exists():
        return None, f"字幕文件不存在: {subtitle_path}"

    try:
        subtitles = parse_srt(subtitle_path)
        subtitles = filter_short_subtitles(subtitles, min_duration)

        rows = []
        for sub in subtitles:
            rows.append([
                True,  # 选择
                sub.index,
                round(sub.start_sec, 2),
                round(sub.end_sec, 2),
                round(sub.end_sec - sub.start_sec, 2),
                sub.text
            ])

        return rows, f"共加载 {len(rows)} 条字幕"
    except Exception as e:
        return None, f"加载失败: {e}"


def process_selected(
    video_path: str,
    subtitle_path: str,
    table_data,
    output_dir: str
):
    """处理选中的句子，生成 Anki 牌组"""
    if not video_path or not subtitle_path or not table_data:
        yield "请先加载视频和字幕"
        return

    if not Path(video_path).exists():
        yield f"视频文件不存在: {video_path}"
        return

    try:
        yield "正在解析选中句子..."
        # 从 table_data 提取选中的字幕索引
        selected_indices = set()
        for row in table_data:
            if row[0]:  # 选择列
                selected_indices.add(int(row[1]))  # 序号列

        # 解析字幕并过滤
        all_subtitles = parse_srt(subtitle_path)
        selected_subtitles = [s for s in all_subtitles if s.index in selected_indices]

        if not selected_subtitles:
            yield "没有选中的句子"
            return

        yield f"选中 {len(selected_subtitles)} 条，开始处理..."
        yield f"正在 AI 筛选..."
        yield f"正在切割媒体..."
        yield f"正在打包..."

        # 调用 main.py 的处理逻辑
        output_dir_path = Path(output_dir) if output_dir else Path("./output")

        # 保存临时字幕文件（只包含选中的）
        temp_srt = output_dir_path / "temp_selected.srt"
        with open(temp_srt, "w", encoding="utf-8") as f:
            for sub in selected_subtitles:
                start = format_time(sub.start_sec)
                end = format_time(sub.end_sec)
                f.write(f"{sub.index}\n{start} --> {end}\n{sub.text}\n\n")

        # 处理
        result_path = process_cards(
            video_path,
            str(temp_srt),
            str(output_dir_path)
        )

        yield f"完成！牌组已生成: {result_path}"

    except Exception as e:
        yield f"处理失败: {e}"


def format_time(seconds: float) -> str:
    """将秒数转为 SRT 时间格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def toggle_all(table_data, select: bool):
    """全选/取消全选"""
    if table_data is None:
        return None
    for row in table_data:
        row[0] = select
    return table_data


def create_ui():
    """创建 Gradio 界面"""

    with gr.Blocks(title="Anki 卡片生成器") as app:
        gr.Markdown("# Anki 卡片生成器\n辅助学习英语 - 智能筛选有价值的句子")

        with gr.Row():
            with gr.Column(scale=1):
                video_input = gr.File(label="视频文件", file_types=[".mp4", ".mkv", ".avi"])
                subtitle_input = gr.File(label="字幕文件", file_types=[".srt"])
                min_duration = gr.Slider(0.5, 5, value=1.0, step=0.5, label="最短时长(秒)")
                load_btn = gr.Button("加载字幕", variant="primary")

            with gr.Column(scale=2):
                output_msg = gr.Textbox(label="状态", lines=1)
                subtitles_table = gr.DataFrame(
                    headers=["选择", "序号", "开始(s)", "结束(s)", "时长(s)", "原文"],
                    datatype=["bool", "number", "number", "number", "number", "str"],
                    interactive=True,
                    visible=False,
                    wrap=True
                )

        with gr.Row():
            select_all_btn = gr.Button("全选")
            deselect_all_btn = gr.Button("取消全选")

        with gr.Row():
            output_dir = gr.Textbox(value="./output", label="输出目录")

        with gr.Row():
            process_btn = gr.Button("处理选中的句子", variant="primary", size="lg")
            process_status = gr.Textbox(label="处理进度", lines=5, visible=False)

        # 事件绑定
        load_btn.click(
            fn=load_subtitles,
            inputs=[video_input, subtitle_input, min_duration],
            outputs=[subtitles_table, output_msg]
        ).then(
            fn=lambda: gr.update(visible=True),
            outputs=[subtitles_table]
        )

        select_all_btn.click(
            fn=lambda t: toggle_all(t, True),
            inputs=[subtitles_table],
            outputs=[subtitles_table]
        )

        deselect_all_btn.click(
            fn=lambda t: toggle_all(t, False),
            inputs=[subtitles_table],
            outputs=[subtitles_table]
        )

        process_btn.click(
            fn=process_selected,
            inputs=[video_input, subtitle_input, subtitles_table, output_dir],
            outputs=[process_status]
        )

    return app


if __name__ == "__main__":
    app = create_ui()
    app.launch(server_name="0.0.0.0", server_port=7860)
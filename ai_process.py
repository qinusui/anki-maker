"""
AI 批量处理模块 - 调用 DeepSeek API 进行翻译和注释
"""

import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# 加载 .env 配置
load_dotenv()


class AIProcessor:
    """AI 处理器"""

    SYSTEM_PROMPT = """你是英语学习教材编写专家。为输入的字幕列表的每一条提供中文翻译和知识点注释。

返回格式（JSON对象）：
{"items": [{"index": 数字, "include": true, "translation": "中文翻译", "notes": "重点词汇-释义"}, ...]}

注意：
- 必须返回一个 JSON 对象，items 是数组
- 每条字幕都必须保留，include 始终为 true
- translation 和 notes 必填，不可为空
- 保持原文顺序输出，每条都必须有 index 字段"""

    def __init__(self, api_key: str = None, base_url: str = None, model_name: str = None):
        """
        初始化 AI 处理器

        Args:
            api_key: API Key，默认从环境变量读取
            base_url: API 地址，默认 https://api.deepseek.com
            model_name: 模型名称，默认 deepseek-chat
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("需要设置 DEEPSEEK_API_KEY 环境变量或在 .env 文件中配置")
        self.client = OpenAI(api_key=self.api_key, base_url=base_url or "https://api.deepseek.com")
        self.model_name = model_name or "deepseek-chat"

    def process_batch(self, subtitles: list[dict], batch_size: int = 30, system_prompt: str = None) -> list[dict]:
        """
        批量处理字幕

        Args:
            subtitles: 字幕列表，每项包含 index, start_sec, end_sec, text
            batch_size: 每批处理数量
            system_prompt: 自定义系统提示词，默认使用 SYSTEM_PROMPT

        Returns:
            处理结果列表
        """
        results = []
        total_batches = (len(subtitles) + batch_size - 1) // batch_size

        for i in range(0, len(subtitles), batch_size):
            batch = subtitles[i:i + batch_size]
            batch_num = i // batch_size + 1
            print(f"  处理第 {batch_num}/{total_batches} 批 ({len(batch)} 条)...")

            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt or self.SYSTEM_PROMPT},
                        {"role": "user", "content": json.dumps(batch, ensure_ascii=False)}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2,
                )

                content = response.choices[0].message.content
                parsed = json.loads(content)

                # 处理可能返回的是 {"items": [...]} 或直接是数组
                if isinstance(parsed, dict):
                    if "items" in parsed:
                        results.extend(parsed["items"])
                    elif "results" in parsed:
                        results.extend(parsed["results"])
                    else:
                        # 尝试找第一个数组值
                        for v in parsed.values():
                            if isinstance(v, list):
                                results.extend(v)
                                break
                elif isinstance(parsed, list):
                    results.extend(parsed)

            except Exception as e:
                print(f"    批次处理失败: {e}")
                # 失败的批次标记为 skip
                for _ in batch:
                    results.append({"skip": True})

        return results


def process_subtitles_with_ai(subtitles: list, api_key: str = None,
                              api_base: str = None, model_name: str = None) -> list[dict]:
    """
    批量处理字幕列表

    Args:
        subtitles: Subtitle 对象列表
        api_key: API Key
        api_base: API 地址（可选）
        model_name: 模型名称（可选）

    Returns:
        处理后的完整数据列表
    """
    processor = AIProcessor(api_key, api_base, model_name)

    # 转换为 dict 列表
    subtitle_dicts = [
        {
            "index": s.index,
            "start_sec": s.start_sec,
            "end_sec": s.end_sec,
            "text": s.text
        }
        for s in subtitles
    ]

    print(f"开始 AI 处理，共 {len(subtitle_dicts)} 条字幕...")
    results = processor.process_batch(subtitle_dicts)

    # 合并原数据和 AI 结果（保留所有句子，仅添加注释）
    processed = []
    for i, sub in enumerate(subtitle_dicts):
        result = results[i] if i < len(results) and isinstance(results[i], dict) else {}
        processed.append({
            "index": sub["index"],
            "start_sec": sub["start_sec"],
            "end_sec": sub["end_sec"],
            "text": sub["text"],
            "translation": result.get("translation", ""),
            "notes": result.get("notes", ""),
            "reason": result.get("reason", "")
        })

    print(f"AI 注释完成，共 {len(processed)} 条")

    return processed


if __name__ == '__main__':
    # 测试
    import os
    os.environ["DEEPSEEK_API_KEY"] = "test-key"
    processor = AIProcessor()
    print("AIProcessor 已初始化")
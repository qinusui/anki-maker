"""
卡片相关 API
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import List, Optional
import sqlite3
import json

from models.schemas import ProcessedCard

router = APIRouter()


@router.get("/list")
async def list_cards(apkg_path: str):
    """
    列出 .apkg 文件中的卡片

    Args:
        apkg_path: .apkg 文件路径

    Returns:
        卡片列表
    """
    apkg_file = Path(apkg_path)

    if not apkg_file.exists():
        raise HTTPException(status_code=404, detail="APKG 文件不存在")

    try:
        # .apkg 文件实际上是 zip 文件，包含 .anki2 SQLite 数据库
        import zipfile
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as temp_dir:
            # 解压文件
            with zipfile.ZipFile(apkg_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # 查找 .anki2 文件
            anki_files = list(Path(temp_dir).glob("*.anki2"))

            if not anki_files:
                return {"cards": []}

            db_path = anki_files[0]

            # 连接数据库并读取卡片
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询卡片数据
            cursor.execute("""
                SELECT cards.id, cards.note_id, notes.flds
                FROM cards
                JOIN notes ON cards.note_id = notes.id
                ORDER BY cards.ord
            """)

            cards = []
            for row in cursor.fetchall():
                # 字段通常用 \x1f 分隔
                fields = row['flds'].split('\x1f')

                card = {
                    "id": row['id'],
                    "note_id": row['note_id'],
                    "fields": fields
                }
                cards.append(card)

            conn.close()

            return {"cards": cards, "total": len(cards)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取卡片失败: {str(e)}")


@router.post("/preview")
async def preview_cards(cards: List[ProcessedCard]):
    """
    预览卡片（前端传入数据，后端不做处理）

    Args:
        cards: 卡片列表

    Returns:
        预览HTML
    """
    html = """
    <div style="padding: 20px; font-family: Arial, sans-serif;">
    """

    for idx, card in enumerate(cards[:10]):  # 只预览前10张
        html += f"""
        <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
            <h3 style="margin: 0 0 12px 0; color: #333;">卡片 #{idx + 1}</h3>
            <div style="margin-bottom: 12px;">
                <strong>原文：</strong>
                <p style="margin: 4px 0; color: #666;">{card.sentence}</p>
            </div>
            <div style="margin-bottom: 12px;">
                <strong>翻译：</strong>
                <p style="margin: 4px 0; color: #666;">{card.translation}</p>
            </div>
            <div>
                <strong>词汇注释：</strong>
                <p style="margin: 4px 0; color: #666; white-space: pre-line;">{card.notes}</p>
            </div>
        </div>
        """

    if len(cards) > 5:
        html += f"<p style='text-align: center; color: #888;'>... 还有 {len(cards) - 5} 张卡片</p>"

    html += "</div>"

    return {"html": html}


@router.get("/download/{filename}")
async def download_card_file(filename: str):
    """
    下载生成的文件

    Args:
        filename: 文件名

    Returns:
        文件
    """
    # 这个路由已经在 main.py 中实现，这里保留作为文档说明
    pass

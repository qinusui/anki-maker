"""
学习进度追踪 - SQLite 持久化已学单词
"""

import sqlite3
import threading
from pathlib import Path

# 数据库路径：~/.cliplingo/progress.db
_DB_DIR = Path.home() / ".cliplingo"
_DB_PATH = _DB_DIR / "progress.db"
_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """建表（幂等）"""
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learned_words (
                word TEXT PRIMARY KEY,
                definition TEXT,
                source_video TEXT,
                learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def get_learned_words() -> dict[str, str]:
    """返回 {word_lower: definition}"""
    init_db()
    with _get_conn() as conn:
        rows = conn.execute("SELECT word, definition FROM learned_words").fetchall()
    return {row[0]: row[1] or "" for row in rows}


def mark_words_learned(words: list[dict], source_video: str = ""):
    """
    批量写入已学单词
    words: [{"word": "abandon", "definition": "放弃"}, ...]
    """
    if not words:
        return
    init_db()
    with _lock:
        with _get_conn() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO learned_words (word, definition, source_video) VALUES (?, ?, ?)",
                [(w["word"].strip().lower(), w.get("definition", ""), source_video) for w in words if w.get("word")]
            )


def get_learned_count() -> int:
    """统计已学单词数"""
    init_db()
    with _get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) FROM learned_words").fetchone()
    return row[0]

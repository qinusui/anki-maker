"""
打包模块 - 使用 genanki 生成可导入 Anki 的 .apkg 文件
"""

import genanki
import hashlib
import os
from pathlib import Path
from dataclasses import dataclass


@dataclass
class CardData:
    """卡片数据"""
    index: int
    sentence: str
    translation: str
    notes: str
    audio_path: str
    screenshot_path: str
    word: str = ""
    definition: str = ""


def generate_model_id(name: str) -> int:
    """根据名称生成稳定的模型 ID"""
    hash_val = hashlib.md5(name.encode()).digest()
    return int.from_bytes(hash_val[:4], 'big') & 0x7FFFFFFF


# ── 统一样式 ──────────────────────────────────────────────
_CSS = """\
.card {
  font-family: system-ui, -apple-system, sans-serif;
  font-size: 18px;
  text-align: center;
  color: #2c3e50;
  background-color: #f8f9fa;
  margin: 0;
  padding: 10px;
}
.container { max-width: 600px; margin: 0 auto; }
.image-box img {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  margin-bottom: 10px;
}
/* ── 句型卡 ── */
.original { font-weight: 600; font-size: 1.2em; color: #000; margin-top: 15px; }
.translation { color: #666; font-size: 0.95em; margin-top: 8px; }
.notes {
  text-align: left;
  background: #fff;
  border-left: 4px solid #007bff;
  padding: 10px;
  margin-top: 15px;
  font-size: 0.9em;
  border-radius: 4px;
  white-space: pre-line;
}
/* ── 词汇卡 ── */
.target-word {
  font-size: 2.5em;
  font-weight: 800;
  color: #007bff;
  margin: 40px 0 10px 0;
}
.word-meaning {
  font-size: 1.4em;
  color: #28a745;
  font-weight: 500;
  margin-bottom: 20px;
}
.hint {
  color: #999;
  font-size: 0.85em;
  margin-top: 20px;
}
.example-box {
  background: #f0f2f5;
  padding: 15px;
  border-radius: 12px;
  text-align: left;
  margin-top: 15px;
}
.example-box .tag {
  display: inline-block;
  font-size: 0.7em;
  padding: 2px 8px;
  background: #6c757d;
  color: white;
  border-radius: 4px;
  margin-bottom: 8px;
}
.example-box .image-box img {
  width: 100%;
  height: auto;
  border-radius: 8px;
}
.example-box .original {
  font-weight: 600;
  font-size: 1em;
  color: #333;
  margin: 8px 0;
}
/* ── 夜间模式 ── */
.nightMode .card { background-color: #1e1e1e; color: #eee; }
.nightMode .translation { color: #aaa; }
.nightMode .notes { background: #2d2d2d; border-left-color: #375a7f; }
.nightMode .target-word { color: #4da6ff; }
.nightMode .word-meaning { color: #5cb85c; }
.nightMode .hint { color: #666; }
.nightMode .example-box { background: #2d2d2d; }
.nightMode .example-box .original { color: #ccc; }"""

# ── 句型卡模板 ──────────────────────────────────────────
_SENTENCE_FRONT = """\
<div class="container">
  <div class="image-box">{{Screenshot}}</div>
  <div class="audio-box">{{Audio}}</div>
</div>"""

_SENTENCE_BACK = """\
<div class="container">
  <div class="image-box">{{Screenshot}}</div>
  <hr id="answer">
  <div class="text-content">
    <div class="original">{{Sentence}}</div>
    {{#Translation}}
    <div class="translation">{{Translation}}</div>
    {{/Translation}}
    {{#Notes}}
    <div class="notes">{{Notes}}</div>
    {{/Notes}}
  </div>
</div>"""

# ── 词汇卡模板 ──────────────────────────────────────────
_VOCAB_FRONT = """\
<div class="container">
  <div class="target-word">{{Word}}</div>
  <div class="hint">试着回想这个词在视频里的意思</div>
</div>"""

_VOCAB_BACK = """\
<div class="container">
  <div class="target-word">{{Word}}</div>
  {{#Definition}}
  <div class="word-meaning">{{Definition}}</div>
  {{/Definition}}

  <hr id="answer">

  <div class="example-box">
    <div class="tag">CONTEXT / 例句</div>
    {{#Screenshot}}
    <div class="image-box">{{Screenshot}}</div>
    {{/Screenshot}}
    <div class="original">{{Sentence}}</div>
    <div class="audio-box">{{Audio}}</div>
  </div>
</div>"""


def _create_model(model_id: int, name: str, templates: list[dict]) -> genanki.Model:
    """创建统一字段的 Anki 模型"""
    return genanki.Model(
        model_id=model_id,
        name=name,
        fields=[
            {'name': 'Screenshot'},
            {'name': 'Audio'},
            {'name': 'Sentence'},
            {'name': 'Translation'},
            {'name': 'Notes'},
            {'name': 'Word'},
            {'name': 'Definition'},
        ],
        templates=templates,
        css=_CSS
    )


def create_deck(
    deck_name: str,
    cards: list[CardData],
    card_styles: list[str] = None,
    audio_dir: str = None,
    screenshot_dir: str = None
) -> genanki.Deck:
    """
    创建 Anki 牌组

    Args:
        deck_name: 牌组名称
        cards: 卡片数据列表
        card_styles: 卡片样式列表，如 ["sentence"]、["vocab"]、["sentence", "vocab"]
        audio_dir: 音频目录
        screenshot_dir: 截图目录

    Returns:
        genanki.Deck 对象
    """
    if card_styles is None:
        card_styles = ["sentence"]

    # 根据选中的样式构建模板列表
    templates = []
    if "sentence" in card_styles:
        templates.append({'name': '句型卡', 'qfmt': _SENTENCE_FRONT, 'afmt': _SENTENCE_BACK})
    if "vocab" in card_styles:
        templates.append({'name': '词汇卡', 'qfmt': _VOCAB_FRONT, 'afmt': _VOCAB_BACK})

    if not templates:
        templates.append({'name': '句型卡', 'qfmt': _SENTENCE_FRONT, 'afmt': _SENTENCE_BACK})

    model = _create_model(
        generate_model_id("ClipLingo_" + deck_name),
        'ClipLingo',
        templates
    )

    deck = genanki.Deck(
        deck_id=generate_model_id(deck_name),
        name=deck_name
    )

    for card in cards:
        audio_name = os.path.basename(card.audio_path) if card.audio_path else ""
        screenshot_name = os.path.basename(card.screenshot_path) if card.screenshot_path else ""
        screenshot_field = f'<img src="{screenshot_name}">' if screenshot_name else ""
        audio_field = f'[sound:{audio_name}]' if audio_name else ""
        word = card.word or card.sentence  # 降级：无单词时用整句

        note = genanki.Note(
            model=model,
            fields=[
                screenshot_field,   # Screenshot
                audio_field,        # Audio
                card.sentence,      # Sentence
                card.translation,   # Translation
                card.notes,         # Notes
                word,               # Word
                card.definition,    # Definition
            ]
        )
        deck.add_note(note)

    return deck


def save_deck_with_media(
    deck: genanki.Deck,
    output_path: str,
    audio_files: list[str] = None,
    screenshot_files: list[str] = None,
    audio_dir: str = None,
    screenshot_dir: str = None
):
    """
    保存牌组并打包媒体文件

    Args:
        deck: genanki.Deck 对象
        output_path: 输出 .apkg 路径
        audio_files: 音频文件列表（完整路径）
        screenshot_files: 截图文件列表（完整路径）
        audio_dir: 音频源目录
        screenshot_dir: 截图源目录
    """
    # 创建临时目录存放媒体文件
    import tempfile
    import shutil

    temp_dir = Path(tempfile.mkdtemp())
    print(f"创建临时目录: {temp_dir}")

    # 复制媒体文件到临时目录
    copied_files = []

    def copy_to_media(filename: str, source_dir: str = None) -> str:
        if not filename:
            return None
        if source_dir:
            source = Path(source_dir) / filename
        else:
            source = Path(filename)

        if source.exists():
            dest = temp_dir / Path(filename).name
            shutil.copy2(source, dest)
            copied_files.append(str(dest))
            print(f"复制文件: {source} -> {dest}")
            return str(Path(filename).name)
        else:
            print(f"文件不存在: {source}")
            return None

    # 处理音频文件
    if audio_files:
        print(f"音频文件: {audio_files}")
        for af in audio_files:
            copy_to_media(os.path.basename(af), audio_dir)

    # 处理截图文件
    if screenshot_files:
        print(f"截图文件: {screenshot_files}")
        for sf in screenshot_files:
            copy_to_media(os.path.basename(sf), screenshot_dir)

    print(f"复制的媒体文件: {copied_files}")

    # 写入包文件
    package = genanki.Package(deck)
    package.media_files = copied_files

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    print(f"保存到: {output}")
    package.write_to_file(str(output))

    # 清理临时目录
    shutil.rmtree(temp_dir, ignore_errors=True)
    print(f"清理临时目录: {temp_dir}")


def create_apkg(
    video_name: str,
    cards: list[dict],
    output_dir: str,
    audio_dir: str,
    screenshot_dir: str,
    card_styles: list[str] = None
) -> str:
    """
    创建完整的 .apkg 文件

    Args:
        video_name: 视频名称（用于牌组名）
        cards: 卡片数据列表
        output_dir: 输出目录
        audio_dir: 音频目录
        screenshot_dir: 截图目录
        card_styles: 卡片样式列表，如 ["sentence"]、["vocab"]、["sentence", "vocab"]

    Returns:
        输出的 .apkg 文件路径
    """
    if card_styles is None:
        card_styles = ["sentence"]

    deck_name = Path(video_name).stem

    card_data_list = []
    for i, c in enumerate(cards):
        print(f"卡片 {i}: audio_path={c.get('audio_path', 'N/A')}, screenshot_path={c.get('screenshot_path', 'N/A')}")
        card_data_list.append(CardData(
            index=c.get("index", i),
            sentence=c.get("text", ""),
            translation=c.get("translation", ""),
            notes=c.get("notes", ""),
            audio_path=c.get("audio_path", ""),
            screenshot_path=c.get("screenshot_path", ""),
            word=c.get("word", ""),
            definition=c.get("definition", "")
        ))

    deck = create_deck(deck_name, card_data_list, card_styles=card_styles)

    # 收集媒体文件
    audio_files = []
    screenshot_files = []

    for c in card_data_list:
        if c.audio_path and Path(c.audio_path).exists():
            audio_files.append(c.audio_path)
            print(f"音频文件存在: {c.audio_path}")
        else:
            print(f"音频文件不存在: {c.audio_path}")

        if c.screenshot_path and Path(c.screenshot_path).exists():
            screenshot_files.append(c.screenshot_path)
            print(f"截图文件存在: {c.screenshot_path}")
        else:
            print(f"截图文件不存在: {c.screenshot_path}")

    print(f"有效音频文件总数: {len(audio_files)}")
    print(f"有效截图文件总数: {len(screenshot_files)}")

    # 保存
    output_path = Path(output_dir) / f"{deck_name}.apkg"
    save_deck_with_media(
        deck,
        str(output_path),
        audio_files=audio_files,
        screenshot_files=screenshot_files,
        audio_dir=audio_dir,
        screenshot_dir=screenshot_dir
    )

    # 验证文件是否创建成功
    if output_path.exists():
        print(f"牌组已生成: {output_path}")
        print(f"文件大小: {output_path.stat().st_size} bytes")
        return str(output_path)
    else:
        raise Exception(f"牌组生成失败: {output_path} 不存在")


if __name__ == '__main__':
    # 测试
    deck = create_deck("测试牌组", [])
    print(f"测试牌组创建成功，ID: {deck.deck_id}")
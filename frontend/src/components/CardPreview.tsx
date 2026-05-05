import { useState, useRef } from 'react';
import { ProcessedCard } from '../types';
import { ChevronLeft, ChevronRight, Play, Pause, Image as ImageIcon } from 'lucide-react';

interface CardPreviewProps {
  cards: ProcessedCard[];
  cardStyles: string[];
  currentIndex: number;
  onPrevious: () => void;
  onNext: () => void;
}

// 与 core/pack_apkg.py 中 _CSS 保持一致
const ANKI_CSS = `
.anki-card {
  font-family: system-ui, -apple-system, sans-serif;
  font-size: 18px;
  text-align: center;
  color: #2c3e50;
  background-color: #f8f9fa;
  margin: 0;
  padding: 10px;
}
.anki-card .container { max-width: 600px; margin: 0 auto; }
.anki-card .image-box img {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  margin-bottom: 10px;
}
.anki-card .original { font-weight: 600; font-size: 1.2em; color: #000; margin-top: 15px; }
.anki-card .translation { color: #666; font-size: 0.95em; margin-top: 8px; }
.anki-card .notes {
  text-align: left;
  background: #fff;
  border-left: 4px solid #007bff;
  padding: 10px;
  margin-top: 15px;
  font-size: 0.9em;
  border-radius: 4px;
  white-space: pre-line;
}
.anki-card .target-word {
  font-size: 2.5em;
  font-weight: 800;
  color: #007bff;
  margin: 40px 0 10px 0;
}
.anki-card .word-meaning {
  font-size: 1.4em;
  color: #28a745;
  font-weight: 500;
  margin-bottom: 20px;
}
.anki-card .hint {
  color: #999;
  font-size: 0.85em;
  margin-top: 20px;
}
.anki-card .example-box {
  background: #f0f2f5;
  padding: 15px;
  border-radius: 12px;
  text-align: left;
  margin-top: 15px;
}
.anki-card .example-box .tag {
  display: inline-block;
  font-size: 0.7em;
  padding: 2px 8px;
  background: #6c757d;
  color: white;
  border-radius: 4px;
  margin-bottom: 8px;
}
.anki-card .example-box .image-box img {
  width: 100%;
  height: auto;
  border-radius: 8px;
}
.anki-card .example-box .original {
  font-weight: 600;
  font-size: 1em;
  color: #333;
  margin: 8px 0;
}
.anki-card hr#answer {
  border: none;
  border-top: 1px solid #ddd;
  margin: 16px 0;
}
`;

const SentenceFront = ({ card }: { card: ProcessedCard }) => (
  <div className="anki-card">
    <div className="container">
      <div className="image-box">
        {card.screenshot_path ? (
          <img src={card.screenshot_path} alt="截图" />
        ) : (
          <div className="flex items-center justify-center w-full h-40 bg-gray-200 rounded-lg">
            <ImageIcon className="w-8 h-8 text-gray-400" />
          </div>
        )}
      </div>
    </div>
  </div>
);

const SentenceBack = ({ card }: { card: ProcessedCard }) => (
  <div className="anki-card">
    <div className="container">
      <div className="image-box">
        {card.screenshot_path && <img src={card.screenshot_path} alt="截图" />}
      </div>
      <hr id="answer" />
      <div className="text-content">
        <div className="original">{card.sentence}</div>
        {card.translation && <div className="translation">{card.translation}</div>}
        {card.notes && <div className="notes">{card.notes}</div>}
      </div>
    </div>
  </div>
);

const VocabFront = ({ card }: { card: ProcessedCard }) => (
  <div className="anki-card">
    <div className="container">
      <div className="target-word">{card.word || card.sentence}</div>
      <div className="hint">试着回想这个词在视频里的意思</div>
    </div>
  </div>
);

const VocabBack = ({ card }: { card: ProcessedCard }) => (
  <div className="anki-card">
    <div className="container">
      <div className="target-word">{card.word || card.sentence}</div>
      {card.definition && <div className="word-meaning">{card.definition}</div>}
      <hr id="answer" />
      <div className="example-box">
        <div className="tag">CONTEXT / 例句</div>
        {card.screenshot_path && (
          <div className="image-box">
            <img src={card.screenshot_path} alt="截图" />
          </div>
        )}
        <div className="original">{card.sentence}</div>
      </div>
    </div>
  </div>
);

export const CardPreview = ({ cards, cardStyles, currentIndex, onPrevious, onNext }: CardPreviewProps) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [previewStyle, setPreviewStyle] = useState<string>(cardStyles[0] || 'sentence');
  const [showAnswer, setShowAnswer] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  if (cards.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        暂无卡片数据
      </div>
    );
  }

  const card = cards[currentIndex];

  const handlePlayPause = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlaying(false);
    } else {
      audioRef.current.play().catch(() => {});
      setIsPlaying(true);
    }
  };

  const handleAudioEnded = () => {
    setIsPlaying(false);
  };

  const handleChangeCard = (fn: () => void) => {
    setIsPlaying(false);
    setShowAnswer(false);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    fn();
  };

  return (
    <div className="space-y-4">
      <style>{ANKI_CSS}</style>

      {/* 导航 + 样式切换 */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => handleChangeCard(onPrevious)}
          disabled={currentIndex === 0}
          className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:hover:bg-gray-700"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
            卡片 {currentIndex + 1} / {cards.length}
          </span>
          {cardStyles.length > 1 && (
            <div className="flex bg-gray-200 dark:bg-gray-700 rounded-lg p-0.5">
              {cardStyles.includes('sentence') && (
                <button
                  onClick={() => { setPreviewStyle('sentence'); setShowAnswer(false); }}
                  className={`px-2 py-0.5 text-xs rounded-md transition-colors ${
                    previewStyle === 'sentence'
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm'
                      : 'text-gray-600 dark:text-gray-400'
                  }`}
                >
                  句型卡
                </button>
              )}
              {cardStyles.includes('vocab') && (
                <button
                  onClick={() => { setPreviewStyle('vocab'); setShowAnswer(false); }}
                  className={`px-2 py-0.5 text-xs rounded-md transition-colors ${
                    previewStyle === 'vocab'
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm'
                      : 'text-gray-600 dark:text-gray-400'
                  }`}
                >
                  词汇卡
                </button>
              )}
            </div>
          )}
        </div>

        <button
          onClick={() => handleChangeCard(onNext)}
          disabled={currentIndex === cards.length - 1}
          className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:hover:bg-gray-700"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* 卡片：正面 → 翻转 → 背面 */}
      <div className="border-2 border-dashed border-gray-300 rounded-lg overflow-hidden dark:border-gray-600">
        {showAnswer
          ? (previewStyle === 'vocab' ? <VocabBack card={card} /> : <SentenceBack card={card} />)
          : (previewStyle === 'vocab' ? <VocabFront card={card} /> : <SentenceFront card={card} />)
        }
      </div>

      {/* 显示/隐藏答案 */}
      <button
        onClick={() => setShowAnswer(!showAnswer)}
        className="w-full py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm"
      >
        {showAnswer ? '回到正面' : '显示答案'}
      </button>

      {/* 音频控制 */}
      <div className="flex items-center justify-center gap-3">
        {card.audio_path ? (
          <>
            <audio
              ref={audioRef}
              src={card.audio_path}
              onEnded={handleAudioEnded}
              preload="auto"
            />
            <button
              onClick={handlePlayPause}
              className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 text-sm"
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              {isPlaying ? '暂停' : '播放音频'}
            </button>
          </>
        ) : (
          <span className="text-sm text-gray-400">无音频</span>
        )}
      </div>
    </div>
  );
};

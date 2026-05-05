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

export const CardPreview = ({ cards, cardStyles, currentIndex, onPrevious, onNext }: CardPreviewProps) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [previewStyle, setPreviewStyle] = useState<string>(cardStyles[0] || 'sentence');
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

  // 切换卡片时重置播放状态
  const handleChangeCard = (fn: () => void) => {
    setIsPlaying(false);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    fn();
  };

  return (
    <div className="space-y-4">
      {/* 导航控制 + 样式切换 */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => handleChangeCard(onPrevious)}
          disabled={currentIndex === 0}
          className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:hover:bg-gray-700"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
            卡片 {currentIndex + 1} / {cards.length}
          </span>
          {cardStyles.length > 1 && (
            <div className="flex bg-gray-200 dark:bg-gray-700 rounded-lg p-0.5">
              <button
                onClick={() => setPreviewStyle('sentence')}
                className={`px-2 py-0.5 text-xs rounded-md transition-colors ${
                  previewStyle === 'sentence'
                    ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm'
                    : 'text-gray-600 dark:text-gray-400'
                }`}
              >
                句型卡
              </button>
              <button
                onClick={() => setPreviewStyle('vocab')}
                className={`px-2 py-0.5 text-xs rounded-md transition-colors ${
                  previewStyle === 'vocab'
                    ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm'
                    : 'text-gray-600 dark:text-gray-400'
                }`}
              >
                词汇卡
              </button>
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

      {/* 卡片正面 */}
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 bg-gray-50 dark:border-gray-600 dark:bg-gray-800">
        <div className="text-center">
          {previewStyle === 'vocab' ? (
            // 词汇卡正面：单词
            <>
              <div className="text-3xl font-bold text-gray-900 dark:text-gray-100 my-6">
                {card.word || card.sentence}
              </div>
              <div className="text-sm text-gray-400">试着回想这个词在视频里的意思</div>
            </>
          ) : (
            // 句型卡正面：截图
            <>
              {card.screenshot_path ? (
                <img
                  src={card.screenshot_path}
                  alt="截图"
                  className="w-full max-w-md mx-auto mb-4 rounded-lg object-cover"
                />
              ) : (
                <div className="w-48 h-32 bg-gray-200 rounded-lg mx-auto mb-4 flex items-center justify-center dark:bg-gray-700">
                  <ImageIcon className="w-8 h-8 text-gray-400" />
                </div>
              )}
            </>
          )}

          {/* 音频按钮 */}
          {card.audio_path ? (
            <div className="mt-2">
              <audio
                ref={audioRef}
                src={card.audio_path}
                onEnded={handleAudioEnded}
                preload="auto"
              />
              <button
                onClick={handlePlayPause}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
              >
                {isPlaying ? (
                  <>
                    <Pause className="w-4 h-4" />
                    暂停
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    播放音频
                  </>
                )}
              </button>
            </div>
          ) : (
            <button className="inline-flex items-center gap-2 px-4 py-2 bg-gray-300 text-gray-500 rounded-lg cursor-not-allowed dark:bg-gray-600 dark:text-gray-400" disabled>
              <Play className="w-4 h-4" />
              无音频
            </button>
          )}
        </div>
      </div>

      {/* 卡片背面 */}
      <div className="border border-gray-200 rounded-lg p-6 space-y-4 dark:border-gray-700">
        {previewStyle === 'vocab' ? (
          // 词汇卡背面：释义 + 例句框
          <>
            <div>
              <h4 className="text-sm font-medium text-gray-500 mb-1 dark:text-gray-400">单词</h4>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{card.word || card.sentence}</p>
            </div>
            {card.definition && (
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-1 dark:text-gray-400">释义</h4>
                <p className="text-green-600 dark:text-green-400 text-lg font-medium">{card.definition}</p>
              </div>
            )}
            <hr className="border-gray-200 dark:border-gray-600" />
            <div className="bg-gray-100 dark:bg-gray-800 rounded-xl p-4 text-left">
              <span className="inline-block text-xs px-2 py-0.5 bg-gray-500 text-white rounded mb-2">
                CONTEXT / 例句
              </span>
              {card.screenshot_path && (
                <img
                  src={card.screenshot_path}
                  alt="截图"
                  className="w-full rounded-lg object-cover mb-2"
                />
              )}
              <p className="text-gray-900 dark:text-gray-100 font-semibold">{card.sentence}</p>
            </div>
          </>
        ) : (
          // 句型卡背面：原文 + 翻译 + 注释
          <>
            <div>
              <h4 className="text-sm font-medium text-gray-500 mb-1 dark:text-gray-400">原文</h4>
              <p className="text-gray-900 dark:text-gray-100">{card.sentence}</p>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-500 mb-1 dark:text-gray-400">翻译</h4>
              <p className="text-gray-700 dark:text-gray-300">{card.translation}</p>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-500 mb-1 dark:text-gray-400">词汇注释</h4>
              <p className="text-gray-700 whitespace-pre-line dark:text-gray-300">{card.notes}</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

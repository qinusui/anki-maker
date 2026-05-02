import { useState, useRef } from 'react';
import { ProcessedCard } from '../types';
import { ChevronLeft, ChevronRight, Play, Pause, Image as ImageIcon } from 'lucide-react';

interface CardPreviewProps {
  cards: ProcessedCard[];
  currentIndex: number;
  onPrevious: () => void;
  onNext: () => void;
}

export const CardPreview = ({ cards, currentIndex, onPrevious, onNext }: CardPreviewProps) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  if (cards.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
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
      {/* 导航控制 */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => handleChangeCard(onPrevious)}
          disabled={currentIndex === 0}
          className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>

        <span className="text-sm font-medium text-gray-600">
          卡片 {currentIndex + 1} / {cards.length}
        </span>

        <button
          onClick={() => handleChangeCard(onNext)}
          disabled={currentIndex === cards.length - 1}
          className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* 卡片正面 */}
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 bg-gray-50">
        <div className="text-center">
          {card.screenshot_path ? (
            <img
              src={card.screenshot_path}
              alt="截图"
              className="w-full max-w-xs mx-auto mb-4 rounded-lg object-cover"
            />
          ) : (
            <div className="w-32 h-20 bg-gray-200 rounded-lg mx-auto mb-4 flex items-center justify-center">
              <ImageIcon className="w-8 h-8 text-gray-400" />
            </div>
          )}

          {card.audio_path ? (
            <div>
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
            <button className="inline-flex items-center gap-2 px-4 py-2 bg-gray-300 text-gray-500 rounded-lg cursor-not-allowed" disabled>
              <Play className="w-4 h-4" />
              无音频
            </button>
          )}
        </div>
      </div>

      {/* 卡片背面 */}
      <div className="border border-gray-200 rounded-lg p-6 space-y-4">
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-1">原文</h4>
          <p className="text-gray-900">{card.sentence}</p>
        </div>

        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-1">翻译</h4>
          <p className="text-gray-700">{card.translation}</p>
        </div>

        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-1">词汇注释</h4>
          <p className="text-gray-700 whitespace-pre-line">{card.notes}</p>
        </div>
      </div>
    </div>
  );
};

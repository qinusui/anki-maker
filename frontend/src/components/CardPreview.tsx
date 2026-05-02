import { ProcessedCard } from '../types';
import { ChevronLeft, ChevronRight, Play, Image as ImageIcon } from 'lucide-react';

interface CardPreviewProps {
  cards: ProcessedCard[];
  currentIndex: number;
  onPrevious: () => void;
  onNext: () => void;
}

export const CardPreview = ({ cards, currentIndex, onPrevious, onNext }: CardPreviewProps) => {
  if (cards.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        暂无卡片数据
      </div>
    );
  }

  const card = cards[currentIndex];

  return (
    <div className="space-y-4">
      {/* 导航控制 */}
      <div className="flex items-center justify-between">
        <button
          onClick={onPrevious}
          disabled={currentIndex === 0}
          className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>

        <span className="text-sm font-medium text-gray-600">
          卡片 {currentIndex + 1} / {cards.length}
        </span>

        <button
          onClick={onNext}
          disabled={currentIndex === cards.length - 1}
          className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* 卡片正面 */}
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 bg-gray-50">
        <div className="text-center">
          <div className="w-32 h-20 bg-gray-200 rounded-lg mx-auto mb-4 flex items-center justify-center">
            <ImageIcon className="w-8 h-8 text-gray-400" />
          </div>
          <button className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors">
            <Play className="w-4 h-4" />
            播放音频
          </button>
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

import { SubtitleItem, AIRecommendation } from '../types';
import { cn } from '../utils/cn';

interface SubtitleTableProps {
  subtitles: SubtitleItem[];
  selectedIndices: Set<number>;
  onToggleSelection: (index: number) => void;
  onSelectAll: () => void;
  isAllSelected: boolean;
  recommendations: Map<number, AIRecommendation> | null;
  isRecommending: boolean;
}

export const SubtitleTable = ({
  subtitles,
  selectedIndices,
  onToggleSelection,
  onSelectAll,
  isAllSelected,
  recommendations,
  isRecommending,
}: SubtitleTableProps) => {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const recommendedCount = recommendations
    ? Array.from(recommendations.values()).filter(r => r.include).length
    : 0;

  return (
    <div className="w-full border border-gray-200 rounded-lg overflow-hidden">
      {/* 表头 */}
      <div className="bg-gray-50 grid grid-cols-12 gap-2 px-4 py-3 border-b border-gray-200">
        <div className="col-span-1">
          <input
            type="checkbox"
            checked={isAllSelected}
            onChange={onSelectAll}
            className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
          />
        </div>
        <div className="col-span-1 text-xs font-medium text-gray-500">序号</div>
        <div className="col-span-5 text-xs font-medium text-gray-500">原文</div>
        <div className="col-span-2 text-xs font-medium text-gray-500">时间</div>
        <div className="col-span-1 text-xs font-medium text-gray-500">时长</div>
        <div className="col-span-2 text-xs font-medium text-gray-500">
          AI 推荐
          {recommendations && (
            <span className="ml-1 text-green-600">({recommendedCount})</span>
          )}
        </div>
      </div>

      {/* 表格内容 */}
      <div className="max-h-96 overflow-y-auto">
        {isRecommending && subtitles.length > 0 && (
          <div className="px-4 py-2 bg-blue-50 text-blue-700 text-sm flex items-center gap-2">
            <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
            AI 正在分析字幕，评估学习价值...
          </div>
        )}
        {subtitles.map((subtitle) => {
          const rec = recommendations?.get(subtitle.index);
          return (
            <div
              key={subtitle.index}
              className={cn(
                'grid grid-cols-12 gap-2 px-4 py-3 border-b border-gray-100 hover:bg-gray-50 transition-colors',
                selectedIndices.has(subtitle.index) && 'bg-blue-50',
                rec?.include && 'bg-green-50 hover:bg-green-100'
              )}
            >
              <div className="col-span-1 flex items-center">
                <input
                  type="checkbox"
                  checked={selectedIndices.has(subtitle.index)}
                  onChange={() => onToggleSelection(subtitle.index)}
                  className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                />
              </div>
              <div className="col-span-1 text-sm text-gray-500 flex items-center">
                {subtitle.index}
              </div>
              <div className="col-span-5 text-sm text-gray-900 flex items-center">
                {subtitle.text}
              </div>
              <div className="col-span-2 text-sm text-gray-500 flex items-center">
                {formatTime(subtitle.start_sec)} - {formatTime(subtitle.end_sec)}
              </div>
              <div className="col-span-1 text-sm text-gray-500 flex items-center">
                {subtitle.duration.toFixed(1)}s
              </div>
              <div className="col-span-2 flex items-center">
                {rec ? (
                  <span
                    className={cn(
                      'inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full',
                      rec.include
                        ? 'bg-green-100 text-green-700'
                        : 'bg-gray-100 text-gray-500'
                    )}
                    title={rec.reason}
                  >
                    {rec.include ? '推荐' : '跳过'}
                  </span>
                ) : (
                  <span className="text-xs text-gray-400">-</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {subtitles.length === 0 && (
        <div className="p-8 text-center text-gray-500">
          暂无字幕数据
        </div>
      )}
    </div>
  );
};

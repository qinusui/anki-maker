import { SubtitleItem } from '../types';
import { cn } from '../utils/cn';

interface SubtitleTableProps {
  subtitles: SubtitleItem[];
  selectedIndices: Set<number>;
  onToggleSelection: (index: number) => void;
  onSelectAll: () => void;
  isAllSelected: boolean;
}

export const SubtitleTable = ({
  subtitles,
  selectedIndices,
  onToggleSelection,
  onSelectAll,
  isAllSelected,
}: SubtitleTableProps) => {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

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
        <div className="col-span-6 text-xs font-medium text-gray-500">原文</div>
        <div className="col-span-2 text-xs font-medium text-gray-500">时间</div>
        <div className="col-span-2 text-xs font-medium text-gray-500">时长</div>
      </div>

      {/* 表格内容 */}
      <div className="max-h-96 overflow-y-auto">
        {subtitles.map((subtitle) => (
          <div
            key={subtitle.index}
            className={cn(
              'grid grid-cols-12 gap-2 px-4 py-3 border-b border-gray-100 hover:bg-gray-50 transition-colors',
              selectedIndices.has(subtitle.index) && 'bg-blue-50'
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
            <div className="col-span-6 text-sm text-gray-900 flex items-center">
              {subtitle.text}
            </div>
            <div className="col-span-2 text-sm text-gray-500 flex items-center">
              {formatTime(subtitle.start_sec)} - {formatTime(subtitle.end_sec)}
            </div>
            <div className="col-span-2 text-sm text-gray-500 flex items-center">
              {subtitle.duration.toFixed(1)}s
            </div>
          </div>
        ))}
      </div>

      {subtitles.length === 0 && (
        <div className="p-8 text-center text-gray-500">
          暂无字幕数据
        </div>
      )}
    </div>
  );
};

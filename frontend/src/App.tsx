import { useState } from 'react';
import { Film, FileText, Download, Settings, Info } from 'lucide-react';
import { Button } from './components/Button';
import { Card, CardContent, CardHeader, CardTitle } from './components/Card';
import { Input } from './components/Input';
import { ProgressBar } from './components/ProgressBar';
import { FileUpload } from './components/FileUpload';
import { SubtitleTable } from './components/SubtitleTable';
import { ProcessingStatus } from './components/ProcessingStatus';
import { CardPreview } from './components/CardPreview';
import { SubtitleItem, ProcessedCard } from './types';
import { subtitleAPI, processAPI } from './services/api';

const PROCESSING_STEPS = [
  { id: 'upload', label: '上传文件', status: 'pending' as const },
  { id: 'parse', label: '解析字幕', status: 'pending' as const },
  { id: 'ai', label: 'AI 处理', status: 'pending' as const },
  { id: 'media', label: '处理媒体', status: 'pending' as const },
  { id: 'pack', label: '打包卡片', status: 'pending' as const },
];

function App() {
  const [apiKey, setApiKey] = useState('');
  const [minDuration, setMinDuration] = useState(1.0);
  const [outputDir, setOutputDir] = useState('./output');

  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [subtitleFile, setSubtitleFile] = useState<File | null>(null);

  const [subtitles, setSubtitles] = useState<SubtitleItem[]>([]);
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());

  const [isProcessing, setIsProcessing] = useState(false);
  const [processingSteps, setProcessingSteps] = useState(PROCESSING_STEPS);
  const [currentStep, setCurrentStep] = useState(-1);

  const [result, setResult] = useState<ProcessedCard[] | null>(null);
  const [apkgPath, setApkgPath] = useState<string | null>(null);

  const [previewIndex, setPreviewIndex] = useState(0);
  const [showHelp, setShowHelp] = useState(false);

  // 加载字幕
  const handleLoadSubtitles = async () => {
    if (!subtitleFile) return;

    try {
      setProcessingSteps(steps =>
        steps.map((s, i) =>
          i === 0 ? { ...s, status: 'processing' } : { ...s, status: 'pending' }
        )
      );
      setCurrentStep(0);

      const response = await subtitleAPI.upload(subtitleFile, minDuration);

      setSubtitles(response.subtitles);
      setSelectedIndices(new Set(response.subtitles.map(s => s.index)));

      setProcessingSteps(steps =>
        steps.map((s, i) =>
          i === 0 ? { ...s, status: 'completed' } : { ...s, status: 'pending' }
        )
      );
    } catch (error) {
      console.error('加载字幕失败:', error);
      setProcessingSteps(steps =>
        steps.map((s, i) =>
          i === 0 ? { ...s, status: 'error', error: String(error) } : s
        )
      );
    }
  };

  // 处理选中的字幕
  const handleProcess = async () => {
    if (!videoFile || selectedIndices.size === 0) return;

    setIsProcessing(true);
    setProcessingSteps(PROCESSING_STEPS);

    try {
      // 模拟处理流程（实际应该调用后端 API）
      const steps = ['upload', 'parse', 'ai', 'media', 'pack'];
      for (let i = 0; i < steps.length; i++) {
        setCurrentStep(i);
        setProcessingSteps(s =>
          s.map((step, idx) =>
            idx === i
              ? { ...step, status: 'processing' }
              : idx < i
              ? { ...step, status: 'completed' }
              : { ...step, status: 'pending' }
          )
        );

        // 模拟每个步骤的延迟
        await new Promise(resolve => setTimeout(resolve, 1500));
      }

      // 模拟生成结果
      const mockCards: ProcessedCard[] = [
        {
          sentence: 'Hello, how are you?',
          translation: '你好，你还好吗？',
          notes: 'how are you: 常见问候语\nhello: 问候',
          start_sec: 83.456,
          end_sec: 85.789,
        },
        {
          sentence: "I'm doing great, thanks for asking!",
          translation: '我很好，谢谢你的关心！',
          notes: "I'm: I am 的缩写\ndoing great: 表现很好\nthanks for asking: 谢谢关心",
          start_sec: 86.123,
          end_sec: 89.456,
        },
      ];

      setResult(mockCards);
      setApkgPath('./output/deck.apkg');

      setProcessingSteps(s => s.map(step => ({ ...step, status: 'completed' as const })));

    } catch (error) {
      console.error('处理失败:', error);
      setProcessingSteps(s =>
        s.map((step, i) =>
          step.status === 'processing'
            ? { ...step, status: 'error', error: String(error) }
            : step
        )
      );
    } finally {
      setIsProcessing(false);
    }
  };

  // 下载文件
  const handleDownload = () => {
    if (!apkgPath) return;
    window.open(`/download/${apkgPath.split('/').pop()}`, '_blank');
  };

  // 切换选中状态
  const toggleSelection = (index: number) => {
    const newSelected = new Set(selectedIndices);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedIndices(newSelected);
  };

  // 全选/取消全选
  const toggleSelectAll = () => {
    const allSelected = selectedIndices.size === subtitles.length;
    if (allSelected) {
      setSelectedIndices(new Set());
    } else {
      setSelectedIndices(new Set(subtitles.map(s => s.index)));
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航 */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <Film className="w-8 h-8 text-primary-600" />
              <h1 className="text-xl font-bold text-gray-900">Anki 卡片生成器</h1>
            </div>
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowHelp(!showHelp)}
              >
                <Info className="w-4 h-4 mr-2" />
                使用说明
              </Button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 使用说明 */}
        {showHelp && (
          <Card className="mb-6">
            <CardContent>
              <h3 className="text-lg font-semibold mb-3">使用说明</h3>
              <ol className="list-decimal list-inside space-y-2 text-gray-700">
                <li>上传视频文件（.mp4, .mkv, .avi）</li>
                <li>上传对应的字幕文件（.srt）</li>
                <li>调整最短时长过滤条件</li>
                <li>点击"加载字幕"预览内容</li>
                <li>勾选需要生成卡片的句子</li>
                <li>点击"开始处理"生成卡片</li>
                <li>预览卡片后下载 .apkg 文件导入 Anki</li>
              </ol>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧：设置和上传 */}
          <div className="lg:col-span-2 space-y-6">
            {/* API Key 配置 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="w-5 h-5" />
                  配置
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input
                  type="password"
                  label="DeepSeek API Key"
                  placeholder="输入你的 DeepSeek API Key"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      最短字幕时长（秒）
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      min="0.5"
                      max="5"
                      value={minDuration}
                      onChange={(e) => setMinDuration(parseFloat(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  <Input
                    label="输出目录"
                    placeholder="./output"
                    value={outputDir}
                    onChange={(e) => setOutputDir(e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>

            {/* 文件上传 */}
            <Card>
              <CardHeader>
                <CardTitle>上传文件</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <FileUpload
                  accept=".mp4,.mkv,.avi,.mov,.webm"
                  onFileSelect={setVideoFile}
                  selectedFile={videoFile}
                  onClear={() => setVideoFile(null)}
                  label="视频文件"
                  icon="video"
                />
                <FileUpload
                  accept=".srt"
                  onFileSelect={setSubtitleFile}
                  selectedFile={subtitleFile}
                  onClear={() => setSubtitleFile(null)}
                  label="字幕文件"
                  icon="text"
                />
                <Button
                  variant="primary"
                  className="w-full"
                  onClick={handleLoadSubtitles}
                  disabled={!subtitleFile || isProcessing}
                >
                  加载字幕
                </Button>
              </CardContent>
            </Card>

            {/* 字幕表格 */}
            {subtitles.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>
                    字幕预览 ({selectedIndices.size} / {subtitles.length})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <SubtitleTable
                    subtitles={subtitles}
                    selectedIndices={selectedIndices}
                    onToggleSelection={toggleSelection}
                    onSelectAll={toggleSelectAll}
                    isAllSelected={selectedIndices.size === subtitles.length}
                  />
                  <Button
                    variant="primary"
                    className="w-full mt-4"
                    onClick={handleProcess}
                    disabled={selectedIndices.size === 0 || isProcessing || !videoFile}
                  >
                    开始处理 ({selectedIndices.size} 条)
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>

          {/* 右侧：状态和结果 */}
          <div className="space-y-6">
            {/* 处理状态 */}
            <Card>
              <CardHeader>
                <CardTitle>处理进度</CardTitle>
              </CardHeader>
              <CardContent>
                <ProcessingStatus
                  steps={processingSteps}
                  currentStepIndex={currentStep}
                />
                {isProcessing && (
                  <div className="mt-4">
                    <ProgressBar
                      progress={(currentStep + 1) / PROCESSING_STEPS.length * 100}
                    />
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 结果预览 */}
            {result && result.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>卡片预览</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardPreview
                    cards={result}
                    currentIndex={previewIndex}
                    onPrevious={() => setPreviewIndex(Math.max(0, previewIndex - 1))}
                    onNext={() => setPreviewIndex(Math.min(result.length - 1, previewIndex + 1))}
                  />
                  <Button
                    variant="primary"
                    className="w-full mt-4"
                    onClick={handleDownload}
                  >
                    <Download className="w-4 h-4 mr-2" />
                    下载牌组 (.apkg)
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;

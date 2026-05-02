import { useState, useEffect, useRef } from 'react';
import { Film, FileText, Download, Settings, Info, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from './components/Button';
import { Card, CardContent, CardHeader, CardTitle } from './components/Card';
import { Input } from './components/Input';
import { ProgressBar } from './components/ProgressBar';
import { FileUpload } from './components/FileUpload';
import { SubtitleTable } from './components/SubtitleTable';
import { ProcessingStatus } from './components/ProcessingStatus';
import { CardPreview } from './components/CardPreview';
import { SubtitleItem, ProcessedCard, AIRecommendation } from './types';
import { subtitleAPI, processAPI } from './services/api';

// 格式化时间为 SRT 格式
function formatSRTTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 1000);
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')},${ms.toString().padStart(3, '0')}`;
}

// 根据选中的字幕生成新的 SRT 文件内容
function generateSRTContent(subtitles: SubtitleItem[], selectedIndices: Set<number>): string {
  const selectedSubtitles = subtitles.filter(s => selectedIndices.has(s.index));
  let content = '';

  selectedSubtitles.forEach((sub, idx) => {
    content += `${idx + 1}\n`;
    content += `${formatSRTTime(sub.start_sec)} --> ${formatSRTTime(sub.end_sec)}\n`;
    content += `${sub.text}\n\n`;
  });

  return content;
}

const PROCESSING_STEPS = [
  { id: 'upload', label: '上传文件', status: 'pending' as const },
  { id: 'parse', label: '解析字幕', status: 'pending' as const },
  { id: 'ai', label: 'AI 智能注释', status: 'pending' as const },
  { id: 'media', label: '切割音频与截图', status: 'pending' as const },
  { id: 'pack', label: '打包 Anki 牌组', status: 'pending' as const },
];

const DEFAULT_RECOMMEND_PROMPT = `你是英语学习教材编写专家。对输入的字幕列表，每条判断是否值得作为学习材料：

判断标准：
- 有明确的语法知识点（如时态、从句、虚拟语气等）
- 有实用表达或固定搭配
- 对话内容有意义（非简单寒暄如'okay', 'yeah', 'uh-huh'等）
- 有文化背景或情境意义`;

function App() {
  const [apiKey, setApiKey] = useState('');
  const [minDuration, setMinDuration] = useState(1.0);

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

  // AI 推荐相关
  const [recommendations, setRecommendations] = useState<Map<number, AIRecommendation> | null>(null);
  const [isRecommending, setIsRecommending] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const transcribingRef = useRef(false);
  const transcribedVideoName = useRef<string | null>(null);
  const [transcribeStep, setTranscribeStep] = useState(0);
  const [transcribeTotalSteps, setTranscribeTotalSteps] = useState(4);
  const [transcribeMessage, setTranscribeMessage] = useState('');
  const [transcribeAnimProgress, setTranscribeAnimProgress] = useState(0); // 动画进度
  const transcribeAnimRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [recommendBatch, setRecommendBatch] = useState(0);
  const [recommendTotalBatches, setRecommendTotalBatches] = useState(0);
  const [customPrompt, setCustomPrompt] = useState(DEFAULT_RECOMMEND_PROMPT);
  const [showPromptEditor, setShowPromptEditor] = useState(false);
  const [recommendBatchSize, setRecommendBatchSize] = useState(30);

  // 每 3 秒发送心跳（延迟 6 秒等后端完全就绪）
  useEffect(() => {
    const sendHeartbeat = () => {
      fetch('/api/heartbeat', { method: 'POST' }).catch(() => {});
    };
    const timer = setTimeout(() => {
      sendHeartbeat();
      const interval = setInterval(sendHeartbeat, 3000);
      (window as any).__heartbeatInterval = interval;
    }, 6000);
    return () => {
      clearTimeout(timer);
      clearInterval((window as any).__heartbeatInterval);
    };
  }, []);

  // 转录进度动画：分阶段加权 + 转录阶段缓慢渐进
  useEffect(() => {
    // 加权基准：保存0%→加载模型10%→转录中20%→解析90%→完成100%
    const stepBase = [0, 10, 20, 90, 100];

    if (!isTranscribing) {
      setTranscribeAnimProgress(0);
      if (transcribeAnimRef.current) clearInterval(transcribeAnimRef.current);
      return;
    }

    const base = stepBase[transcribeStep] || 0;
    setTranscribeAnimProgress(base);

    if (transcribeStep === 2) {
      // 转录中：每秒微增 0.3%，从 20% 慢慢爬到接近 90%
      transcribeAnimRef.current = setInterval(() => {
        setTranscribeAnimProgress(prev => {
          if (prev < 20) return 20;
          if (prev >= 88) return 88;
          return Math.min(88, prev + 0.3);
        });
      }, 1000);
    } else {
      if (transcribeAnimRef.current) clearInterval(transcribeAnimRef.current);
    }

    return () => {
      if (transcribeAnimRef.current) clearInterval(transcribeAnimRef.current);
    };
  }, [isTranscribing, transcribeStep]);

  // Whisper 转录视频生成字幕
  const handleTranscribe = async () => {
    if (!videoFile || transcribingRef.current) return;

    if (transcribedVideoName.current === videoFile.name) {
      return;
    }

    transcribingRef.current = true;
    setIsTranscribing(true);
    setTranscribeStep(0);
    setTranscribeTotalSteps(4);
    setTranscribeMessage('准备转录...');

    try {
      const { task_id } = await subtitleAPI.startTranscribe(videoFile, minDuration);

      const pollInterval = setInterval(async () => {
        try {
          const progress = await subtitleAPI.getTranscribeProgress(task_id);

          setTranscribeStep(progress.step);
          setTranscribeTotalSteps(progress.total_steps);
          setTranscribeMessage(progress.message);

          if (progress.status === 'completed' && progress.result) {
            clearInterval(pollInterval);
            setIsTranscribing(false);
            transcribingRef.current = false;

            setSubtitles(progress.result.subtitles);
            setSelectedIndices(new Set(progress.result.subtitles.map((s: SubtitleItem) => s.index)));
            setRecommendations(null);
            transcribedVideoName.current = videoFile.name;
          }

          if (progress.status === 'error') {
            clearInterval(pollInterval);
            setIsTranscribing(false);
            transcribingRef.current = false;
            alert(progress.error || '转录失败');
          }
        } catch (e) {
          // 轮询失败不中断
        }
      }, 1000);

      (window as any).__transcribePoll = pollInterval;

    } catch (error) {
      console.error('转录失败:', error);
      alert('转录失败: ' + (error instanceof Error ? error.message : '未知错误'));
      setIsTranscribing(false);
      transcribingRef.current = false;
    }
  };

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

  // AI 推荐字幕
  const handleAIRecommend = async () => {
    if (!apiKey) {
      alert('请先在配置中填写 DeepSeek API Key');
      return;
    }
    if (subtitles.length === 0) {
      alert('请先加载字幕');
      return;
    }

    setIsRecommending(true);
    setRecommendations(null);
    setRecommendBatch(0);
    setRecommendTotalBatches(0);

    try {
      // 1. 启动 AI 推荐任务
      const { task_id } = await subtitleAPI.startRecommend(
        subtitles,
        apiKey,
        customPrompt || undefined,
        recommendBatchSize
      );

      // 2. 轮询进度
      const pollInterval = setInterval(async () => {
        try {
          const progress = await subtitleAPI.getRecommendProgress(task_id);

          setRecommendBatch(progress.batch);
          setRecommendTotalBatches(progress.total_batches);

          if (progress.status === 'completed' && progress.result) {
            clearInterval(pollInterval);
            setIsRecommending(false);

            const map = new Map<number, AIRecommendation>();
            progress.result.recommendations.forEach(r => map.set(r.index, r));
            setRecommendations(map);

            // 自动选中推荐的句子
            const recommendedIndices = progress.result.recommendations
              .filter(r => r.include)
              .map(r => r.index);
            setSelectedIndices(new Set(recommendedIndices));
          }
        } catch (e) {
          // 轮询失败不中断
        }
      }, 1000);

      (window as any).__recommendPoll = pollInterval;

    } catch (error) {
      console.error('AI 推荐失败:', error);
      alert('AI 推荐失败: ' + (error instanceof Error ? error.message : '未知错误'));
      setIsRecommending(false);
    }
  };

  // 仅选推荐
  const selectRecommended = () => {
    if (!recommendations) return;
    const recommendedIndices = Array.from(recommendations.values())
      .filter(r => r.include)
      .map(r => r.index);
    setSelectedIndices(new Set(recommendedIndices));
  };

  // 处理选中的字幕
  const handleProcess = async () => {
    if (!videoFile) {
      alert('请先上传视频文件');
      return;
    }
    if (subtitles.length === 0) {
      alert('请先加载或生成字幕');
      return;
    }

    if (selectedIndices.size === 0) {
      alert('请至少选择一条字幕');
      return;
    }

    setIsProcessing(true);
    setProcessingSteps(PROCESSING_STEPS.map(s => ({ ...s, status: 'pending' as const })));
    setCurrentStep(0);

    // 根据选中的字幕生成新的 SRT 文件
    const srtContent = generateSRTContent(subtitles, selectedIndices);
    const selectedSubtitleBlob = new Blob([srtContent], { type: 'text/plain' });
    const selectedSubtitleFile = new File([selectedSubtitleBlob], 'selected_subtitles.srt', { type: 'text/plain' });

    // 如果有 AI 推荐结果，构建预处理数据（跳过后端 AI 步骤）
    let preProcessed: object[] | undefined;
    if (recommendations) {
      preProcessed = subtitles
        .filter(s => selectedIndices.has(s.index))
        .map(s => {
          const rec = recommendations.get(s.index);
          return {
            index: s.index,
            text: s.text,
            translation: rec?.translation || '',
            notes: rec?.notes || '',
            reason: rec?.reason || ''
          };
        });
    }

    try {
      // 1. 上传并启动后台处理
      const { task_id } = await processAPI.uploadAndProcess(
        videoFile,
        selectedSubtitleFile,
        minDuration,
        apiKey || undefined,
        preProcessed
      );

      // 2. 轮询进度
      const pollInterval = setInterval(async () => {
        try {
          const progress = await processAPI.getProgress(task_id);

          // 更新步骤状态
          setCurrentStep(progress.step);
          setProcessingSteps(steps => {
            const newSteps = [...steps];
            for (let i = 0; i < newSteps.length; i++) {
              if (i < progress.step) {
                newSteps[i] = { ...newSteps[i], status: 'completed' as const };
              } else if (i === progress.step) {
                newSteps[i] = { ...newSteps[i], status: 'processing' as const };
              }
            }
            return newSteps;
          });

          if (progress.status === 'completed' && progress.result) {
            clearInterval(pollInterval);
            setIsProcessing(false);
            setProcessingSteps(s => s.map(step => ({ ...step, status: 'completed' as const })));

            const r = progress.result;
            setApkgPath(r.apkg_path);

            if (r.cards && r.cards.length > 0) {
              setResult(r.cards);
              setPreviewIndex(0);
            } else {
              alert(`处理完成！生成了 ${r.cards_count} 张卡片。`);
            }
          }

          if (progress.status === 'error') {
            clearInterval(pollInterval);
            setIsProcessing(false);
            const errMsg = progress.error || '未知错误';
            alert(`处理失败: ${errMsg}`);
            setProcessingSteps(s =>
              s.map((step, i) =>
                step.status === 'processing'
                  ? { ...step, status: 'error' as const, error: errMsg }
                  : step
              )
            );
          }
        } catch (e) {
          // 轮询失败不中断
        }
      }, 1000);

      // 保存 interval ID 以便清理
      (window as any).__pollInterval = pollInterval;

    } catch (error) {
      console.error('处理失败:', error);
      const errorMessage = error instanceof Error ? error.message : '未知错误';
      alert(`处理失败: ${errorMessage}`);

      setProcessingSteps(s =>
        s.map((step, i) =>
          step.status === 'processing'
            ? { ...step, status: 'error' as const, error: errorMessage }
            : step
        )
      );
      setIsProcessing(false);
    }
  };

  // 下载文件
  const handleDownload = async () => {
    if (!apkgPath) return;

    try {
      // 创建一个临时链接下载
      const response = await fetch(`/download/${encodeURIComponent(apkgPath)}`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `下载失败 (HTTP ${response.status})`);
      }
      const blob = await response.blob();

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = apkgPath.split('/').pop() || 'deck.apkg';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();

      // 下载后清理服务端文件
      try {
        await processAPI.cleanup(apkgPath);
      } catch (e) {
        console.error('清理文件失败:', e);
      }
    } catch (error) {
      console.error('下载失败:', error);
      alert('下载失败，请手动访问: /download/' + encodeURIComponent(apkgPath));
    }
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
                  onFileSelect={(f) => { setVideoFile(f); transcribedVideoName.current = null; }}
                  selectedFile={videoFile}
                  onClear={() => { setVideoFile(null); transcribedVideoName.current = null; }}
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
                {subtitleFile ? (
                  <Button
                    variant="primary"
                    className="w-full"
                    onClick={handleLoadSubtitles}
                    disabled={!subtitleFile || isProcessing}
                  >
                    加载字幕
                  </Button>
                ) : (
                  <div className="space-y-2">
                    <Button
                      variant="primary"
                      className="w-full"
                      onClick={handleTranscribe}
                      disabled={!videoFile || isProcessing || isTranscribing}
                    >
                      {isTranscribing ? '转录中...' : '生成字幕'}
                    </Button>
                    {isTranscribing && (
                      <div className="space-y-1">
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${transcribeAnimProgress}%` }}
                          />
                        </div>
                        <p className="text-xs text-gray-500">{transcribeMessage}</p>
                      </div>
                    )}
                  </div>
                )}
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
                  {/* AI 推荐区域 */}
                  <div className="mb-4 space-y-3">
                    <div className="flex items-center gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={handleAIRecommend}
                        disabled={isRecommending || isProcessing}
                      >
                        <Sparkles className="w-4 h-4 mr-2" />
                        {isRecommending
                          ? recommendTotalBatches > 0
                            ? `分析中 ${recommendBatch}/${recommendTotalBatches}`
                            : 'AI 分析中...'
                          : 'AI 推荐'}
                      </Button>
                      {recommendations && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={selectRecommended}
                        >
                          仅选推荐
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowPromptEditor(!showPromptEditor)}
                      >
                        {showPromptEditor ? (
                          <ChevronUp className="w-4 h-4 mr-1" />
                        ) : (
                          <ChevronDown className="w-4 h-4 mr-1" />
                        )}
                        提示词
                      </Button>
                    </div>

                    {showPromptEditor && (
                      <div className="space-y-3">
                        <div className="flex items-center gap-3">
                          <div className="w-32">
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              每批数量
                            </label>
                            <input
                              type="number"
                              min={1}
                              max={100}
                              value={recommendBatchSize}
                              onChange={(e) => setRecommendBatchSize(parseInt(e.target.value) || 30)}
                              className="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                              disabled={isRecommending}
                            />
                          </div>
                          <span className="text-xs text-gray-400 mt-5">1-100，越大越快但可能超时</span>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            自定义提示词（描述 AI 如何筛选有价值的学习材料）
                          </label>
                          <textarea
                            value={customPrompt}
                            onChange={(e) => setCustomPrompt(e.target.value)}
                            rows={6}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm font-mono"
                            placeholder="输入自定义提示词..."
                            disabled={isRecommending}
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  <SubtitleTable
                    subtitles={subtitles}
                    selectedIndices={selectedIndices}
                    onToggleSelection={toggleSelection}
                    onSelectAll={toggleSelectAll}
                    isAllSelected={selectedIndices.size === subtitles.length}
                    recommendations={recommendations}
                    isRecommending={isRecommending}
                    recommendBatch={recommendBatch}
                    recommendTotalBatches={recommendTotalBatches}
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

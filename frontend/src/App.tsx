import { useState, useEffect } from 'react';
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
  { id: 'ai', label: 'AI 智能筛选', status: 'pending' as const },
  { id: 'media', label: '切割音频与截图', status: 'pending' as const },
  { id: 'pack', label: '打包 Anki 牌组', status: 'pending' as const },
];

const DEFAULT_RECOMMEND_PROMPT = `你是英语学习教材编写专家。对输入的字幕列表，每条判断是否值得作为学习材料：

判断标准：
- 有明确的语法知识点（如时态、从句、虚拟语气等）
- 有实用表达或固定搭配
- 对话内容有意义（非简单寒暄如'okay', 'yeah', 'uh-huh'等）
- 有文化背景或情境意义

返回格式（JSON对象）：
{"items": [{"index": 数字, "include": true/false, "reason": "简短原因", "translation": "中文翻译", "notes": "重点词汇-释义"}, ...]}

注意：
- 必须返回一个 JSON 对象，items 是数组
- include=true 表示值得加入学习
- include=false 时 reason 说明原因（如：纯简单应答、无知识价值）
- 只对 include=true 的句子提供 translation 和 notes
- 保持原文顺序输出，每条都必须有 index 字段`;

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
  const [customPrompt, setCustomPrompt] = useState(DEFAULT_RECOMMEND_PROMPT);
  const [showPromptEditor, setShowPromptEditor] = useState(false);

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

    try {
      const response = await subtitleAPI.recommend(
        subtitles,
        apiKey,
        customPrompt || undefined
      );

      const map = new Map<number, AIRecommendation>();
      response.recommendations.forEach(r => map.set(r.index, r));
      setRecommendations(map);

      // 自动选中推荐的句子
      const recommendedIndices = response.recommendations
        .filter(r => r.include)
        .map(r => r.index);
      setSelectedIndices(new Set(recommendedIndices));
    } catch (error) {
      console.error('AI 推荐失败:', error);
      alert('AI 推荐失败: ' + (error instanceof Error ? error.message : '未知错误'));
    } finally {
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
    if (!videoFile || !subtitleFile) {
      alert('请先上传视频和字幕文件');
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
                        {isRecommending ? 'AI 分析中...' : 'AI 推荐'}
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

import { useState, useEffect, useRef } from 'react';
import { Film, Download, Settings, Info, Sparkles, ChevronDown, ChevronUp, MessageSquare, Sun, Moon, Monitor } from 'lucide-react';
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
import { useTheme } from './hooks/useTheme';

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

type StepStatus = 'pending' | 'processing' | 'completed' | 'error';
type ProcessingStep = { id: string; label: string; status: StepStatus; error?: string };

const PROCESSING_STEPS: ProcessingStep[] = [
  { id: 'upload', label: '上传文件', status: 'pending' },
  { id: 'parse', label: '解析字幕', status: 'pending' },
  { id: 'ai', label: 'AI 智能注释', status: 'pending' },
  { id: 'media', label: '切割音频与截图', status: 'pending' },
  { id: 'pack', label: '打包 Anki 牌组', status: 'pending' },
];

const PRESETS = {
  grammar: {
    label: '语法句型',
    prompt: `你是英语学习教材编写专家。对输入的字幕列表，每条判断是否值得作为学习材料：

判断标准：
- 有明确的语法知识点（如时态、从句、虚拟语气等）
- 有实用表达或固定搭配
- 对话内容有意义（非简单寒暄如'okay', 'yeah', 'uh-huh'等）
- 有文化背景或情境意义`,
  },
  vocab: {
    label: '背单词',
    prompt: `你是英语词汇教学专家。对输入的字幕列表，每条判断是否值得作为单词学习材料：

判断标准：
- 句子中包含高频核心词汇或学术词汇（如 TOEFL/IELTS/GRE 词汇）
- 包含值得掌握的动词短语、介词搭配或习语
- 包含一词多义、熟词僻义的实际用例
- 单词在语境中有助于理解和记忆
- 对话内容有意义（非简单寒暄如'okay', 'yeah', 'uh-huh'等）

对于 include=true 的句子，notes 字段需标注：重点单词-词性-释义，如遇词组则整体标注`,
  },
} as const;

type PresetKey = keyof typeof PRESETS;

const DEFAULT_RECOMMEND_PROMPT = PRESETS.grammar.prompt;

// 从 localStorage 读取 AI 配置（持久化）
function loadAIConfig() {
  try {
    const raw = localStorage.getItem('anki_ai_config');
    if (raw) return JSON.parse(raw);
  } catch {}
  return null;
}

function App() {
  const { theme, toggleTheme } = useTheme();
  const savedConfig = loadAIConfig();
  const [apiBase, setApiBase] = useState(savedConfig?.apiBase || 'https://api.deepseek.com');
  const [modelName, setModelName] = useState(savedConfig?.modelName || 'deepseek-chat');
  const [apiKey, setApiKey] = useState(savedConfig?.apiKey || '');
  const [configExpanded, setConfigExpanded] = useState(!savedConfig); // 首次展开
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ valid: boolean; message: string } | null>(null);
  const [modelList, setModelList] = useState<string[] | null>(null);
  const [minDuration, setMinDuration] = useState(1.0);
  const [paddingStartMs, setPaddingStartMs] = useState(200);
  const [paddingEndMs, setPaddingEndMs] = useState(200);
  const [whisperModel, setWhisperModel] = useState('base');
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [checkingEmbedded, setCheckingEmbedded] = useState(false);
  const [embeddedStreams, setEmbeddedStreams] = useState<Array<{ index: number; codec: string; language: string; title: string; text_based: boolean }>>([]);
  const [extractedSource, setExtractedSource] = useState('');

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
  const [helpTab, setHelpTab] = useState<'basic' | 'advanced'>('basic');

  // AI 推荐相关
  const [recommendations, setRecommendations] = useState<Map<number, AIRecommendation> | null>(null);
  const [failedIndices, setFailedIndices] = useState<Set<number>>(new Set());
  const [isRecommending, setIsRecommending] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const transcribingRef = useRef(false);
  const transcribedVideoName = useRef<string | null>(null);
  const [transcribeStep, setTranscribeStep] = useState(0);
  const [, setTranscribeTotalSteps] = useState(4);
  const [transcribeMessage, setTranscribeMessage] = useState('');
  const [transcribeAnimProgress, setTranscribeAnimProgress] = useState(0);
  const transcribeAnimRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // OCR 提取状态
  const [isOcrExtracting, setIsOcrExtracting] = useState(false);
  const [ocrStep, setOcrStep] = useState(0);
  const [ocrTotalSteps, setOcrTotalSteps] = useState(3);
  const [ocrMessage, setOcrMessage] = useState('');
  const ocrPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [recommendBatch, setRecommendBatch] = useState(0);
  const [recommendTotalBatches, setRecommendTotalBatches] = useState(0);
  const [customPrompt, setCustomPrompt] = useState<string>(DEFAULT_RECOMMEND_PROMPT);
  const [promptPreset, setPromptPreset] = useState<PresetKey>('grammar');
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

  // AI 配置变化时自动保存到 localStorage
  useEffect(() => {
    localStorage.setItem('anki_ai_config', JSON.stringify({ apiBase, modelName, apiKey }));
  }, [apiBase, modelName, apiKey]);

  // 转录/OCR 进度动画
  const [ocrAnimProgress, setOcrAnimProgress] = useState(0);
  const ocrAnimRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const stepBase = [0, 10, 30, 100];

    if (!isTranscribing) {
      setTranscribeAnimProgress(0);
      if (transcribeAnimRef.current) clearInterval(transcribeAnimRef.current);
      return;
    }

    const base = stepBase[transcribeStep] || 0;
    setTranscribeAnimProgress(base);

    if (transcribeStep === 2) {
      transcribeAnimRef.current = setInterval(() => {
        setTranscribeAnimProgress(prev => {
          if (prev < 30) return 30;
          if (prev >= 94) return 94;
          return Math.min(94, prev + 0.3);
        });
      }, 1000);
    } else {
      if (transcribeAnimRef.current) clearInterval(transcribeAnimRef.current);
    }

    return () => {
      if (transcribeAnimRef.current) clearInterval(transcribeAnimRef.current);
    };
  }, [isTranscribing, transcribeStep]);

  useEffect(() => {
    const stepBase = [0, 10, 50, 100];

    if (!isOcrExtracting) {
      setOcrAnimProgress(0);
      if (ocrAnimRef.current) clearInterval(ocrAnimRef.current);
      return;
    }

    const base = stepBase[ocrStep] || 0;
    setOcrAnimProgress(base);

    if (ocrStep === 1) {
      ocrAnimRef.current = setInterval(() => {
        setOcrAnimProgress(prev => {
          if (prev < 50) return 50;
          if (prev >= 94) return 94;
          return Math.min(94, prev + 0.4);
        });
      }, 1000);
    } else {
      if (ocrAnimRef.current) clearInterval(ocrAnimRef.current);
    }

    return () => {
      if (ocrAnimRef.current) clearInterval(ocrAnimRef.current);
    };
  }, [isOcrExtracting, ocrStep]);

  // 清理所有轮询
  useEffect(() => {
    return () => {
      if (ocrPollRef.current) clearInterval(ocrPollRef.current);
    };
  }, []);

  // 测试 AI 连接
  const handleTestConnection = async () => {
    if (!apiKey) return;
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await processAPI.testConnection(apiKey, apiBase, modelName);
      setTestResult(res);
    } catch {
      setTestResult({ valid: false, message: '请求失败，请检查 API 地址' });
    }
    setIsTesting(false);
  };

  // 获取模型列表
  const handleListModels = async () => {
    if (!apiKey) return;
    try {
      const res = await processAPI.listModels(apiKey, apiBase);
      setModelList(res.models);
    } catch {
      setModelList([]);
    }
  };

  const WHISPER_MODELS = [
    { key: 'tiny',  label: 'tiny',   size: '~75 MB',  speed: '最快，精度最低' },
    { key: 'base',  label: 'base',   size: '~145 MB', speed: '较快，日常够用' },
    { key: 'small', label: 'small',  size: '~488 MB', speed: '中等，精度较好' },
    { key: 'medium',label: 'medium', size: '~1.5 GB', speed: '较慢，精度高' },
    { key: 'large', label: 'large',  size: '~2.9 GB', speed: '最慢，精度最高' },
  ];

  // 生成字幕 — 方案链：软字幕 > OCR 硬字幕 > Whisper 转录
  const handleTranscribe = async () => {
    if (!videoFile || transcribingRef.current) return;
    if (transcribedVideoName.current === videoFile.name) return;

    setCheckingEmbedded(true);
    setEmbeddedStreams([]);
    setExtractedSource('');

    try {
      // 第一优先：提取内嵌软字幕
      const result = await subtitleAPI.extractEmbeddedSubs(videoFile, 0, minDuration);
      setEmbeddedStreams(result.streams);

      if (result.found && result.extracted) {
        setSubtitles(result.extracted.subtitles as SubtitleItem[]);
        setSelectedIndices(new Set(result.extracted.subtitles.map((s: SubtitleItem) => s.index)));
        setRecommendations(null);
        transcribedVideoName.current = videoFile.name;
        setExtractedSource(`从视频提取（${result.extracted.codec} / ${result.extracted.language}，${result.extracted.total} 条）`);
        setCheckingEmbedded(false);
        return;
      }

      // 第二优先：检测可见硬字幕 → OCR 识别
      if (!result.found || !result.extracted) {
        setCheckingEmbedded(false);
        try {
          const detectResult = await subtitleAPI.detectVisibleSubs(videoFile);
          if (detectResult.has_visible_subtitles) {
            // 启动 OCR 提取（异步轮询）
            await startOcrExtract();
            return;
          }
        } catch (_) {
          // 检测失败，继续走 Whisper
        }
      } else if (result.found && !result.extracted) {
        alert(result.message);
      }
    } catch (e) {
      console.error('检测字幕失败:', e);
    }

    setCheckingEmbedded(false);
    setShowModelPicker(true);
  };

  // OCR 提取硬字幕
  const startOcrExtract = async () => {
    if (!videoFile) return;

    setIsOcrExtracting(true);
    setOcrStep(0);
    setOcrTotalSteps(3);
    setOcrMessage('准备 OCR 识别...');

    try {
      const { task_id } = await subtitleAPI.startOcrExtract(videoFile, 'ch', 1.0, minDuration);

      const pollInterval = setInterval(async () => {
        try {
          const progress = await subtitleAPI.getOcrProgress(task_id);

          setOcrStep(progress.step);
          setOcrTotalSteps(progress.total_steps);
          setOcrMessage(progress.message);

          if (progress.status === 'completed' && progress.result) {
            clearInterval(pollInterval);
            setIsOcrExtracting(false);

            setSubtitles(progress.result.subtitles as SubtitleItem[]);
            setSelectedIndices(new Set(progress.result.subtitles.map((s: SubtitleItem) => s.index)));
            setRecommendations(null);
            transcribedVideoName.current = videoFile.name;
            setExtractedSource(`OCR 硬字幕识别（${progress.result.filtered} 条）`);
          }

          if (progress.status === 'error') {
            clearInterval(pollInterval);
            setIsOcrExtracting(false);
            // OCR 失败，降级到 Whisper
            setShowModelPicker(true);
          }
        } catch (_) {
          // 轮询失败不中断
        }
      }, 1000);

      ocrPollRef.current = pollInterval;

    } catch (error) {
      console.error('OCR 提取失败:', error);
      setIsOcrExtracting(false);
      setShowModelPicker(true);
    }
  };

  // 确认模型后开始转录
  const startTranscribe = async () => {
    if (!videoFile || transcribingRef.current) return;

    setShowModelPicker(false);
    transcribingRef.current = true;
    setIsTranscribing(true);
    setTranscribeStep(0);
    setTranscribeTotalSteps(4);
    setTranscribeMessage('准备转录...');

    try {
      const { task_id } = await subtitleAPI.startTranscribe(videoFile, minDuration, undefined, whisperModel);

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
    if (selectedIndices.size === 0) {
      alert('请先勾选需要分析的句子');
      return;
    }

    setIsRecommending(true);
    setRecommendations(new Map());
    setFailedIndices(new Set());
    setRecommendBatch(0);
    setRecommendTotalBatches(0);

    try {
      const stream = subtitleAPI.startRecommendStream(
        subtitles.filter(s => selectedIndices.has(s.index)),
        apiKey,
        customPrompt || undefined,
        recommendBatchSize,
        apiBase || undefined,
        modelName || undefined
      );

      for await (const event of stream) {
        if (event.type === 'start') {
          setRecommendTotalBatches(event.total_batches!);
        } else if (event.type === 'batch') {
          setRecommendBatch(event.batch!);
          // 增量更新 recommendations
          setRecommendations(prev => {
            const next = new Map(prev);
            for (const item of event.items!) {
              next.set(item.index, item);
            }
            return next;
          });
        } else if (event.type === 'done') {
          setIsRecommending(false);
        }
      }

      // 流结束后，收集失败项并自动选中推荐的句子
      setRecommendations(prev => {
        if (prev.size > 0) {
          // 收集失败项
          const failed = new Set<number>();
          for (const [index, rec] of prev) {
            if (rec.reason.startsWith('处理失败:')) {
              failed.add(index);
            }
          }
          setFailedIndices(failed);

          // 自动选中推荐的句子（排除失败项）
          const recommendedIndices = Array.from(prev.values())
            .filter(r => r.include && !r.reason.startsWith('处理失败:'))
            .map(r => r.index);
          setSelectedIndices(new Set(recommendedIndices));
        }
        return prev;
      });

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

  // 重试失败的批次
  const handleRetryFailed = async () => {
    if (!apiKey || failedIndices.size === 0) return;

    const failedSubtitles = subtitles.filter(s => failedIndices.has(s.index));
    if (failedSubtitles.length === 0) return;

    setIsRecommending(true);
    setFailedIndices(new Set());
    setRecommendBatch(0);
    setRecommendTotalBatches(0);

    try {
      const stream = subtitleAPI.startRecommendStream(
        failedSubtitles,
        apiKey,
        customPrompt || undefined,
        recommendBatchSize,
        apiBase || undefined,
        modelName || undefined
      );

      for await (const event of stream) {
        if (event.type === 'start') {
          setRecommendTotalBatches(event.total_batches!);
        } else if (event.type === 'batch') {
          setRecommendBatch(event.batch!);
          setRecommendations(prev => {
            const next = new Map(prev);
            for (const item of event.items!) {
              next.set(item.index, item);
            }
            return next;
          });
        } else if (event.type === 'done') {
          setIsRecommending(false);
        }
      }

      // 重试后更新失败列表
      setRecommendations(prev => {
        if (prev.size > 0) {
          const failed = new Set<number>();
          for (const [index, rec] of prev) {
            if (rec.reason.startsWith('处理失败:')) {
              failed.add(index);
            }
          }
          setFailedIndices(failed);
        }
        return prev;
      });

    } catch (error) {
      console.error('重试失败:', error);
      alert('重试失败: ' + (error instanceof Error ? error.message : '未知错误'));
      setIsRecommending(false);
    }
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

    // 构建预处理数据
    // 有 AI 推荐时使用推荐结果，无推荐时使用空翻译/注释（跳过后端 AI 步骤）
    const preProcessed = subtitles
      .filter(s => selectedIndices.has(s.index))
      .map(s => {
        const rec = recommendations?.get(s.index);
        return {
          index: s.index,
          text: s.text,
          translation: rec?.translation || '',
          notes: rec?.notes || '',
          reason: rec?.reason || ''
        };
      });

    try {
      // 1. 上传并启动后台处理
      const { task_id } = await processAPI.uploadAndProcess(
        videoFile,
        selectedSubtitleFile,
        minDuration,
        apiKey || undefined,
        preProcessed,
        apiBase || undefined,
        modelName || undefined,
        paddingStartMs,
        paddingEndMs
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
              s.map((step) =>
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
        s.map((step) =>
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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* 顶部导航 */}
      <nav className="bg-white border-b border-gray-200 dark:bg-gray-800 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <Film className="w-8 h-8 text-primary-600" />
              <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">Anki 卡片生成器</h1>
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
              <Button
                variant="ghost"
                size="sm"
                onClick={() => window.open('https://github.com/qinusui/anki-maker/issues', '_blank')}
              >
                <MessageSquare className="w-4 h-4 mr-2" />
                反馈
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleTheme}
                title={theme === 'system' ? '跟随系统' : theme === 'light' ? '浅色模式' : '深色模式'}
              >
                {theme === 'system' ? <Monitor className="w-4 h-4" /> : theme === 'light' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
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
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-semibold">使用说明</h3>
                <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5 dark:bg-gray-700">
                  <button
                    onClick={() => setHelpTab('basic')}
                    className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      helpTab === 'basic'
                        ? 'bg-white text-gray-900 shadow dark:bg-gray-600 dark:text-gray-100'
                        : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                    }`}
                  >
                    基础
                  </button>
                  <button
                    onClick={() => setHelpTab('advanced')}
                    className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      helpTab === 'advanced'
                        ? 'bg-white text-gray-900 shadow dark:bg-gray-600 dark:text-gray-100'
                        : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                    }`}
                  >
                    进阶
                  </button>
                </div>
              </div>

              {helpTab === 'basic' ? (
                <ol className="list-decimal list-inside space-y-2 text-gray-700 dark:text-gray-300">
                  <li>上传视频文件（.mp4 / .mkv / .avi）和字幕文件（.srt），或点击「生成字幕」自动转录</li>
                  <li>勾选目标句子，点击「开始处理」等待生成卡片</li>
                  <li>预览卡片，下载 .apkg 文件导入 Anki</li>
                </ol>
              ) : (
                <div className="space-y-4 text-sm text-gray-700 dark:text-gray-300">
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-1 dark:text-gray-100">基础功能（无需 AI）</h4>
                    <ul className="list-disc list-inside space-y-1 ml-2">
                      <li>上传视频和字幕，手动勾选句子即可生成卡片</li>
                      <li>卡片包含：原文、对应音频片段和视频截图</li>
                      <li>可调整最短时长、音频头尾 padding 等参数</li>
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-1 dark:text-gray-100">AI 进阶功能（可选）</h4>
                    <ul className="list-disc list-inside space-y-1 ml-2">
                      <li>配置 AI 后可使用「AI 推荐」智能筛选有学习价值的句子</li>
                      <li>AI 自动翻译并生成词汇注释，卡片额外包含中文翻译和知识点</li>
                      <li>支持 OpenAI / DeepSeek / Ollama 等兼容接口</li>
                      <li>配置自动保存到浏览器，刷新无需重新填写</li>
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-1 dark:text-gray-100">字幕获取</h4>
                    <ul className="list-disc list-inside space-y-1 ml-2">
                      <li>上传 .srt 字幕文件，或仅上传视频点击「生成字幕」使用 Whisper 转录</li>
                      <li>Whisper 模型可选 tiny / base / small / medium / large，越大越准但越慢</li>
                      <li>转录支持中/英/日等多语言，默认自动检测</li>
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-1 dark:text-gray-100">卡片生成</h4>
                    <ul className="list-disc list-inside space-y-1 ml-2">
                      <li>音频切割有 ±0.2s padding，先整体提取音轨再切片，高效不突兀</li>
                      <li>支持预览前后翻页，下载 .apkg 后导入 Anki 即可背诵</li>
                    </ul>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        <div className="space-y-8">
          {/* Step 1 · 准备素材 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="bg-primary-100 text-primary-700 rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold dark:bg-primary-900/40 dark:text-primary-300">1</span>
                准备素材
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* 左侧：文件上传 */}
                <div className="lg:col-span-2 space-y-4">
                  <FileUpload
                    accept=".mp4,.mkv,.avi,.mov,.webm"
                    onFileSelect={(f) => { setVideoFile(f); transcribedVideoName.current = null; setExtractedSource(''); setIsOcrExtracting(false); if (ocrPollRef.current) clearInterval(ocrPollRef.current); }}
                    selectedFile={videoFile}
                    onClear={() => { setVideoFile(null); transcribedVideoName.current = null; setExtractedSource(''); setIsOcrExtracting(false); if (ocrPollRef.current) clearInterval(ocrPollRef.current); }}
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
                      {/* 已提取内嵌字幕 */}
                      {extractedSource && (
                        <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 px-3 py-2 rounded border border-green-200 dark:text-green-400 dark:bg-green-900/30 dark:border-green-800">
                          <span className="flex-1">{extractedSource}</span>
                          <button
                            className="text-xs text-gray-500 underline hover:text-gray-700 shrink-0 dark:text-gray-400 dark:hover:text-gray-200"
                            onClick={() => { setExtractedSource(''); setIsOcrExtracting(false); setShowModelPicker(true); if (ocrPollRef.current) clearInterval(ocrPollRef.current); }}
                          >
                            改用 Whisper 转录
                          </button>
                        </div>
                      )}
                      {/* 未提取时显示生成按钮或进度 */}
                      {!extractedSource && (
                        <>
                          {!isOcrExtracting && (
                            <Button
                              variant="primary"
                              className="w-full"
                              onClick={handleTranscribe}
                              disabled={!videoFile || isProcessing || isTranscribing || checkingEmbedded || isOcrExtracting}
                            >
                              {checkingEmbedded ? '检测字幕中...' : isTranscribing ? '转录中...' : '生成字幕'}
                            </Button>
                          )}
                          {/* OCR 进度条 */}
                          {isOcrExtracting && (
                            <div className="space-y-1">
                              <div className="w-full bg-gray-200 rounded-full h-2 dark:bg-gray-600">
                                <div
                                  className="bg-green-500 h-2 rounded-full transition-all duration-300"
                                  style={{ width: `${ocrAnimProgress}%` }}
                                />
                              </div>
                              <p className="text-xs text-gray-500 dark:text-gray-400">{ocrMessage}</p>
                            </div>
                          )}
                        </>
                      )}
                      {showModelPicker && !isTranscribing && !isOcrExtracting && (
                        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 space-y-3 dark:border-gray-600 dark:bg-gray-800">
                          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">选择 Whisper 模型（首次使用会自动下载）</p>
                          <div className="space-y-2">
                            {WHISPER_MODELS.map(m => (
                              <label
                                key={m.key}
                                className={`flex items-center gap-3 p-2 rounded cursor-pointer border transition-colors ${
                                  whisperModel === m.key
                                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30 dark:border-primary-400'
                                    : 'border-gray-200 hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-gray-700'
                                }`}
                              >
                                <input
                                  type="radio"
                                  name="whisperModel"
                                  value={m.key}
                                  checked={whisperModel === m.key}
                                  onChange={() => setWhisperModel(m.key)}
                                  className="w-4 h-4 text-primary-600"
                                />
                                <div className="flex-1">
                                  <span className="font-medium text-sm">{m.label}</span>
                                  <span className="text-xs text-gray-500 ml-2 dark:text-gray-400">{m.size}</span>
                                </div>
                                <span className="text-xs text-gray-400 dark:text-gray-500">{m.speed}</span>
                              </label>
                            ))}
                          </div>
                          <div className="flex gap-2">
                            <Button variant="primary" size="sm" onClick={startTranscribe}>
                              开始转录
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => setShowModelPicker(false)}>
                              取消
                            </Button>
                          </div>
                        </div>
                      )}
                      {isTranscribing && (
                        <div className="space-y-1">
                          <div className="w-full bg-gray-200 rounded-full h-2 dark:bg-gray-600">
                            <div
                              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${transcribeAnimProgress}%` }}
                            />
                          </div>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{transcribeMessage}</p>
                        </div>
                      )}
                    </div>
                  )}
                  {/* 字幕处理配置 */}
                  <div className="p-4 bg-gray-50 rounded-lg space-y-3 dark:bg-gray-800">
                    <div className="text-xs font-medium text-gray-600 dark:text-gray-400">字幕处理配置</div>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1 dark:text-gray-400">最短时长(s)</label>
                        <input
                          type="number"
                          step="0.1"
                          min="0.5"
                          max="5"
                          value={minDuration}
                          onChange={(e) => setMinDuration(parseFloat(e.target.value))}
                          className="w-full px-2 py-1.5 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1 dark:text-gray-400">开头提前(ms)</label>
                        <input
                          type="number"
                          step="100"
                          min="100"
                          max="1000"
                          value={paddingStartMs}
                          onChange={(e) => setPaddingStartMs(parseInt(e.target.value) || 200)}
                          className="w-full px-2 py-1.5 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1 dark:text-gray-400">结尾延后(ms)</label>
                        <input
                          type="number"
                          step="100"
                          min="100"
                          max="1000"
                          value={paddingEndMs}
                          onChange={(e) => setPaddingEndMs(parseInt(e.target.value) || 200)}
                          className="w-full px-2 py-1.5 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* 右侧：AI 配置 */}
                <div className="space-y-4">
                  <div className="text-sm font-medium text-gray-700 dark:text-gray-300">AI 配置</div>
                  {/* 折叠时显示摘要 */}
                  {!configExpanded && (
                    <div
                      className="flex items-center justify-between cursor-pointer p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors dark:bg-gray-800 dark:hover:bg-gray-700"
                      onClick={() => setConfigExpanded(true)}
                    >
                      <span className="text-sm text-gray-600 truncate dark:text-gray-400">
                        {apiBase.replace(/^https?:\/\//, '')} / {modelName}
                        {apiKey ? ` / ***${apiKey.slice(-4)}` : ' / 未设置 Key'}
                      </span>
                      <ChevronDown className="w-4 h-4 text-gray-400 shrink-0 dark:text-gray-500" />
                    </div>
                  )}
                  {/* 展开时显示完整配置 */}
                  {configExpanded && (
                    <div className="space-y-3 p-4 bg-gray-50 rounded-lg dark:bg-gray-800">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1 dark:text-gray-400">API 地址</label>
                        <input
                          type="text"
                          value={apiBase}
                          onChange={(e) => setApiBase(e.target.value)}
                          placeholder="https://api.deepseek.com"
                          className="w-full px-2 py-1.5 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1 dark:text-gray-400">模型名称</label>
                        <input
                          type="text"
                          value={modelName}
                          onChange={(e) => setModelName(e.target.value)}
                          placeholder="deepseek-chat"
                          className="w-full px-2 py-1.5 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1 dark:text-gray-400">API Key</label>
                        <input
                          type="password"
                          value={apiKey}
                          onChange={(e) => { setApiKey(e.target.value); setTestResult(null); }}
                          placeholder="输入你的 API Key"
                          className="w-full px-2 py-1.5 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                        />
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={handleTestConnection}
                          disabled={isTesting || !apiKey}
                        >
                          {isTesting ? '测试中...' : '测试连接'}
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={handleListModels}
                          disabled={!apiKey}
                        >
                          模型列表
                        </Button>
                      </div>
                      {testResult && (
                        <p className={`text-xs ${testResult.valid ? 'text-green-600' : 'text-red-600'}`}>
                          {testResult.message}
                        </p>
                      )}
                      {modelList && modelList.length > 0 && (
                        <div className="max-h-24 overflow-y-auto border border-gray-200 rounded p-1 dark:border-gray-600">
                          {modelList.map(m => (
                            <button
                              key={m}
                              onClick={() => { setModelName(m); setModelList(null); }}
                              className={`block w-full text-left px-2 py-1 text-xs rounded hover:bg-gray-100 dark:hover:bg-gray-700 ${
                                m === modelName ? 'bg-primary-50 text-primary-700 font-medium dark:bg-primary-900/30 dark:text-primary-300' : 'text-gray-600 dark:text-gray-400'
                              }`}
                            >
                              {m}
                            </button>
                          ))}
                        </div>
                      )}
                      {modelList && modelList.length === 0 && (
                        <p className="text-xs text-red-500">获取模型列表失败，并不影响使用</p>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full"
                        onClick={() => setConfigExpanded(false)}
                      >
                        <ChevronUp className="w-4 h-4 mr-1" />
                        收起配置
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Step 2 · 筛选内容 */}
          {subtitles.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <span className="bg-primary-100 text-primary-700 rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold dark:bg-primary-900/40 dark:text-primary-300">2</span>
                  筛选内容
                  <span className="text-sm font-normal text-gray-500 ml-2 dark:text-gray-400">
                    (已选 {selectedIndices.size} / {subtitles.length})
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {/* 工具栏 */}
                <div className="flex items-center gap-2 mb-4">
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
                  {failedIndices.size > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleRetryFailed}
                      disabled={isRecommending}
                      className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                    >
                      重试失败 ({failedIndices.size})
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

                {/* 提示词编辑器 */}
                {showPromptEditor && (
                  <div className="mb-4 p-4 bg-gray-50 rounded-lg space-y-3 dark:bg-gray-800">
                    <div className="flex items-center gap-3">
                      <div className="w-32">
                        <label className="block text-xs font-medium text-gray-600 mb-1 dark:text-gray-400">每批数量</label>
                        <input
                          type="number"
                          min={1}
                          max={100}
                          value={recommendBatchSize}
                          onChange={(e) => setRecommendBatchSize(parseInt(e.target.value) || 30)}
                          className="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                          disabled={isRecommending}
                        />
                      </div>
                      <span className="text-xs text-gray-400 mt-4 dark:text-gray-500">1-100，越大越快但可能超时</span>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1 dark:text-gray-400">提示词预设</label>
                      <div className="flex gap-2">
                        {(Object.keys(PRESETS) as PresetKey[]).map((key) => (
                          <button
                            key={key}
                            onClick={() => {
                              setPromptPreset(key);
                              setCustomPrompt(PRESETS[key].prompt);
                            }}
                            disabled={isRecommending}
                            className={`px-3 py-1.5 rounded text-sm font-medium border transition-colors ${
                              promptPreset === key
                                ? 'bg-primary-500 text-white border-primary-500'
                                : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-600'
                            }`}
                          >
                            {PRESETS[key].label}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1 dark:text-gray-400">提示词内容（可自由修改）</label>
                      <textarea
                        value={customPrompt}
                        onChange={(e) => setCustomPrompt(e.target.value)}
                        rows={4}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm font-mono dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                        placeholder="输入自定义提示词..."
                        disabled={isRecommending}
                      />
                    </div>
                  </div>
                )}

                {/* 字幕表格 - 全宽 */}
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

                {/* 底部按钮 */}
                <Button
                  variant="primary"
                  className="w-full mt-4"
                  onClick={handleProcess}
                  disabled={selectedIndices.size === 0 || isProcessing || !videoFile || isRecommending}
                >
                  开始处理 ({selectedIndices.size} 条)
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Step 3 · 生成卡片 */}
          {(isProcessing || (result && result.length > 0)) && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <span className="bg-primary-100 text-primary-700 rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold dark:bg-primary-900/40 dark:text-primary-300">3</span>
                  生成卡片
                </CardTitle>
              </CardHeader>
              <CardContent>
                {/* 处理进度 */}
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

                {/* 卡片预览 */}
                {result && result.length > 0 && (
                  <div className="mt-6">
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
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;

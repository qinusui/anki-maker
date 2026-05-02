import axios from 'axios';
import type { SubtitleListResponse, ProcessResult, ProcessedCard, SubtitleItem, AIRecommendResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 字幕相关 API
export const subtitleAPI = {
  // 上传字幕文件
  upload: async (file: File, minDuration: number = 1.0): Promise<SubtitleListResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<SubtitleListResponse>(
      `/api/subtitles/upload?min_duration=${minDuration}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  },

  // Whisper 转录：启动任务
  startTranscribe: async (
    video: File,
    minDuration: number = 1.0,
    language?: string,
    modelName?: string
  ): Promise<{ task_id: string; status: string }> => {
    const formData = new FormData();
    formData.append('video', video);
    const params = new URLSearchParams();
    params.append('min_duration', minDuration.toString());
    if (language) params.append('language', language);
    if (modelName) params.append('model_name', modelName);

    const response = await api.post<{ task_id: string; status: string }>(
      `/api/subtitles/transcribe?${params.toString()}`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 600000 }
    );
    return response.data;
  },

  // Whisper 转录：获取进度
  getTranscribeProgress: async (taskId: string) => {
    const response = await api.get(`/api/subtitles/transcribe/progress/${taskId}`);
    return response.data as {
      status: string;
      step: number;
      total_steps: number;
      message: string;
      error?: string;
      result?: SubtitleListResponse;
    };
  },

  // 获取示例字幕
  getExample: async (): Promise<SubtitleListResponse> => {
    const response = await api.get<SubtitleListResponse>('/api/subtitles/example');
    return response.data;
  },

  // AI 推荐：启动任务
  startRecommend: async (
    subtitles: SubtitleItem[],
    apiKey?: string,
    customPrompt?: string,
    batchSize?: number,
    apiBase?: string,
    modelName?: string
  ): Promise<{ task_id: string; status: string }> => {
    const response = await api.post<{ task_id: string; status: string }>(
      '/api/subtitles/ai-recommend',
      { subtitles, api_key: apiKey || undefined, custom_prompt: customPrompt || undefined,
        batch_size: batchSize ?? 30, api_base: apiBase || undefined, model_name: modelName || undefined }
    );
    return response.data;
  },

  // AI 推荐：获取进度
  getRecommendProgress: async (taskId: string) => {
    const response = await api.get(`/api/subtitles/ai-recommend/progress/${taskId}`);
    return response.data as {
      status: string;
      batch: number;
      total_batches: number;
      message: string;
      result?: AIRecommendResponse;
    };
  },
};

// 处理相关 API
export const processAPI = {
  // 上传文件并处理
  uploadAndProcess: async (
    videoFile: File,
    subtitleFile: File,
    minDuration: number = 1.0,
    apiKey?: string,
    preProcessed?: object[],
    apiBase?: string,
    modelName?: string
  ): Promise<{ task_id: string; status: string }> => {
    const formData = new FormData();
    formData.append('video', videoFile);
    formData.append('subtitle', subtitleFile);
    formData.append('min_duration', minDuration.toString());
    if (apiKey) {
      formData.append('api_key', apiKey);
    }
    if (apiBase) {
      formData.append('api_base', apiBase);
    }
    if (modelName) {
      formData.append('model_name', modelName);
    }
    if (preProcessed && preProcessed.length > 0) {
      formData.append('pre_processed', JSON.stringify(preProcessed));
    }

    const response = await api.post<{ task_id: string; status: string }>(
      '/api/process/upload-and-process',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );

    return response.data;
  },

  // 开始处理
  start: async (
    videoPath: string,
    subtitlePath: string,
    minDuration: number = 1.0,
    apiKey?: string
  ): Promise<ProcessResult> => {
    const response = await api.post<ProcessResult>('/api/process/start', null, {
      params: {
        video_file_path: videoPath,
        subtitle_file_path: subtitlePath,
        min_duration: minDuration,
        api_key: apiKey,
      },
    });

    return response.data;
  },

  // 获取处理进度
  getProgress: async (taskId: string) => {
    const response = await api.get(`/api/process/progress/${taskId}`);
    return response.data as {
      task_id: string;
      status: string;
      step: number;
      total_steps: number;
      message: string;
      details: Record<string, number> | null;
      error: string | null;
      result: ProcessResult | null;
    };
  },

  // 清理输出文件
  cleanup: async (apkgFilename: string) => {
    const response = await api.post('/api/process/cleanup', null, {
      params: { apkg_filename: apkgFilename },
    });
    return response.data;
  },

  // 验证 API Key
  validateApiKey: async (apiKey: string): Promise<{ valid: boolean; message: string }> => {
    const response = await api.post<{ valid: boolean; message: string }>('/api/process/validate-api-key', null, {
      params: { api_key: apiKey },
    });
    return response.data;
  },
};

// 卡片相关 API
export const cardsAPI = {
  // 列出卡片
  list: async (apkgPath: string) => {
    const response = await api.get('/api/cards/list', {
      params: { apkg_path: apkgPath },
    });
    return response.data;
  },

  // 预览卡片
  preview: async (cards: ProcessedCard[]) => {
    const response = await api.post<{ html: string }>('/api/cards/preview', { cards });
    return response.data;
  },
};

// 健康检查
export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

export default api;

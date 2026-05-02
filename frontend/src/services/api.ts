import axios from 'axios';
import type { SubtitleListResponse, ProcessResult, ProcessProgress, ProcessedCard } from '../types';

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

  // 获取示例字幕
  getExample: async (): Promise<SubtitleListResponse> => {
    const response = await api.get<SubtitleListResponse>('/api/subtitles/example');
    return response.data;
  },
};

// 处理相关 API
export const processAPI = {
  // 开始处理
  start: async (
    videoPath: string,
    subtitlePath: string,
    minDuration: number = 1.0,
    outputDir: string = './output',
    apiKey?: string
  ): Promise<ProcessResult> => {
    const response = await api.post<ProcessResult>('/api/process/start', null, {
      params: {
        video_file_path: videoPath,
        subtitle_file_path: subtitlePath,
        min_duration: minDuration,
        output_dir: outputDir,
        api_key: apiKey,
      },
    });

    return response.data;
  },

  // 获取处理进度
  getProgress: async (taskId: string): Promise<ProcessProgress> => {
    const response = await api.get<ProcessProgress>(`/api/process/progress/${taskId}`);
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

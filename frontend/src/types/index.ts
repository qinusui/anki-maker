// API 响应类型
export interface SubtitleItem {
  index: number;
  start_sec: number;
  end_sec: number;
  text: string;
  duration: number;
  selected?: boolean;
}

export interface SubtitleListResponse {
  subtitles: SubtitleItem[];
  total: number;
  filtered: number;
}

export interface ProcessResult {
  success: boolean;
  message: string;
  cards_count: number;
  apkg_path: string | null;
  cards: ProcessedCard[];
}

export interface ProcessedCard {
  sentence: string;
  translation: string;
  notes: string;
  start_sec: number;
  end_sec: number;
  audio_path?: string;
  screenshot_path?: string;
}

export interface ProcessProgress {
  step: string;
  message: string;
  progress: number;
  total_steps: number;
  current_step: number;
}

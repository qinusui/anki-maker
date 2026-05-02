"""
Pydantic 模型定义
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SubtitleItem(BaseModel):
    """字幕条目"""
    index: int
    start_sec: float
    end_sec: float
    text: str
    duration: float = Field(default=0, description="字幕时长（秒）")

    class Config:
        json_schema_extra = {
            "example": {
                "index": 1,
                "start_sec": 83.456,
                "end_sec": 85.789,
                "text": "Hello, how are you?",
                "duration": 2.333
            }
        }


class SubtitleListResponse(BaseModel):
    """字幕列表响应"""
    subtitles: List[SubtitleItem]
    total: int
    filtered: int


class ProcessRequest(BaseModel):
    """处理请求"""
    video_path: str
    subtitle_path: str
    min_duration: float = 1.0
    output_dir: str = "./output"
    api_key: Optional[str] = None


class ProcessProgress(BaseModel):
    """处理进度"""
    step: str
    message: str
    progress: float = 0.0
    total_steps: int = 5
    current_step: int = 0


class ProcessedCard(BaseModel):
    """处理后的卡片"""
    sentence: str
    translation: str
    notes: str
    start_sec: float
    end_sec: float
    audio_path: Optional[str] = None
    screenshot_path: Optional[str] = None


class ProcessResult(BaseModel):
    """处理结果"""
    success: bool
    message: str
    cards_count: int
    apkg_path: Optional[str] = None
    cards: List[ProcessedCard] = []


class ApiKeyConfig(BaseModel):
    """API Key 配置"""
    api_key: str


class AIRecommendRequest(BaseModel):
    """AI 推荐请求"""
    subtitles: List[SubtitleItem]
    api_key: Optional[str] = None
    custom_prompt: Optional[str] = None


class AIRecommendItem(BaseModel):
    """单条推荐结果"""
    index: int
    include: bool
    reason: str
    translation: Optional[str] = None
    notes: Optional[str] = None


class AIRecommendResponse(BaseModel):
    """AI 推荐响应"""
    recommendations: List[AIRecommendItem]


class CardPreviewRequest(BaseModel):
    """卡片预览请求"""
    cards: List[ProcessedCard]

from datetime import datetime
from typing import Optional, Dict, List
from bson import ObjectId
from pydantic import BaseModel, Field
from .topic import PyObjectId


class ModelStatsBase(BaseModel):
    model_id: str
    model_name: str
    display_name: str
    
    # 总体统计
    total_debates: int = 0
    total_wins: int = 0
    total_losses: int = 0
    win_rate: float = 0.0
    
    # 各维度平均分
    avg_logic_score: float = 0.0
    avg_persuasion_score: float = 0.0
    avg_humor_score: float = 0.0
    avg_overall_score: float = 0.0
    
    # 分类统计
    category_stats: Dict[str, Dict] = {}  # {"category": {"wins": 0, "losses": 0, "win_rate": 0.0}}
    
    # 最近表现
    recent_performance: List[Dict] = []  # 最近10场辩论的结果
    
    # 风格标签（基于历史数据分析）
    style_tags: List[str] = []  # 如："aggressive", "defensive", "humorous", "logical", "emotional"


class ModelStats(ModelStatsBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "_id": "60d21b4667d0d8992e610c89",
                "model_id": "model_1",
                "model_name": "doubao-seed-1.8b-chat",
                "display_name": "豆包小模型",
                "total_debates": 100,
                "total_wins": 65,
                "total_losses": 35,
                "win_rate": 0.65,
                "avg_logic_score": 7.8,
                "avg_persuasion_score": 7.5,
                "avg_humor_score": 6.2,
                "avg_overall_score": 7.2,
                "category_stats": {
                    "technology": {"wins": 25, "losses": 15, "win_rate": 0.625},
                    "society": {"wins": 20, "losses": 10, "win_rate": 0.667},
                    "culture": {"wins": 20, "losses": 10, "win_rate": 0.667}
                },
                "recent_performance": [
                    {"debate_id": "60d21b4667d0d8992e610c86", "result": "win", "score": 8.2},
                    {"debate_id": "60d21b4667d0d8992e610c87", "result": "loss", "score": 7.1}
                ],
                "style_tags": ["logical", "conservative"],
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-15T12:00:00"
            }
        }


class RankingItem(BaseModel):
    model_id: str
    model_name: str
    display_name: str
    rank: int
    win_rate: float
    total_debates: int
    avg_overall_score: float
    style_tags: List[str]
    category_performance: Optional[Dict[str, float]] = None


class OverallRanking(BaseModel):
    updated_at: datetime
    rankings: List[RankingItem]
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class CategoryRanking(BaseModel):
    category: str
    updated_at: datetime
    rankings: List[RankingItem]
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

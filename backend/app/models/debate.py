from datetime import datetime
from typing import Optional, List, Dict, Literal
from bson import ObjectId
from pydantic import BaseModel, Field
from .topic import PyObjectId


# 辩论阶段枚举
DebateStage = Literal["waiting", "opening", "cross_examination", "closing", "voting", "finished"]


class DebateParticipant(BaseModel):
    model_id: str  # 模型配置中的ID，如 "model_1"
    model_name: str  # 火山方舟的模型名称
    display_name: str  # 显示名称
    side: Literal["affirmative", "negative"]  # 正方/反方


class DebateBase(BaseModel):
    topic_id: PyObjectId
    title: str
    participants: List[DebateParticipant]
    max_rounds: int = 5
    category: Optional[str] = "general"


class DebateCreate(DebateBase):
    pass


class Debate(DebateBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    stage: DebateStage = "waiting"
    current_round: int = 0
    current_speaker: Optional[str] = None  # 当前发言的模型ID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    viewer_count: int = 0
    message_count: int = 0
    is_active: bool = True
    
    # 投票结果（辩论结束后填充）
    vote_results: Optional[Dict] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "_id": "60d21b4667d0d8992e610c86",
                "topic_id": "60d21b4667d0d8992e610c85",
                "title": "AI是否会取代人类工作？",
                "participants": [
                    {
                        "model_id": "model_1",
                        "model_name": "doubao-seed-1.8b-chat",
                        "display_name": "豆包小模型",
                        "side": "affirmative"
                    },
                    {
                        "model_id": "model_2",
                        "model_name": "doubao-seed-12b-chat",
                        "display_name": "豆包12B模型",
                        "side": "negative"
                    }
                ],
                "max_rounds": 5,
                "category": "technology",
                "stage": "opening",
                "current_round": 1,
                "current_speaker": "model_1",
                "created_at": "2024-01-15T10:30:00",
                "started_at": "2024-01-15T10:35:00",
                "finished_at": None,
                "viewer_count": 120,
                "message_count": 3,
                "is_active": True,
                "vote_results": None
            }
        }


class DebateUpdate(BaseModel):
    stage: Optional[DebateStage] = None
    current_round: Optional[int] = None
    current_speaker: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    viewer_count: Optional[int] = None
    message_count: Optional[int] = None
    is_active: Optional[bool] = None
    vote_results: Optional[Dict] = None

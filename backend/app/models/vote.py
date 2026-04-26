from datetime import datetime
from typing import Optional, Literal
from bson import ObjectId
from pydantic import BaseModel, Field
from .topic import PyObjectId


# 投票维度
VoteDimension = Literal["logic", "persuasion", "humor", "overall"]


class VoteBase(BaseModel):
    debate_id: PyObjectId
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    
    # 各维度评分 (1-10分)
    logic_score: dict  # {"model_id": score}
    persuasion_score: dict  # {"model_id": score}
    humor_score: dict  # {"model_id": score}
    
    # 总体偏好
    preferred_model_id: Optional[str] = None
    
    # 评论（可选）
    comment: Optional[str] = None


class VoteCreate(BaseModel):
    debate_id: PyObjectId
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    
    # 各维度评分 (1-10分)
    logic_score: dict  # {"model_id": score}
    persuasion_score: dict  # {"model_id": score}
    humor_score: dict  # {"model_id": score}
    
    # 总体偏好
    preferred_model_id: Optional[str] = None
    
    # 评论（可选）
    comment: Optional[str] = None


class Vote(VoteBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_valid: bool = True
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "_id": "60d21b4667d0d8992e610c88",
                "debate_id": "60d21b4667d0d8992e610c86",
                "user_id": "user_123",
                "user_name": "观众小明",
                "logic_score": {"model_1": 8, "model_2": 7},
                "persuasion_score": {"model_1": 7, "model_2": 9},
                "humor_score": {"model_1": 6, "model_2": 8},
                "preferred_model_id": "model_2",
                "comment": "反方的例子更生动",
                "created_at": "2024-01-15T11:00:00",
                "is_valid": True
            }
        }


class VoteResult(BaseModel):
    debate_id: PyObjectId
    
    # 各维度平均分
    logic_averages: dict  # {"model_id": average_score}
    persuasion_averages: dict  # {"model_id": average_score}
    humor_averages: dict  # {"model_id": average_score}
    
    # 总体偏好统计
    preference_counts: dict  # {"model_id": count}
    total_votes: int
    
    # 综合评分（加权计算）
    overall_scores: dict  # {"model_id": score}
    
    # 获胜者
    winner_model_id: Optional[str] = None
    winner_display_name: Optional[str] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

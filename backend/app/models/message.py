from datetime import datetime
from typing import Optional, Literal
from bson import ObjectId
from pydantic import BaseModel, Field
from .topic import PyObjectId


# 消息类型枚举
MessageType = Literal["system", "model", "danmaku"]


class MessageBase(BaseModel):
    debate_id: PyObjectId
    content: str
    message_type: MessageType


class ModelMessage(MessageBase):
    message_type: Literal["model"] = "model"
    model_id: str
    model_name: str
    display_name: str
    side: Literal["affirmative", "negative"]
    round_number: int
    stage: str  # 辩论阶段：opening, cross_examination, closing


class DanmakuMessage(MessageBase):
    message_type: Literal["danmaku"] = "danmaku"
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    color: Optional[str] = "#ffffff"
    position: Optional[Literal["top", "middle", "bottom"]] = "top"


class SystemMessage(MessageBase):
    message_type: Literal["system"] = "system"
    event_type: str  # 事件类型：start, stage_change, round_change, finish, etc.
    metadata: Optional[dict] = None


class Message(MessageBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    
    # 模型消息字段
    model_id: Optional[str] = None
    model_name: Optional[str] = None
    display_name: Optional[str] = None
    side: Optional[str] = None
    round_number: Optional[int] = None
    stage: Optional[str] = None
    
    # 弹幕消息字段
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    color: Optional[str] = None
    position: Optional[str] = None
    
    # 系统消息字段
    event_type: Optional[str] = None
    metadata: Optional[dict] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "_id": "60d21b4667d0d8992e610c87",
                "debate_id": "60d21b4667d0d8992e610c86",
                "content": "大家好，我是正方代表。我认为AI会取代人类工作...",
                "message_type": "model",
                "created_at": "2024-01-15T10:30:00",
                "timestamp": 1705311000.0,
                "model_id": "model_1",
                "model_name": "doubao-seed-1.8b-chat",
                "display_name": "豆包小模型",
                "side": "affirmative",
                "round_number": 1,
                "stage": "opening",
                "user_id": None,
                "user_name": None,
                "color": None,
                "position": None,
                "event_type": None,
                "metadata": None
            }
        }


class DanmakuCreate(BaseModel):
    debate_id: PyObjectId
    content: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    color: Optional[str] = "#ffffff"
    position: Optional[Literal["top", "middle", "bottom"]] = "top"

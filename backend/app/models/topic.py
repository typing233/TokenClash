from datetime import datetime
from typing import Optional, List
from bson import ObjectId
from pydantic import BaseModel, Field


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class TopicBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = "general"
    tags: Optional[List[str]] = []
    is_auto_generated: bool = False
    source: Optional[str] = None  # 来源：如微博、知乎、Reddit等


class TopicCreate(TopicBase):
    pass


class Topic(TopicBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    debate_count: int = 0
    is_active: bool = True
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "_id": "60d21b4667d0d8992e610c85",
                "title": "AI是否会取代人类工作？",
                "description": "探讨人工智能发展对就业市场的影响",
                "category": "technology",
                "tags": ["AI", "就业", "未来"],
                "is_auto_generated": False,
                "source": None,
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-15T10:30:00",
                "debate_count": 5,
                "is_active": True
            }
        }


class TopicUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None

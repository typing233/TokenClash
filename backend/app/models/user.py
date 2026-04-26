from datetime import datetime
from typing import Optional, List
from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr
from .topic import PyObjectId


class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    display_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    is_active: bool = True
    is_admin: bool = False
    
    # 用户统计
    total_votes: int = 0
    total_danmakus: int = 0
    watched_debates: List[PyObjectId] = []
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "_id": "60d21b4667d0d8992e610c8a",
                "username": "testuser",
                "email": "user@example.com",
                "display_name": "测试用户",
                "hashed_password": "hashed_password_here",
                "created_at": "2024-01-01T00:00:00",
                "last_login": "2024-01-15T10:00:00",
                "is_active": True,
                "is_admin": False,
                "total_votes": 15,
                "total_danmakus": 50,
                "watched_debates": ["60d21b4667d0d8992e610c86"]
            }
        }


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    is_admin: bool = False

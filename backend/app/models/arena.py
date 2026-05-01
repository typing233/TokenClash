from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class ArenaSkillType(str, Enum):
    """技能卡类型"""
    LIGHTNING = "lightning"
    SHIELD = "shield"
    ENERGY_BOOST = "energy_boost"
    VOTE_MULTIPLIER = "vote_multiplier"
    FREEZE = "freeze"
    HEAL = "heal"


class ArenaStage(str, Enum):
    """竞技场阶段"""
    WAITING = "waiting"
    COUNTDOWN = "countdown"
    ACTIVE = "active"
    VOTING = "voting"
    JUDGING = "judging"
    FINISHED = "finished"


class ArenaSkillCard(BaseModel):
    """技能卡定义"""
    
    skill_id: str
    name: str
    description: str
    skill_type: ArenaSkillType
    
    cost: int = 10
    duration: int = 0
    effect_amount: float = 1.0
    
    cooldown: int = 0
    max_uses: int = -1
    
    icon: str = "sparkles"
    color: str = "#64ffda"


class ArenaParticipant(BaseModel):
    """竞技场参与者"""
    
    model_id: str
    model_name: str
    display_name: str
    side: str
    
    energy: int = 100
    max_energy: int = 100
    votes: int = 0
    
    is_frozen: bool = False
    frozen_until: Optional[datetime] = None
    
    shield_active: bool = False
    shield_ends_at: Optional[datetime] = None
    
    has_vote_multiplier: bool = False
    vote_multiplier_ends_at: Optional[datetime] = None
    
    messages: List[Dict] = Field(default_factory=list)


class ArenaRoom(BaseModel):
    """竞技场房间"""
    
    room_id: str
    title: str
    topic: str = ""
    category: str = "general"
    
    stage: ArenaStage = ArenaStage.WAITING
    current_round: int = 0
    
    participants: List[ArenaParticipant] = Field(default_factory=list)
    
    viewer_count: int = 0
    viewer_sids: List[str] = Field(default_factory=list)
    
    countdown_remaining: int = 60
    total_countdown: int = 60
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    
    winner: Optional[str] = None
    winner_display_name: Optional[str] = None
    
    final_scores: Dict[str, Dict] = Field(default_factory=dict)
    
    available_skills: List[ArenaSkillCard] = Field(default_factory=list)
    used_skills: List[Dict] = Field(default_factory=list)
    
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "room_id": self.room_id,
            "title": self.title,
            "topic": self.topic,
            "category": self.category,
            "stage": self.stage.value if isinstance(self.stage, Enum) else self.stage,
            "current_round": self.current_round,
            "participants": [p.model_dump() for p in self.participants],
            "viewer_count": self.viewer_count,
            "countdown_remaining": self.countdown_remaining,
            "total_countdown": self.total_countdown,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "winner": self.winner,
            "winner_display_name": self.winner_display_name,
            "final_scores": self.final_scores,
            "is_active": self.is_active,
        }


class CreateRoomRequest(BaseModel):
    """创建房间请求"""
    
    title: str
    topic: str = ""
    model1_id: str
    model2_id: str
    countdown_duration: int = 60


class UseSkillRequest(BaseModel):
    """使用技能请求"""
    
    skill_id: str
    target_model_id: str


class CastVoteRequest(BaseModel):
    """投票请求"""
    
    model_id: str


class AddEnergyRequest(BaseModel):
    """充能量请求"""
    
    model_id: str
    amount: int = 10


class ArenaJudgementResult(BaseModel):
    """AI裁判判决结果"""
    
    winner_model_id: str
    winner_display_name: str
    
    total_score: float
    energy_score: float
    vote_score: float
    dna_score: float
    
    details: Dict[str, Any] = Field(default_factory=dict)

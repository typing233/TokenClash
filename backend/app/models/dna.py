from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class DNAFingerprint(BaseModel):
    """Token DNA指纹数据模型"""
    
    model_id: str
    model_name: str
    display_name: str
    
    semantic_vector: List[float] = Field(default_factory=list)
    word_frequency: Dict[str, int] = Field(default_factory=dict)
    context_entropy: float = 0.0
    
    semantic_diversity: float = 0.0
    vocabulary_richness: float = 0.0
    response_consistency: float = 0.0
    
    debate_participations: int = 0
    wins: int = 0
    losses: int = 0
    
    average_argument_length: float = 0.0
    unique_word_count: int = 0
    total_word_count: int = 0
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    raw_messages: List[Dict] = Field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "display_name": self.display_name,
            "semantic_vector": self.semantic_vector,
            "word_frequency": self.word_frequency,
            "context_entropy": self.context_entropy,
            "semantic_diversity": self.semantic_diversity,
            "vocabulary_richness": self.vocabulary_richness,
            "response_consistency": self.response_consistency,
            "debate_participations": self.debate_participations,
            "wins": self.wins,
            "losses": self.losses,
            "average_argument_length": self.average_argument_length,
            "unique_word_count": self.unique_word_count,
            "total_word_count": self.total_word_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class NebulaPattern(BaseModel):
    """动态星云图案数据模型"""
    
    model_id: str
    
    base_color: str
    accent_color: str
    particle_count: int
    rotation_speed: float
    turbulence: float
    
    seed: int
    version: int = 1
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "base_color": self.base_color,
            "accent_color": self.accent_color,
            "particle_count": self.particle_count,
            "rotation_speed": self.rotation_speed,
            "turbulence": self.turbulence,
            "seed": self.seed,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class DNAFingerprintUpdate(BaseModel):
    """DNA指纹更新请求模型"""
    
    model_id: str
    messages: List[Dict[str, Any]]


class DNAComparisonResult(BaseModel):
    """DNA比较结果模型"""
    
    model1_id: str
    model2_id: str
    semantic_similarity: float
    vocabulary_overlap: float
    style_similarity: float
    overall_similarity: float

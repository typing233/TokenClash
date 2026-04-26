from pydantic_settings import BaseSettings
from typing import Optional, Dict
from functools import lru_cache


class Settings(BaseSettings):
    # MongoDB配置
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "tokenclash"
    
    # 火山方舟API配置
    volcano_api_key: str
    volcano_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    
    # 模型配置 - 支持多个模型
    model_configs: Dict[str, Dict] = {}
    
    # JWT配置
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    
    # 辩论配置
    max_debate_rounds: int = 5
    max_message_length: int = 2000
    
    class Config:
        env_file = ".env"
        extra = "ignore"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_model_configs()
    
    def _load_model_configs(self):
        """从环境变量加载模型配置"""
        import os
        
        model_configs = {}
        # 最多支持4个模型配置
        for i in range(1, 5):
            name_key = f"MODEL_{i}_NAME"
            display_key = f"MODEL_{i}_DISPLAY_NAME"
            
            model_name = os.getenv(name_key)
            display_name = os.getenv(display_key)
            
            if model_name and model_name.strip():
                model_configs[f"model_{i}"] = {
                    "model_name": model_name.strip(),
                    "display_name": display_name.strip() if display_name else model_name.strip(),
                    "id": f"model_{i}"
                }
        
        # 如果没有配置任何模型，使用默认值
        if not model_configs:
            model_configs = {
                "model_1": {
                    "model_name": "doubao-seed-1.8b-chat",
                    "display_name": "豆包小模型",
                    "id": "model_1"
                },
                "model_2": {
                    "model_name": "doubao-seed-12b-chat",
                    "display_name": "豆包12B模型",
                    "id": "model_2"
                }
            }
        
        self.model_configs = model_configs


@lru_cache()
def get_settings() -> Settings:
    return Settings()

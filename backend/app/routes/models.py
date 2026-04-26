from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.config import get_settings


router = APIRouter()


@router.get("/")
async def get_all_models():
    """获取所有已配置的模型列表"""
    settings = get_settings()
    
    models = []
    for model_id, config in settings.model_configs.items():
        models.append({
            "model_id": model_id,
            "model_name": config["model_name"],
            "display_name": config["display_name"],
            "is_available": True  # 暂时都标记为可用
        })
    
    return {"models": models, "count": len(models)}


@router.get("/{model_id}")
async def get_model_detail(model_id: str):
    """获取单个模型的详细配置"""
    settings = get_settings()
    
    if model_id not in settings.model_configs:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
    
    config = settings.model_configs[model_id]
    
    return {
        "model_id": model_id,
        "model_name": config["model_name"],
        "display_name": config["display_name"],
        "is_available": True
    }


@router.get("/pairs/available")
async def get_available_model_pairs():
    """获取可用的模型对战组合"""
    settings = get_settings()
    
    model_ids = list(settings.model_configs.keys())
    
    if len(model_ids) < 2:
        return {"pairs": [], "message": "Need at least 2 models to form pairs"}
    
    pairs = []
    for i in range(len(model_ids)):
        for j in range(i + 1, len(model_ids)):
            model1 = settings.model_configs[model_ids[i]]
            model2 = settings.model_configs[model_ids[j]]
            
            # 两种对战组合（正反方互换）
            pairs.append({
                "pair_id": f"{model_ids[i]}_vs_{model_ids[j]}",
                "affirmative": {
                    "model_id": model_ids[i],
                    "model_name": model1["model_name"],
                    "display_name": model1["display_name"]
                },
                "negative": {
                    "model_id": model_ids[j],
                    "model_name": model2["model_name"],
                    "display_name": model2["display_name"]
                }
            })
            
            pairs.append({
                "pair_id": f"{model_ids[j]}_vs_{model_ids[i]}",
                "affirmative": {
                    "model_id": model_ids[j],
                    "model_name": model2["model_name"],
                    "display_name": model2["display_name"]
                },
                "negative": {
                    "model_id": model_ids[i],
                    "model_name": model1["model_name"],
                    "display_name": model1["display_name"]
                }
            })
    
    return {"pairs": pairs, "count": len(pairs)}


@router.get("/status/health")
async def check_model_health():
    """检查模型API的健康状态"""
    from app.services.volcano_api import get_volcano_client
    
    settings = get_settings()
    volcano_client = get_volcano_client()
    
    health_status = {
        "overall_status": "unknown",
        "models": []
    }
    
    # 简单检查：验证API密钥是否配置
    api_key_configured = bool(settings.volcano_api_key and settings.volcano_api_key != "your_api_key_here")
    
    for model_id, config in settings.model_configs.items():
        model_status = {
            "model_id": model_id,
            "model_name": config["model_name"],
            "display_name": config["display_name"],
            "api_key_configured": api_key_configured,
            "status": "ready" if api_key_configured else "not_configured"
        }
        health_status["models"].append(model_status)
    
    # 总体状态
    if all(m["status"] == "ready" for m in health_status["models"]):
        health_status["overall_status"] = "ready"
    elif any(m["status"] == "ready" for m in health_status["models"]):
        health_status["overall_status"] = "partial"
    else:
        health_status["overall_status"] = "not_configured"
    
    return health_status


@router.get("/config/info")
async def get_config_info():
    """获取模型配置信息（安全处理，不暴露密钥）"""
    settings = get_settings()
    
    return {
        "base_url": settings.volcano_base_url,
        "api_key_configured": bool(settings.volcano_api_key and settings.volcano_api_key != "your_api_key_here"),
        "configured_models_count": len(settings.model_configs),
        "max_debate_rounds": settings.max_debate_rounds,
        "max_message_length": settings.max_message_length
    }

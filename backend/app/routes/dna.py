from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from typing import List, Optional
from app.services.dna_service import get_dna_service, get_nebula_service
from app.models.dna import DNAFingerprintUpdate

router = APIRouter()
dna_service = get_dna_service()
nebula_service = get_nebula_service()


@router.get("/fingerprints")
async def get_all_fingerprints():
    """获取所有Token的DNA指纹"""
    fingerprints = await dna_service.get_all_fingerprints()
    return {
        "fingerprints": [fp.to_dict() for fp in fingerprints],
        "count": len(fingerprints)
    }


@router.get("/fingerprints/{model_id}")
async def get_fingerprint(model_id: str):
    """获取指定Token的DNA指纹"""
    fingerprint = await dna_service.get_fingerprint(model_id)
    if not fingerprint:
        raise HTTPException(status_code=404, detail=f"DNA fingerprint not found for model: {model_id}")
    return fingerprint.to_dict()


@router.post("/fingerprints/update")
async def update_fingerprint(data: DNAFingerprintUpdate):
    """更新或创建Token的DNA指纹"""
    fingerprint = await dna_service.update_fingerprint(
        model_id=data.model_id,
        model_name=data.model_id,
        display_name=data.model_id,
        messages=data.messages
    )
    return {
        "success": True,
        "fingerprint": fingerprint.to_dict()
    }


@router.get("/compare/{model1_id}/{model2_id}")
async def compare_fingerprints(model1_id: str, model2_id: str):
    """比较两个Token的DNA指纹相似度"""
    result = await dna_service.compare_fingerprints(model1_id, model2_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"One or both fingerprints not found: {model1_id}, {model2_id}"
        )
    return result


@router.get("/nebula/{model_id}")
async def get_nebula_pattern(model_id: str):
    """获取Token的星云图案配置"""
    pattern = await nebula_service.get_pattern(model_id)
    if not pattern:
        pattern = await nebula_service.generate_pattern(model_id)
    return pattern.to_dict()


@router.post("/nebula/{model_id}/generate")
async def generate_nebula_pattern(model_id: str):
    """生成或更新Token的星云图案"""
    fingerprint = await dna_service.get_fingerprint(model_id)
    pattern = await nebula_service.generate_pattern(model_id, fingerprint)
    return {
        "success": True,
        "pattern": pattern.to_dict()
    }


@router.get("/nebula/{model_id}/export/svg")
async def export_nebula_svg(
    model_id: str,
    width: int = Query(800, ge=200, le=2000),
    height: int = Query(600, ge=200, le=2000)
):
    """导出星云图案为SVG格式"""
    svg_content = await nebula_service.export_pattern_svg(model_id, width, height)
    if not svg_content:
        raise HTTPException(status_code=404, detail=f"Nebula pattern not found for model: {model_id}")
    
    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": f"attachment; filename=nebula_{model_id}.svg"
        }
    )


@router.get("/nebula")
async def get_all_nebula_patterns():
    """获取所有星云图案配置"""
    patterns = await nebula_service.get_all_patterns()
    return {
        "patterns": [p.to_dict() for p in patterns],
        "count": len(patterns)
    }


@router.get("/fingerprints/{model_id}/analytics")
async def get_fingerprint_analytics(model_id: str):
    """获取Token DNA指纹的详细分析数据"""
    fingerprint = await dna_service.get_fingerprint(model_id)
    if not fingerprint:
        raise HTTPException(status_code=404, detail=f"DNA fingerprint not found for model: {model_id}")
    
    win_rate = 0.0
    if fingerprint.debate_participations > 0:
        win_rate = fingerprint.wins / fingerprint.debate_participations
    
    top_words = []
    if fingerprint.word_frequency:
        sorted_words = sorted(fingerprint.word_frequency.items(), key=lambda x: x[1], reverse=True)
        top_words = [{"word": w, "count": c} for w, c in sorted_words[:20]]
    
    return {
        "model_id": fingerprint.model_id,
        "display_name": fingerprint.display_name,
        "debate_stats": {
            "total_participations": fingerprint.debate_participations,
            "wins": fingerprint.wins,
            "losses": fingerprint.losses,
            "win_rate": round(win_rate, 4)
        },
        "language_metrics": {
            "context_entropy": round(fingerprint.context_entropy, 4),
            "semantic_diversity": round(fingerprint.semantic_diversity, 4),
            "vocabulary_richness": round(fingerprint.vocabulary_richness, 4),
            "response_consistency": round(fingerprint.response_consistency, 4)
        },
        "word_stats": {
            "total_word_count": fingerprint.total_word_count,
            "unique_word_count": fingerprint.unique_word_count,
            "average_argument_length": round(fingerprint.average_argument_length, 2),
            "top_words": top_words
        },
        "profile_summary": {
            "style": _determine_style(fingerprint),
            "dominant_traits": _identify_traits(fingerprint)
        }
    }


def _determine_style(fp) -> str:
    """根据指纹数据确定语言风格"""
    if fp.vocabulary_richness > 0.6 and fp.context_entropy > 4.0:
        return "diverse_and_creative"
    elif fp.response_consistency > 0.7:
        return "consistent_and_focused"
    elif fp.semantic_diversity > 0.5:
        return "varied_expression"
    else:
        return "balanced"


def _identify_traits(fp) -> List[str]:
    """识别主要特征"""
    traits = []
    
    if fp.context_entropy > 4.5:
        traits.append("high_lexical_diversity")
    if fp.vocabulary_richness > 0.5:
        traits.append("rich_vocabulary")
    if fp.response_consistency > 0.65:
        traits.append("consistent_style")
    if fp.average_argument_length > 300:
        traits.append("detailed_arguments")
    if fp.semantic_diversity > 0.4:
        traits.append("varied_sentence_structure")
    if fp.wins > fp.losses and fp.debate_participations > 5:
        traits.append("high_win_rate")
    
    if not traits:
        traits.append("balanced_profile")
    
    return traits

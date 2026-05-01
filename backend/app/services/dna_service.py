import re
import math
import hashlib
import numpy as np
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from app.database import get_database
from app.models.dna import DNAFingerprint, NebulaPattern
from app.config import get_settings

import jieba
from scipy.stats import entropy as scipy_entropy

settings = get_settings()


class DNAFingerprintService:
    """Token DNA指纹计算服务"""
    
    def __init__(self):
        self.db = None
        self._stopwords = set()
        self._load_stopwords()
    
    def _load_stopwords(self):
        """加载常用停用词"""
        self._stopwords = {
            '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
            '自己', '这', '那', '他', '她', '它', '们', '这个', '那个', '什么', '怎么', '为什么',
            '吗', '呢', '吧', '啊', '呀', '哦', '嗯', '哈', '啦', '呗', '罢了', '而已',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'shall', 'need', 'dare',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
            'through', 'during', 'before', 'after', 'above', 'below', 'between',
            'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'so',
            'that', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
            'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his',
        }
    
    def get_db(self):
        """获取数据库实例"""
        if self.db is None:
            self.db = get_database()
        return self.db
    
    def _tokenize(self, text: str) -> List[str]:
        """分词处理（支持中英文）"""
        if not text:
            return []
        
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        has_chinese = bool(chinese_pattern.search(text))
        
        if has_chinese:
            words = list(jieba.cut(text))
        else:
            words = text.lower().split()
        
        words = [w for w in words if w.strip() and w.strip() not in self._stopwords]
        words = [re.sub(r'[^\w\s]', '', w) for w in words]
        words = [w for w in words if w]
        
        return words
    
    def calculate_word_frequency(self, texts: List[str]) -> Dict[str, int]:
        """计算词频"""
        all_words = []
        for text in texts:
            words = self._tokenize(text)
            all_words.extend(words)
        
        return dict(Counter(all_words).most_common(100))
    
    def calculate_context_entropy(self, texts: List[str]) -> float:
        """计算上下文熵 - 衡量语言多样性"""
        if not texts:
            return 0.0
        
        all_words = []
        for text in texts:
            words = self._tokenize(text)
            all_words.extend(words)
        
        if not all_words:
            return 0.0
        
        word_counts = Counter(all_words)
        total = sum(word_counts.values())
        
        if total == 0:
            return 0.0
        
        probabilities = [count / total for count in word_counts.values()]
        
        return float(scipy_entropy(probabilities, base=2))
    
    def calculate_semantic_diversity(self, texts: List[str]) -> float:
        """计算语义多样性 - 基于句子长度和结构变化"""
        if not texts:
            return 0.0
        
        lengths = [len(text) for text in texts if text]
        
        if len(lengths) < 2:
            return 0.0
        
        mean_length = np.mean(lengths)
        std_length = np.std(lengths)
        
        if mean_length == 0:
            return 0.0
        
        cv = std_length / mean_length
        
        sentence_structures = []
        for text in texts:
            num_sentences = len(re.split(r'[。！？.!?]+', text.strip()))
            avg_sentence_length = len(text) / max(num_sentences, 1)
            sentence_structures.append(avg_sentence_length)
        
        if len(sentence_structures) > 1:
            structure_std = np.std(sentence_structures)
            cv = (cv + structure_std / max(np.mean(sentence_structures), 1)) / 2
        
        return float(min(cv * 2, 1.0))
    
    def calculate_vocabulary_richness(self, texts: List[str]) -> float:
        """计算词汇丰富度 - Type-Token Ratio"""
        all_words = []
        for text in texts:
            words = self._tokenize(text)
            all_words.extend(words)
        
        if not all_words:
            return 0.0
        
        unique_words = set(all_words)
        total_words = len(all_words)
        
        ttr = len(unique_words) / total_words
        
        if total_words > 50:
            log_ttr = len(unique_words) / math.log(total_words)
            ttr = min(log_ttr / 2, 1.0)
        
        return float(ttr)
    
    def calculate_response_consistency(self, texts: List[str]) -> float:
        """计算响应一致性 - 衡量回复风格的一致性"""
        if len(texts) < 2:
            return 0.5
        
        features = []
        for text in texts:
            words = self._tokenize(text)
            avg_word_len = np.mean([len(w) for w in words]) if words else 0
            num_sentences = len(re.split(r'[。！？.!?]+', text.strip()))
            sentence_complexity = len(text) / max(num_sentences, 1)
            
            features.append([
                len(text),
                avg_word_len,
                sentence_complexity,
                num_sentences
            ])
        
        features = np.array(features)
        
        if len(features) < 2:
            return 0.5
        
        stds = np.std(features, axis=0)
        means = np.mean(features, axis=0)
        
        cvs = stds / (means + 1e-8)
        avg_cv = np.mean(cvs)
        
        consistency = 1.0 - min(avg_cv * 0.5, 0.8)
        
        return float(consistency)
    
    def generate_semantic_vector(self, texts: List[str], dimension: int = 64) -> List[float]:
        """生成语义向量（简化版，基于词频和统计特征）"""
        all_words = []
        for text in texts:
            words = self._tokenize(text)
            all_words.extend(words)
        
        word_counts = Counter(all_words)
        top_words = [w for w, _ in word_counts.most_common(dimension)]
        
        vector = []
        for i in range(dimension):
            if i < len(top_words):
                word = top_words[i]
                freq = word_counts[word] / max(len(all_words), 1)
                vector.append(freq)
            else:
                vector.append(0.0)
        
        total_length = sum(len(t) for t in texts) / max(len(texts), 1)
        avg_length = total_length / 1000.0
        
        if len(texts) > 0:
            for i in range(min(4, dimension)):
                if i < len(vector):
                    vector[i] = (vector[i] + avg_length * 0.1) / 2
        
        norm = math.sqrt(sum(x * x for x in vector)) + 1e-8
        vector = [x / norm for x in vector]
        
        return vector
    
    async def update_fingerprint(
        self,
        model_id: str,
        model_name: str,
        display_name: str,
        messages: List[Dict[str, Any]],
        is_winner: Optional[bool] = None
    ) -> DNAFingerprint:
        """更新或创建Token的DNA指纹"""
        db = self.get_db()
        
        existing = await db.dna_fingerprints.find_one({"model_id": model_id})
        
        text_contents = [m.get("content", "") for m in messages if m.get("content")]
        
        if existing:
            fingerprint = DNAFingerprint(**existing)
            
            stored_messages = fingerprint.raw_messages or []
            stored_messages.extend(messages)
            if len(stored_messages) > 500:
                stored_messages = stored_messages[-500:]
            fingerprint.raw_messages = stored_messages
            
            all_texts = text_contents + [m.get("content", "") for m in existing.get("raw_messages", [])[-100:]]
        else:
            fingerprint = DNAFingerprint(
                model_id=model_id,
                model_name=model_name,
                display_name=display_name,
                raw_messages=messages
            )
            all_texts = text_contents
        
        fingerprint.word_frequency = self.calculate_word_frequency(all_texts)
        fingerprint.context_entropy = self.calculate_context_entropy(all_texts)
        fingerprint.semantic_diversity = self.calculate_semantic_diversity(all_texts)
        fingerprint.vocabulary_richness = self.calculate_vocabulary_richness(all_texts)
        fingerprint.response_consistency = self.calculate_response_consistency(all_texts)
        fingerprint.semantic_vector = self.generate_semantic_vector(all_texts)
        
        fingerprint.debate_participations += 1
        
        if is_winner is True:
            fingerprint.wins += 1
        elif is_winner is False:
            fingerprint.losses += 1
        
        total_lengths = [len(t) for t in all_texts if t]
        if total_lengths:
            fingerprint.average_argument_length = float(np.mean(total_lengths))
        
        all_words = []
        for text in all_texts:
            all_words.extend(self._tokenize(text))
        fingerprint.unique_word_count = len(set(all_words))
        fingerprint.total_word_count = len(all_words)
        
        fingerprint.updated_at = datetime.utcnow()
        
        fingerprint_dict = fingerprint.to_dict()
        fingerprint_dict["raw_messages"] = fingerprint.raw_messages
        
        await db.dna_fingerprints.update_one(
            {"model_id": model_id},
            {"$set": fingerprint_dict},
            upsert=True
        )
        
        return fingerprint
    
    async def get_fingerprint(self, model_id: str) -> Optional[DNAFingerprint]:
        """获取Token的DNA指纹"""
        db = self.get_db()
        doc = await db.dna_fingerprints.find_one({"model_id": model_id})
        if doc:
            return DNAFingerprint(**doc)
        return None
    
    async def compare_fingerprints(
        self,
        model1_id: str,
        model2_id: str
    ) -> Optional[Dict[str, Any]]:
        """比较两个Token的DNA指纹"""
        fp1 = await self.get_fingerprint(model1_id)
        fp2 = await self.get_fingerprint(model2_id)
        
        if not fp1 or not fp2:
            return None
        
        vec1 = np.array(fp1.semantic_vector)
        vec2 = np.array(fp2.semantic_vector)
        
        if len(vec1) > 0 and len(vec2) > 0:
            semantic_sim = float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-8))
        else:
            semantic_sim = 0.5
        
        words1 = set(fp1.word_frequency.keys())
        words2 = set(fp2.word_frequency.keys())
        
        if words1 or words2:
            vocab_overlap = len(words1 & words2) / len(words1 | words2)
        else:
            vocab_overlap = 0.0
        
        style_features1 = [fp1.context_entropy, fp1.semantic_diversity, fp1.vocabulary_richness, fp1.response_consistency]
        style_features2 = [fp2.context_entropy, fp2.semantic_diversity, fp2.vocabulary_richness, fp2.response_consistency]
        
        f1 = np.array(style_features1)
        f2 = np.array(style_features2)
        
        if np.sum(np.abs(f1)) > 0 and np.sum(np.abs(f2)) > 0:
            style_sim = float(1.0 - np.mean(np.abs(f1 - f2)))
        else:
            style_sim = 0.5
        
        overall_sim = (semantic_sim * 0.4 + vocab_overlap * 0.3 + style_sim * 0.3)
        
        return {
            "model1_id": model1_id,
            "model2_id": model2_id,
            "semantic_similarity": max(0.0, min(1.0, semantic_sim)),
            "vocabulary_overlap": float(vocab_overlap),
            "style_similarity": max(0.0, min(1.0, style_sim)),
            "overall_similarity": max(0.0, min(1.0, overall_sim))
        }
    
    async def get_all_fingerprints(self) -> List[DNAFingerprint]:
        """获取所有Token的DNA指纹"""
        db = self.get_db()
        cursor = db.dna_fingerprints.find()
        docs = await cursor.to_list(length=None)
        return [DNAFingerprint(**doc) for doc in docs]


class NebulaPatternService:
    """动态星云图案生成服务"""
    
    COLOR_PALETTES = [
        {"base": "#1a1a2e", "accent": "#0f3460", "highlight": "#e94560"},
        {"base": "#0c0c1e", "accent": "#16213e", "highlight": "#e94560"},
        {"base": "#1b262c", "accent": "#0f4c75", "highlight": "#3282b8"},
        {"base": "#2d132c", "accent": "#801336", "highlight": "#c72c41"},
        {"base": "#1a1a1a", "accent": "#2d2d2d", "highlight": "#00d9ff"},
        {"base": "#0a192f", "accent": "#112240", "highlight": "#64ffda"},
        {"base": "#16213e", "accent": "#1a1a2e", "highlight": "#f39c12"},
        {"base": "#1e1e2f", "accent": "#2e2e4f", "highlight": "#ff6b6b"},
    ]
    
    def __init__(self):
        self.db = None
        self.dna_service = DNAFingerprintService()
    
    def get_db(self):
        """获取数据库实例"""
        if self.db is None:
            self.db = get_database()
        return self.db
    
    def _generate_seed_from_model_id(self, model_id: str) -> int:
        """从model_id生成种子"""
        hash_obj = hashlib.md5(model_id.encode())
        return int(hash_obj.hexdigest()[:8], 16)
    
    async def generate_pattern(
        self,
        model_id: str,
        fingerprint: Optional[DNAFingerprint] = None
    ) -> NebulaPattern:
        """基于DNA指纹生成星云图案"""
        if fingerprint is None:
            fingerprint = await self.dna_service.get_fingerprint(model_id)
        
        seed = self._generate_seed_from_model_id(model_id)
        np.random.seed(seed)
        
        if fingerprint:
            palette_index = int((fingerprint.context_entropy * 10 + fingerprint.semantic_diversity * 10) % len(self.COLOR_PALETTES))
        else:
            palette_index = hash(model_id) % len(self.COLOR_PALETTES)
        
        palette = self.COLOR_PALETTES[palette_index]
        
        if fingerprint:
            particle_count = int(200 + fingerprint.unique_word_count * 0.5)
            particle_count = min(max(particle_count, 100), 500)
        else:
            particle_count = 200
        
        if fingerprint:
            rotation_speed = (fingerprint.semantic_diversity * 0.02 + fingerprint.vocabulary_richness * 0.01)
            rotation_speed = max(0.001, min(rotation_speed, 0.05))
        else:
            rotation_speed = 0.01
        
        if fingerprint:
            turbulence = (fingerprint.context_entropy * 0.1 + fingerprint.response_consistency * 0.05)
            turbulence = max(0.1, min(turbulence, 0.8))
        else:
            turbulence = 0.3
        
        existing = await self.get_pattern(model_id)
        if existing:
            version = existing.version + 1
        else:
            version = 1
        
        pattern = NebulaPattern(
            model_id=model_id,
            base_color=palette["base"],
            accent_color=palette["accent"],
            particle_count=particle_count,
            rotation_speed=rotation_speed,
            turbulence=turbulence,
            seed=seed,
            version=version
        )
        
        await self.save_pattern(pattern)
        
        return pattern
    
    async def get_pattern(self, model_id: str) -> Optional[NebulaPattern]:
        """获取已保存的星云图案配置"""
        db = self.get_db()
        doc = await db.nebula_patterns.find_one({"model_id": model_id})
        if doc:
            return NebulaPattern(**doc)
        return None
    
    async def save_pattern(self, pattern: NebulaPattern):
        """保存星云图案配置"""
        db = self.get_db()
        pattern.updated_at = datetime.utcnow()
        await db.nebula_patterns.update_one(
            {"model_id": pattern.model_id},
            {"$set": pattern.to_dict()},
            upsert=True
        )
    
    async def export_pattern_svg(
        self,
        model_id: str,
        width: int = 800,
        height: int = 600
    ) -> Optional[str]:
        """导出星云图案为SVG格式"""
        pattern = await self.get_pattern(model_id)
        if not pattern:
            pattern = await self.generate_pattern(model_id)
        
        np.random.seed(pattern.seed)
        
        particles = []
        for i in range(pattern.particle_count):
            angle = np.random.uniform(0, 2 * np.pi)
            radius = np.random.exponential(scale=width * 0.2)
            radius = min(radius, width * 0.45)
            
            x = width / 2 + radius * np.cos(angle)
            y = height / 2 + radius * np.sin(angle)
            size = np.random.uniform(1, 4)
            opacity = np.random.uniform(0.1, 0.6)
            
            particles.append({"x": x, "y": y, "size": size, "opacity": opacity})
        
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
            f'  <defs>',
            f'    <radialGradient id="bgGradient" cx="50%" cy="50%" r="60%">',
            f'      <stop offset="0%" style="stop-color:{pattern.accent_color};stop-opacity:1" />',
            f'      <stop offset="100%" style="stop-color:{pattern.base_color};stop-opacity:1" />',
            f'    </radialGradient>',
            f'    <filter id="glow">',
            f'      <feGaussianBlur stdDeviation="3" result="coloredBlur"/>',
            f'      <feMerge>',
            f'        <feMergeNode in="coloredBlur"/>',
            f'        <feMergeNode in="SourceGraphic"/>',
            f'      </feMerge>',
            f'    </filter>',
            f'  </defs>',
            f'  <rect width="100%" height="100%" fill="url(#bgGradient)" />',
        ]
        
        for p in particles:
            svg_parts.append(
                f'  <circle cx="{p["x"]:.2f}" cy="{p["y"]:.2f}" r="{p["size"]:.2f}" '
                f'fill="white" opacity="{p["opacity"]:.2f}" filter="url(#glow)" />'
            )
        
        svg_parts.append('</svg>')
        
        return '\n'.join(svg_parts)
    
    async def get_all_patterns(self) -> List[NebulaPattern]:
        """获取所有星云图案配置"""
        db = self.get_db()
        cursor = db.nebula_patterns.find()
        docs = await cursor.to_list(length=None)
        return [NebulaPattern(**doc) for doc in docs]


dna_service = DNAFingerprintService()
nebula_service = NebulaPatternService()


def get_dna_service() -> DNAFingerprintService:
    """获取DNA指纹服务实例"""
    return dna_service


def get_nebula_service() -> NebulaPatternService:
    """获取星云图案服务实例"""
    return nebula_service

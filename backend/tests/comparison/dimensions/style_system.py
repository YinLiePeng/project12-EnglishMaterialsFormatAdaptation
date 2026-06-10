"""样式系统对比维度"""

from typing import List, Tuple, Dict, Any, Set
from pathlib import Path
from difflib import SequenceMatcher

from .base import ComparisonDimension
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.docx.parser import ElementType, ParagraphInfo


class StyleSystemDimension(ComparisonDimension):
    """对比样式系统：格式属性分布、字体使用统计"""

    name = "style_system"
    weight = 0.05
    description = "对比样式系统一致性（格式属性分布、字体使用）"

    def compare(
        self,
        gen_elements: List,
        ref_elements: List,
        gen_path: Path,
        ref_path: Path,
        match_result=None,
    ) -> Tuple[float, Dict[str, Any]]:
        try:
            # 提取段落
            gen_paras = [e.paragraph for e in gen_elements
                        if e.element_type == ElementType.PARAGRAPH and e.paragraph]
            ref_paras = [e.paragraph for e in ref_elements
                        if e.element_type == ElementType.PARAGRAPH and e.paragraph]

            if not gen_paras and not ref_paras:
                return 1.0, {"reason": "both_empty"}

            # 1. 字体使用分布比较
            font_dist_sim = self._compare_font_distribution(gen_paras, ref_paras)

            # 2. 字号分布比较
            size_dist_sim = self._compare_size_distribution(gen_paras, ref_paras)

            # 3. 对齐方式分布比较
            align_dist_sim = self._compare_alignment_distribution(gen_paras, ref_paras)

            # 4. 加粗比例比较
            bold_ratio_sim = self._compare_bold_ratio(gen_paras, ref_paras)

            # 5. 格式属性多样性比较
            diversity_sim = self._compare_format_diversity(gen_paras, ref_paras)

            score = (
                font_dist_sim * 0.25
                + size_dist_sim * 0.25
                + align_dist_sim * 0.20
                + bold_ratio_sim * 0.15
                + diversity_sim * 0.15
            )

            details = {
                "font_distribution_similarity": round(font_dist_sim, 4),
                "size_distribution_similarity": round(size_dist_sim, 4),
                "alignment_distribution_similarity": round(align_dist_sim, 4),
                "bold_ratio_similarity": round(bold_ratio_sim, 4),
                "format_diversity_similarity": round(diversity_sim, 4),
                "gen_para_count": len(gen_paras),
                "ref_para_count": len(ref_paras),
            }
            return round(min(score, 1.0), 4), details

        except Exception as e:
            return 0.0, {"error": str(e)}

    def _compare_font_distribution(
        self, gen_paras: List[ParagraphInfo], ref_paras: List[ParagraphInfo]
    ) -> float:
        """比较字体使用分布"""
        from font_utils import fuzzy_font_match, normalize_font_name

        gen_fonts = self._count_fonts(gen_paras)
        ref_fonts = self._count_fonts(ref_paras)

        if not gen_fonts and not ref_fonts:
            return 1.0
        if not gen_fonts or not ref_fonts:
            return 0.0

        # 比较主要字体（前5个）
        gen_top = sorted(gen_fonts.items(), key=lambda x: -x[1])[:5]
        ref_top = sorted(ref_fonts.items(), key=lambda x: -x[1])[:5]

        scores = []
        for gen_font, gen_count in gen_top:
            best_sim = 0.0
            for ref_font, ref_count in ref_top:
                sim = fuzzy_font_match(gen_font, ref_font)
                # 加权：字体相似度 * 使用频率相似度
                freq_sim = min(gen_count, ref_count) / max(gen_count, ref_count)
                combined = sim * 0.7 + freq_sim * 0.3
                best_sim = max(best_sim, combined)
            scores.append(best_sim)

        return self._mean(scores) if scores else 0.0

    def _compare_size_distribution(
        self, gen_paras: List[ParagraphInfo], ref_paras: List[ParagraphInfo]
    ) -> float:
        """比较字号分布"""
        gen_sizes = self._count_sizes(gen_paras)
        ref_sizes = self._count_sizes(ref_paras)

        if not gen_sizes and not ref_sizes:
            return 1.0
        if not gen_sizes or not ref_sizes:
            return 0.0

        # 比较主要字号（前5个）
        gen_top = sorted(gen_sizes.items(), key=lambda x: -x[1])[:5]
        ref_top = sorted(ref_sizes.items(), key=lambda x: -x[1])[:5]

        scores = []
        for gen_size, gen_count in gen_top:
            best_sim = 0.0
            for ref_size, ref_count in ref_top:
                size_sim = 1.0 - min(abs(gen_size - ref_size) / max(gen_size, ref_size, 0.01), 1.0)
                freq_sim = min(gen_count, ref_count) / max(gen_count, ref_count)
                combined = size_sim * 0.7 + freq_sim * 0.3
                best_sim = max(best_sim, combined)
            scores.append(best_sim)

        return self._mean(scores) if scores else 0.0

    def _compare_alignment_distribution(
        self, gen_paras: List[ParagraphInfo], ref_paras: List[ParagraphInfo]
    ) -> float:
        """比较对齐方式分布"""
        gen_aligns = self._count_alignments(gen_paras)
        ref_aligns = self._count_alignments(ref_paras)

        if not gen_aligns and not ref_aligns:
            return 1.0

        all_aligns = set(list(gen_aligns.keys()) + list(ref_aligns.keys()))
        if not all_aligns:
            return 1.0

        scores = []
        for align in all_aligns:
            gen_ratio = gen_aligns.get(align, 0) / max(len(gen_paras), 1)
            ref_ratio = ref_aligns.get(align, 0) / max(len(ref_paras), 1)
            scores.append(1.0 - abs(gen_ratio - ref_ratio))

        return self._mean(scores)

    def _compare_bold_ratio(
        self, gen_paras: List[ParagraphInfo], ref_paras: List[ParagraphInfo]
    ) -> float:
        """比较加粗段落比例"""
        gen_bold = sum(1 for p in gen_paras if p.font and p.font.bold)
        ref_bold = sum(1 for p in ref_paras if p.font and p.font.bold)

        gen_ratio = gen_bold / max(len(gen_paras), 1)
        ref_ratio = ref_bold / max(len(ref_paras), 1)

        return 1.0 - abs(gen_ratio - ref_ratio)

    def _compare_format_diversity(
        self, gen_paras: List[ParagraphInfo], ref_paras: List[ParagraphInfo]
    ) -> float:
        """比较格式多样性（不同格式签名的数量比例）"""
        gen_sigs = set(self._format_signature(p) for p in gen_paras)
        ref_sigs = set(self._format_signature(p) for p in ref_paras)

        if not gen_sigs and not ref_sigs:
            return 1.0

        # 使用Jaccard相似度
        intersection = len(gen_sigs & ref_sigs)
        union = len(gen_sigs | ref_sigs)

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def _format_signature(para: ParagraphInfo) -> str:
        """生成格式签名"""
        align = "left"
        if para.format and para.format.alignment:
            align = para.format.alignment

        font_name = "default"
        if para.font and para.font.name:
            font_name = para.font.name

        font_size = 12.0
        if para.font and para.font.size:
            font_size = para.font.size

        bold = "B" if para.font and para.font.bold else "n"

        return f"{align}_{font_name}_{font_size:.0f}_{bold}"

    @staticmethod
    def _count_fonts(paras: List[ParagraphInfo]) -> Dict[str, int]:
        fonts = {}
        for p in paras:
            if p.font and p.font.name:
                name = p.font.name
                fonts[name] = fonts.get(name, 0) + 1
        return fonts

    @staticmethod
    def _count_sizes(paras: List[ParagraphInfo]) -> Dict[float, int]:
        sizes = {}
        for p in paras:
            if p.font and p.font.size:
                size = round(p.font.size, 1)
                sizes[size] = sizes.get(size, 0) + 1
        return sizes

    @staticmethod
    def _count_alignments(paras: List[ParagraphInfo]) -> Dict[str, int]:
        aligns = {}
        for p in paras:
            align = "left"
            if p.format and p.format.alignment:
                align = p.format.alignment
            aligns[align] = aligns.get(align, 0) + 1
        return aligns

    @staticmethod
    def _mean(values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0

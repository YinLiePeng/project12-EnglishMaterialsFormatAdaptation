"""文档结构对比维度"""

from difflib import SequenceMatcher
from typing import List, Tuple, Dict, Any
from pathlib import Path
from collections import Counter

from .base import ComparisonDimension
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.docx.parser import ContentElement, ElementType


class DocumentStructureDimension(ComparisonDimension):
    name = "document_structure"
    weight = 0.07
    description = "文档结构对比（元素类型分布、格式签名分布、标题层级）"

    def compare(
        self,
        gen_elements: List[ContentElement],
        ref_elements: List[ContentElement],
        gen_path: Path,
        ref_path: Path,
        match_result=None,
    ) -> Tuple[float, Dict[str, Any]]:
        try:
            if not gen_elements and not ref_elements:
                return 1.0, {"reason": "both_empty"}

            # 过滤掉空行进行比较（PDF不会生成空行）
            gen_content = [e for e in gen_elements if e.element_type != ElementType.BLANK_LINE]
            ref_content = [e for e in ref_elements if e.element_type != ElementType.BLANK_LINE]

            # 1. 元素类型分布相似度（按比例比较）
            type_dist_sim = self._compare_type_distribution(gen_content, ref_content)

            # 2. 格式签名分布相似度
            format_dist_sim = self._compare_format_distribution(gen_content, ref_content)

            # 3. 标题层级分布相似度
            heading_dist_sim = self._compare_heading_distribution(gen_content, ref_content)

            # 4. 元素数量匹配
            count_sim = self._count_match(len(gen_content), len(ref_content))

            score = (
                type_dist_sim * 0.20
                + format_dist_sim * 0.35
                + heading_dist_sim * 0.25
                + count_sim * 0.20
            )

            details = {
                "type_distribution_similarity": round(type_dist_sim, 4),
                "format_distribution_similarity": round(format_dist_sim, 4),
                "heading_distribution_similarity": round(heading_dist_sim, 4),
                "count_similarity": round(count_sim, 4),
                "gen_element_count": len(gen_elements),
                "ref_element_count": len(ref_elements),
                "gen_content_count": len(gen_content),
                "ref_content_count": len(ref_content),
            }
            return round(min(score, 1.0), 4), details

        except Exception as e:
            return 0.0, {"error": str(e)}

    def _compare_type_distribution(
        self,
        gen_elements: List[ContentElement],
        ref_elements: List[ContentElement],
    ) -> float:
        """比较元素类型分布（按比例，非序列）"""
        gen_types = Counter(e.element_type.value for e in gen_elements)
        ref_types = Counter(e.element_type.value for e in ref_elements)

        all_types = set(list(gen_types.keys()) + list(ref_types.keys()))
        if not all_types:
            return 1.0

        gen_total = max(len(gen_elements), 1)
        ref_total = max(len(ref_elements), 1)

        scores = []
        for t in all_types:
            gen_ratio = gen_types.get(t, 0) / gen_total
            ref_ratio = ref_types.get(t, 0) / ref_total
            scores.append(1.0 - abs(gen_ratio - ref_ratio))

        return self._mean(scores)

    def _compare_format_distribution(
        self,
        gen_elements: List[ContentElement],
        ref_elements: List[ContentElement],
    ) -> float:
        """比较格式签名分布"""
        gen_sigs = [self._element_signature(e) for e in gen_elements]
        ref_sigs = [self._element_signature(e) for e in ref_elements]

        gen_dist = Counter(gen_sigs)
        ref_dist = Counter(ref_sigs)

        all_sigs = set(list(gen_dist.keys()) + list(ref_dist.keys()))
        if not all_sigs:
            return 1.0

        gen_total = max(len(gen_sigs), 1)
        ref_total = max(len(ref_sigs), 1)

        scores = []
        for sig in all_sigs:
            gen_ratio = gen_dist.get(sig, 0) / gen_total
            ref_ratio = ref_dist.get(sig, 0) / ref_total
            scores.append(1.0 - abs(gen_ratio - ref_ratio))

        return self._mean(scores)

    def _compare_heading_distribution(
        self,
        gen_elements: List[ContentElement],
        ref_elements: List[ContentElement],
    ) -> float:
        """比较标题层级分布"""
        gen_levels = self._extract_heading_levels(gen_elements)
        ref_levels = self._extract_heading_levels(ref_elements)

        gen_dist = Counter(gen_levels)
        ref_dist = Counter(ref_levels)

        all_levels = set(list(gen_dist.keys()) + list(ref_dist.keys()))
        if not all_levels:
            return 1.0

        gen_total = max(len(gen_levels), 1)
        ref_total = max(len(ref_levels), 1)

        scores = []
        for level in all_levels:
            gen_ratio = gen_dist.get(level, 0) / gen_total
            ref_ratio = ref_dist.get(level, 0) / ref_total
            scores.append(1.0 - abs(gen_ratio - ref_ratio))

        return self._mean(scores)

    @staticmethod
    def _element_signature(element: ContentElement) -> str:
        """生成元素格式签名"""
        if element.element_type == ElementType.TABLE:
            return "TABLE"
        elif element.element_type == ElementType.IMAGE:
            return "IMAGE"
        elif element.element_type == ElementType.PARAGRAPH and element.paragraph:
            para = element.paragraph
            align = "L"
            if para.format and para.format.alignment:
                align = para.format.alignment[0].upper()

            font_size = 12.0
            if para.font and para.font.size:
                font_size = para.font.size

            if font_size >= 18:
                size_cat = "XL"
            elif font_size >= 14:
                size_cat = "LG"
            elif font_size >= 11:
                size_cat = "MD"
            else:
                size_cat = "SM"

            bold = "B" if para.font and para.font.bold else "n"

            level = para.level or 0
            if level > 0:
                return f"H{level}"

            return f"P_{align}_{size_cat}_{bold}"

        return "UNKNOWN"

    @staticmethod
    def _extract_heading_levels(elements: List[ContentElement]) -> List[str]:
        """提取标题层级分布"""
        levels = []
        for e in elements:
            if e.element_type == ElementType.PARAGRAPH and e.paragraph:
                level = e.paragraph.level or 0
                if level > 0:
                    levels.append(f"H{level}")
                else:
                    para = e.paragraph
                    is_title_like = False
                    if para.font:
                        if para.font.size and para.font.size >= 14 and para.font.bold:
                            is_title_like = True
                    if para.format and para.format.alignment == "center":
                        is_title_like = True
                    levels.append("TITLE_LIKE" if is_title_like else "BODY")
            elif e.element_type == ElementType.TABLE:
                levels.append("TABLE")
            elif e.element_type == ElementType.IMAGE:
                levels.append("IMG")
        return levels

    @staticmethod
    def _count_match(a: int, b: int) -> float:
        if a == 0 and b == 0:
            return 1.0
        if a == 0 or b == 0:
            return 0.0
        return min(a, b) / max(a, b)

    @staticmethod
    def _mean(values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0

"""图片对比维度"""

import hashlib
from typing import List, Tuple, Dict, Any
from pathlib import Path

from .base import ComparisonDimension
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.docx.parser import ContentElement, ElementType


class ImageComparisonDimension(ComparisonDimension):
    name = "image_comparison"
    weight = 0.08
    description = "图片对比（数量、尺寸、内容哈希）"

    def compare(
        self,
        gen_elements: List[ContentElement],
        ref_elements: List[ContentElement],
        gen_path: Path,
        ref_path: Path,
        match_result=None,
    ) -> Tuple[float, Dict[str, Any]]:
        try:
            gen_images = [e for e in gen_elements if e.element_type == ElementType.IMAGE]
            ref_images = [e for e in ref_elements if e.element_type == ElementType.IMAGE]

            if not gen_images and not ref_images:
                return 0.5, {"image_count": 0, "reason": "no_images_in_both"}

            count_score = self._count_match(len(gen_images), len(ref_images))

            pair_count = min(len(gen_images), len(ref_images))
            pair_scores = []
            dimension_matches = []

            for i in range(pair_count):
                pair_result = self._compare_image(gen_images[i], ref_images[i])
                pair_scores.append(pair_result["score"])
                dimension_matches.append(pair_result)

            avg_pair_score = self._mean(pair_scores) if pair_scores else 0.0
            score = count_score * 0.3 + avg_pair_score * 0.7

            details = {
                "gen_image_count": len(gen_images),
                "ref_image_count": len(ref_images),
                "count_score": round(count_score, 4),
                "per_image_scores": [round(d["score"], 4) for d in dimension_matches],
                "dimension_matches": dimension_matches,
            }
            return round(min(score, 1.0), 4), details

        except Exception as e:
            return 0.0, {"error": str(e)}

    def _count_match(self, a: int, b: int) -> float:
        if a == 0 and b == 0:
            return 1.0
        return min(a, b) / max(a, b)

    def _compare_image(self, gen_elem: ContentElement, ref_elem: ContentElement) -> Dict[str, Any]:
        sub_scores = []

        gen_w = gen_elem.image_width
        gen_h = gen_elem.image_height
        ref_w = ref_elem.image_width
        ref_h = ref_elem.image_height

        # 宽高比比较（PDF和DOCX的绝对尺寸可能差100倍，但宽高比应该接近）
        if gen_w and gen_h and ref_w and ref_h and gen_w > 0 and gen_h > 0 and ref_w > 0 and ref_h > 0:
            gen_ratio = gen_w / gen_h
            ref_ratio = ref_w / ref_h
            ratio_diff = abs(gen_ratio - ref_ratio) / max(gen_ratio, ref_ratio)
            aspect_score = max(0.0, 1.0 - ratio_diff)
            sub_scores.append(aspect_score)
        elif gen_w is None and ref_w is None:
            sub_scores.append(1.0)
        else:
            sub_scores.append(0.5)

        # 数据大小比较（图片数据量应该相近，即使编码不同）
        gen_size = len(gen_elem.image_data) if gen_elem.image_data else 0
        ref_size = len(ref_elem.image_data) if ref_elem.image_data else 0
        if gen_size > 0 and ref_size > 0:
            size_ratio = min(gen_size, ref_size) / max(gen_size, ref_size)
            sub_scores.append(size_ratio)
        elif gen_size == 0 and ref_size == 0:
            sub_scores.append(1.0)
        else:
            sub_scores.append(0.3)

        score = self._mean(sub_scores)

        return {
            "score": round(score, 4),
            "gen_size": gen_size,
            "ref_size": ref_size,
            "gen_aspect": round(gen_w / gen_h, 3) if gen_w and gen_h and gen_h > 0 else None,
            "ref_aspect": round(ref_w / ref_h, 3) if ref_w and ref_h and ref_h > 0 else None,
        }

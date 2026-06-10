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
                return 1.0, {"image_count": 0, "reason": "no_images"}

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
        ref_w = ref_elem.image_width
        if gen_w and ref_w:
            width_match = 1.0 - min(abs(gen_w - ref_w), abs(gen_w - ref_w)) / max(abs(gen_w), abs(ref_w), 1)
            sub_scores.append(max(0.0, width_match))
        elif gen_w is None and ref_w is None:
            sub_scores.append(1.0)
        else:
            sub_scores.append(0.5)

        gen_h = gen_elem.image_height
        ref_h = ref_elem.image_height
        if gen_h and ref_h:
            height_match = 1.0 - min(abs(gen_h - ref_h), abs(gen_h - ref_h)) / max(abs(gen_h), abs(ref_h), 1)
            sub_scores.append(max(0.0, height_match))
        elif gen_h is None and ref_h is None:
            sub_scores.append(1.0)
        else:
            sub_scores.append(0.5)

        gen_hash = self._image_hash(gen_elem.image_data)
        ref_hash = self._image_hash(ref_elem.image_data)
        if gen_hash and ref_hash:
            hash_match = 1.0 if gen_hash == ref_hash else 0.0
            sub_scores.append(hash_match)
        else:
            sub_scores.append(0.5)

        score = self._mean(sub_scores)

        return {
            "score": round(score, 4),
            "width_match": gen_w == ref_w if (gen_w and ref_w) else None,
            "height_match": gen_h == ref_h if (gen_h and ref_h) else None,
            "hash_match": gen_hash == ref_hash if (gen_hash and ref_hash) else None,
        }

    @staticmethod
    def _image_hash(data: bytes) -> str:
        if not data:
            return ""
        return hashlib.md5(data).hexdigest()

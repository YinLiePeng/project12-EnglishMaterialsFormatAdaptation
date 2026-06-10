"""段落格式对比维度"""

from typing import List, Tuple, Dict, Any
from pathlib import Path

from .base import ComparisonDimension
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.docx.parser import ContentElement, ElementType, ParagraphFormat
from font_utils import numeric_match


class ParagraphFormattingDimension(ComparisonDimension):
    name = "paragraph_formatting"
    weight = 0.10
    description = "段落格式对比（对齐、行距、缩进、间距等）"

    COMPARE_FIELDS = [
        "alignment",
        "line_spacing",
        "line_spacing_rule",
        "space_before",
        "space_after",
        "first_line_indent",
        "left_indent",
        "right_indent",
    ]

    def compare(
        self,
        gen_elements: List[ContentElement],
        ref_elements: List[ContentElement],
        gen_path: Path,
        ref_path: Path,
        match_result=None,
    ) -> Tuple[float, Dict[str, Any]]:
        try:
            if not match_result or not hasattr(match_result, "pairs"):
                return 1.0, {"reason": "no_match_result"}

            property_scores: Dict[str, List[float]] = {f: [] for f in self.COMPARE_FIELDS}

            for pair in match_result.pairs:
                if pair.gen_para is None or pair.ref_para is None:
                    continue

                gen_fmt = pair.gen_para.format
                ref_fmt = pair.ref_para.format
                if gen_fmt is None or ref_fmt is None:
                    continue

                for field_name in self.COMPARE_FIELDS:
                    gen_val = getattr(gen_fmt, field_name, None)
                    ref_val = getattr(ref_fmt, field_name, None)
                    score = self._compare_field(field_name, gen_val, ref_val)
                    property_scores[field_name].append(score)

            property_rates = {}
            for key, scores in property_scores.items():
                property_rates[key] = round(self._mean(scores), 4) if scores else 1.0

            score = self._mean(list(property_rates.values()))

            details = {
                "property_match_rates": property_rates,
            }
            return round(min(score, 1.0), 4), details

        except Exception as e:
            return 0.0, {"error": str(e)}

    def _compare_field(self, field_name: str, gen_val, ref_val) -> float:
        if field_name == "alignment":
            return self._alignment_match(gen_val, ref_val)
        if field_name in ("line_spacing", "space_before", "space_after",
                          "first_line_indent", "left_indent", "right_indent"):
            return numeric_match(gen_val, ref_val, tolerance=0.05)
        if field_name == "line_spacing_rule":
            return self._string_match(gen_val, ref_val)
        return 1.0

    @staticmethod
    def _alignment_match(gen_val, ref_val) -> float:
        a = str(gen_val).lower() if gen_val else "left"
        b = str(ref_val).lower() if ref_val else "left"
        if a == b:
            return 1.0
        alignment_groups = [
            {"left", "justify", "both"},
            {"center"},
            {"right"},
        ]
        for group in alignment_groups:
            if a in group and b in group:
                return 0.8
        return 0.0

    @staticmethod
    def _string_match(gen_val, ref_val) -> float:
        a = str(gen_val).lower() if gen_val else ""
        b = str(ref_val).lower() if ref_val else ""
        if a == b:
            return 1.0
        if not a and not b:
            return 1.0
        return 0.0

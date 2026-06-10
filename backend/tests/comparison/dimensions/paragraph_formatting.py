"""段落格式对比维度"""

from typing import List, Tuple, Dict, Any
from pathlib import Path

from .base import ComparisonDimension
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.docx.parser import ContentElement, ElementType, ParagraphFormat


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
                    score = self._compare_field(field_name, gen_val, ref_val, gen_fmt, ref_fmt)
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

    def _compare_field(self, field_name: str, gen_val, ref_val, gen_fmt=None, ref_fmt=None) -> float:
        if field_name == "alignment":
            return self._alignment_match(gen_val, ref_val)
        if field_name == "line_spacing":
            return self._line_spacing_match(gen_val, ref_val, gen_fmt, ref_fmt)
        if field_name == "line_spacing_rule":
            return self._line_spacing_rule_match(gen_val, ref_val)
        if field_name in ("space_before", "space_after"):
            return self._spacing_match(gen_val, ref_val)
        if field_name in ("first_line_indent", "left_indent", "right_indent"):
            return self._indent_match(gen_val, ref_val)
        return 1.0

    @staticmethod
    def _alignment_match(gen_val, ref_val) -> float:
        a = str(gen_val).lower() if gen_val else "left"
        b = str(ref_val).lower() if ref_val else "left"
        if a == b:
            return 1.0
        # justify和both等价
        equiv = {"left", "justify", "both"}
        if a in equiv and b in equiv:
            return 0.9
        return 0.0

    @staticmethod
    def _line_spacing_match(gen_val, ref_val, gen_fmt=None, ref_fmt=None) -> float:
        """行距匹配 - 考虑不同行距规则"""
        if gen_val is None and ref_val is None:
            return 1.0
        if gen_val is None or ref_val is None:
            return 0.5  # 一方有行距一方没有，给部分分

        try:
            gen_ls = float(gen_val)
            ref_ls = float(ref_val)
        except (ValueError, TypeError):
            return 0.0

        # 获取行距规则
        gen_rule = str(gen_fmt.line_spacing_rule).lower() if gen_fmt and gen_fmt.line_spacing_rule else "auto"
        ref_rule = str(ref_fmt.line_spacing_rule).lower() if ref_fmt and ref_fmt.line_spacing_rule else "auto"

        # 如果规则不同，需要转换单位
        # auto规则的值是倍数（如1.15表示1.15倍行距）
        # exact规则的值是磅数（如11pt）
        if gen_rule != ref_rule:
            # 不同规则，给一个基础分（因为无法直接比较）
            # 但不算完全不匹配
            return 0.3

        # 相同规则，比较数值
        if gen_rule == "auto":
            # 倍数模式，容差较大
            diff = abs(gen_ls - ref_ls) / max(ref_ls, 0.01)
            if diff < 0.05:
                return 1.0
            return max(0.0, 1.0 - diff)
        else:
            # 精确模式（pt），容差1pt
            diff = abs(gen_ls - ref_ls)
            if diff < 0.5:
                return 1.0
            if diff < 2.0:
                return max(0.5, 1.0 - diff / 10.0)
            return max(0.0, 1.0 - diff / 20.0)

    @staticmethod
    def _line_spacing_rule_match(gen_val, ref_val) -> float:
        """行距规则匹配"""
        a = str(gen_val).lower() if gen_val else "auto"
        b = str(ref_val).lower() if ref_val else "auto"
        if a == b:
            return 1.0
        # auto和multiple是等价的
        equiv = {"auto", "multiple"}
        if a in equiv and b in equiv:
            return 1.0
        return 0.0

    @staticmethod
    def _spacing_match(gen_val, ref_val) -> float:
        """段前段后距匹配 - 容差2pt"""
        if gen_val is None and ref_val is None:
            return 1.0
        if gen_val is None or ref_val is None:
            return 0.5
        try:
            g = float(gen_val)
            r = float(ref_val)
        except (ValueError, TypeError):
            return 0.0

        if g == 0 and r == 0:
            return 1.0
        if g == 0 or r == 0:
            # 一方为0一方不为0
            diff = abs(g - r)
            if diff < 3:
                return 0.5
            return 0.0

        diff = abs(g - r)
        if diff < 1:
            return 1.0
        if diff < 3:
            return 0.8
        if diff < 6:
            return 0.5
        return max(0.0, 1.0 - diff / 20.0)

    @staticmethod
    def _indent_match(gen_val, ref_val) -> float:
        """缩进匹配 - 容差0.5cm"""
        if gen_val is None and ref_val is None:
            return 1.0
        if gen_val is None or ref_val is None:
            return 0.5
        try:
            g = float(gen_val)
            r = float(ref_val)
        except (ValueError, TypeError):
            return 0.0

        if g == 0 and r == 0:
            return 1.0
        if g == 0 or r == 0:
            diff = abs(g - r)
            if diff < 0.5:
                return 0.7
            return 0.0

        diff = abs(g - r)
        if diff < 0.2:
            return 1.0
        if diff < 0.5:
            return 0.8
        if diff < 1.0:
            return 0.5
        return max(0.0, 1.0 - diff / 5.0)

    @staticmethod
    def _mean(values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0

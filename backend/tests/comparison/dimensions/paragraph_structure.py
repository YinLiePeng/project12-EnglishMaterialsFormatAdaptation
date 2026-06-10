"""段落结构对比维度"""

from difflib import SequenceMatcher
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path

from .base import ComparisonDimension
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.docx.parser import ElementType, ParagraphFormat


class ParagraphStructureDimension(ComparisonDimension):
    """对比段落结构：段落数量、匹配率、格式序列相似度"""

    name = "paragraph_structure"
    weight = 0.10
    description = "对比段落结构一致性（段落数量、匹配率、格式序列）"

    def compare(
        self,
        gen_elements: List,
        ref_elements: List,
        gen_path: Path,
        ref_path: Path,
        match_result: Any = None,
    ) -> Tuple[float, Dict[str, Any]]:

        gen_paras = [
            e for e in gen_elements if e.element_type == ElementType.PARAGRAPH
        ]
        ref_paras = [
            e for e in ref_elements if e.element_type == ElementType.PARAGRAPH
        ]

        gen_count = len(gen_paras)
        ref_count = len(ref_paras)

        # 段落数量匹配
        if gen_count == 0 and ref_count == 0:
            count_score = 1.0
        elif gen_count == 0 or ref_count == 0:
            count_score = 0.0
        else:
            count_score = min(gen_count, ref_count) / max(gen_count, ref_count)

        # 从 match_result 获取匹配率
        match_rate = self._extract_match_rate(match_result)

        # 格式属性序列相似度（替代样式名比较）
        format_sim = self._compare_format_sequences(gen_paras, ref_paras, match_result)

        # 综合分数：数量 + 匹配率 + 格式相似度
        score = count_score * 0.2 + match_rate * 0.4 + format_sim * 0.4
        score = max(0.0, min(1.0, score))

        details = {
            "gen_count": gen_count,
            "ref_count": ref_count,
            "count_score": round(count_score, 4),
            "match_rate": round(match_rate, 4),
            "format_sequence_similarity": round(format_sim, 4),
        }

        return score, details

    def _compare_format_sequences(
        self, gen_paras: List, ref_paras: List, match_result: Any
    ) -> float:
        """比较格式属性序列（对齐+字号+加粗的组合序列）"""
        if not match_result or not hasattr(match_result, "pairs"):
            # 回退：按位置比较格式
            gen_fmts = [self._para_signature(e) for e in gen_paras]
            ref_fmts = [self._para_signature(e) for e in ref_paras]
            return SequenceMatcher(None, gen_fmts, ref_fmts).ratio()

        # 使用匹配结果比较
        scores = []
        for pair in match_result.pairs:
            if pair.gen_para is None or pair.ref_para is None:
                continue
            gen_sig = self._format_signature(pair.gen_para)
            ref_sig = self._format_signature(pair.ref_para)
            if gen_sig == ref_sig:
                scores.append(1.0)
            else:
                # 部分匹配：比较各属性
                scores.append(self._partial_format_match(pair.gen_para.format, pair.ref_para.format))

        return self._mean(scores) if scores else 0.0

    @staticmethod
    def _para_signature(element) -> str:
        """从ContentElement生成格式签名"""
        if element.paragraph is None:
            return ""
        fmt = element.paragraph.format
        return ParagraphStructureDimension._format_signature_from_fmt(fmt)

    @staticmethod
    def _format_signature(para) -> str:
        """从ParagraphInfo生成格式签名"""
        if para is None:
            return ""
        return ParagraphStructureDimension._format_signature_from_fmt(para.format)

    @staticmethod
    def _format_signature_from_fmt(fmt: ParagraphFormat) -> str:
        """从ParagraphFormat生成格式签名（对齐+字号范围+加粗）"""
        if fmt is None:
            return ""
        align = fmt.alignment or "left"
        return f"{align}"

    @staticmethod
    def _partial_format_match(gen_fmt, ref_fmt) -> float:
        """部分格式匹配得分"""
        if gen_fmt is None or ref_fmt is None:
            return 0.0

        scores = []

        # 对齐方式
        gen_align = (gen_fmt.alignment or "left").lower()
        ref_align = (ref_fmt.alignment or "left").lower()
        scores.append(1.0 if gen_align == ref_align else 0.0)

        # 行距
        if gen_fmt.line_spacing is not None and ref_fmt.line_spacing is not None:
            diff = abs(gen_fmt.line_spacing - ref_fmt.line_spacing) / max(ref_fmt.line_spacing, 0.01)
            scores.append(max(0.0, 1.0 - diff))
        elif gen_fmt.line_spacing is None and ref_fmt.line_spacing is None:
            scores.append(1.0)

        # 段前距
        if gen_fmt.space_before is not None and ref_fmt.space_before is not None:
            diff = abs(gen_fmt.space_before - ref_fmt.space_before) / max(ref_fmt.space_before, 0.01)
            scores.append(max(0.0, 1.0 - diff))
        elif gen_fmt.space_before is None and ref_fmt.space_before is None:
            scores.append(1.0)

        # 段后距
        if gen_fmt.space_after is not None and ref_fmt.space_after is not None:
            diff = abs(gen_fmt.space_after - ref_fmt.space_after) / max(ref_fmt.space_after, 0.01)
            scores.append(max(0.0, 1.0 - diff))
        elif gen_fmt.space_after is None and ref_fmt.space_after is None:
            scores.append(1.0)

        # 缩进
        if gen_fmt.first_line_indent is not None and ref_fmt.first_line_indent is not None:
            diff = abs(gen_fmt.first_line_indent - ref_fmt.first_line_indent) / max(abs(ref_fmt.first_line_indent), 0.01)
            scores.append(max(0.0, 1.0 - diff))
        elif gen_fmt.first_line_indent is None and ref_fmt.first_line_indent is None:
            scores.append(1.0)

        return sum(scores) / len(scores) if scores else 0.0

    @staticmethod
    def _extract_match_rate(match_result: Any) -> float:
        """从 match_result 中提取匹配率"""
        if match_result is None:
            return 0.0
        try:
            if hasattr(match_result, "match_rate"):
                return float(match_result.match_rate)
            elif isinstance(match_result, dict) and "match_rate" in match_result:
                return float(match_result["match_rate"])
        except Exception:
            pass
        return 0.0

    @staticmethod
    def _mean(values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0

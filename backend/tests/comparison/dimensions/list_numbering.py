"""列表编号对比维度"""

from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path

from .base import ComparisonDimension


class ListNumberingDimension(ComparisonDimension):
    """对比列表编号：检查匹配段落对的编号格式一致性"""

    name = "list_numbering"
    weight = 0.05
    description = "对比列表编号格式（编号类型、缩进层级、起始值）"

    def compare(
        self,
        gen_elements: List,
        ref_elements: List,
        gen_path: Path,
        ref_path: Path,
        match_result: Any = None,
    ) -> Tuple[float, Dict[str, Any]]:
        matched_pairs = self._extract_matched_pairs(match_result)

        if not matched_pairs:
            return 0.5, {
                "numbering_match_rate": 0.5,
                "total_pairs": 0,
                "details": [],
            }

        from docx import Document as DocxDocument
        from docx.oxml.ns import qn

        gen_doc = None
        ref_doc = None
        try:
            gen_doc = DocxDocument(str(gen_path))
        except Exception:
            pass
        try:
            ref_doc = DocxDocument(str(ref_path))
        except Exception:
            pass

        scores = []
        details = []

        for gen_idx, ref_idx in matched_pairs:
            gen_para = self._get_paragraph(gen_doc, gen_elements, gen_idx)
            ref_para = self._get_paragraph(ref_doc, ref_elements, ref_idx)

            gen_num = self._extract_numbering(gen_para, qn) if gen_para is not None else None
            ref_num = self._extract_numbering(ref_para, qn) if ref_para is not None else None

            pair_score, pair_detail = self._compare_numbering_pair(
                gen_num, ref_num, gen_idx, ref_idx
            )
            scores.append(pair_score)
            details.append(pair_detail)

        match_rate = sum(scores) / len(scores) if scores else 1.0

        return match_rate, {
            "numbering_match_rate": round(match_rate, 4),
            "total_pairs": len(matched_pairs),
            "details": details,
        }

    @staticmethod
    def _extract_matched_pairs(match_result: Any) -> List[tuple]:
        """从 match_result 提取匹配对列表 (gen_index, ref_index)"""
        if match_result is None:
            return []
        try:
            # MatcherOutput 对象有 pairs 属性
            if hasattr(match_result, "pairs"):
                return [
                    (p.gen_index, p.ref_index)
                    for p in match_result.pairs
                    if p.gen_para is not None and p.ref_para is not None
                    and p.match_type not in ("unmatched_gen", "unmatched_ref")
                ]
            # 兼容 dict 格式
            if isinstance(match_result, dict) and "pairs" in match_result:
                return [
                    (p["gen_index"], p["ref_index"])
                    for p in match_result["pairs"]
                    if p.get("gen_para") is not None and p.get("ref_para") is not None
                ]
        except Exception:
            pass
        return []

    @staticmethod
    def _get_paragraph(doc, elements, index):
        """获取段落对象，优先从 python-docx Document 获取"""
        if doc is not None:
            try:
                paras = doc.paragraphs
                if 0 <= index < len(paras):
                    return paras[index]
            except Exception:
                pass
        # fallback: 从 elements 获取
        from app.services.docx.parser import ElementType

        para_elements = [
            e for e in elements if e.element_type == ElementType.PARAGRAPH
        ]
        if 0 <= index < len(para_elements):
            elem = para_elements[index]
            if elem.paragraph is not None:
                return elem.paragraph
        return None

    @staticmethod
    def _extract_numbering(para, qn) -> Optional[Dict[str, Any]]:
        """从段落 XML 中提取编号信息"""
        try:
            # para 可能是 python-docx Paragraph 或 ParagraphInfo
            if hasattr(para, "_element"):
                p_elem = para._element
            elif hasattr(para, "element"):
                p_elem = para.element
            else:
                return None

            pPr = p_elem.find(qn("w:pPr"))
            if pPr is None:
                return None

            numPr = pPr.find(qn("w:numPr"))
            if numPr is None:
                return None

            result = {}

            ilvl_elem = numPr.find(qn("w:ilvl"))
            if ilvl_elem is not None:
                val = ilvl_elem.get(qn("w:val"))
                if val is not None:
                    result["ilvl"] = int(val)

            numId_elem = numPr.find(qn("w:numId"))
            if numId_elem is not None:
                val = numId_elem.get(qn("w:val"))
                if val is not None:
                    result["numId"] = int(val)

            return result if result else None
        except Exception:
            return None

    @staticmethod
    def _compare_numbering_pair(
        gen_num: Optional[Dict], ref_num: Optional[Dict],
        gen_idx: int, ref_idx: int,
    ) -> Tuple[float, Dict[str, Any]]:
        """比较一对段落的编号信息"""
        detail = {
            "gen_index": gen_idx,
            "ref_index": ref_idx,
            "gen_has_numbering": gen_num is not None,
            "ref_has_numbering": ref_num is not None,
        }

        # 两者都没有编号
        if gen_num is None and ref_num is None:
            detail["score"] = 1.0
            detail["reason"] = "both_no_numbering"
            return 1.0, detail

        # 只有一方有编号
        if gen_num is None or ref_num is None:
            detail["score"] = 0.0
            detail["reason"] = "numbering_presence_mismatch"
            return 0.0, detail

        # 两者都有编号，比较属性
        sub_scores = []

        # 比较 ilvl
        gen_ilvl = gen_num.get("ilvl")
        ref_ilvl = ref_num.get("ilvl")
        if gen_ilvl is not None and ref_ilvl is not None:
            ilvl_match = 1.0 if gen_ilvl == ref_ilvl else 0.0
            sub_scores.append(ilvl_match)
            detail["ilvl_match"] = ilvl_match == 1.0
            detail["gen_ilvl"] = gen_ilvl
            detail["ref_ilvl"] = ref_ilvl

        # 比较 numId（编号定义引用）
        gen_numId = gen_num.get("numId")
        ref_numId = ref_num.get("numId")
        if gen_numId is not None and ref_numId is not None:
            detail["gen_numId"] = gen_numId
            detail["ref_numId"] = ref_numId

        score = sum(sub_scores) / len(sub_scores) if sub_scores else 1.0
        detail["score"] = round(score, 4)
        detail["reason"] = "numbering_compared"
        return score, detail

"""文本内容对比维度"""

from difflib import SequenceMatcher
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path

from .base import ComparisonDimension
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.docx.parser import ContentElement, ElementType
from run_matcher import RunMatcher


class TextContentDimension(ComparisonDimension):
    name = "text_content"
    weight = 0.20
    description = "文本内容相似度对比"

    def compare(
        self,
        gen_elements: List[ContentElement],
        ref_elements: List[ContentElement],
        gen_path: Path,
        ref_path: Path,
        match_result=None,
    ) -> Tuple[float, Dict[str, Any]]:
        try:
            gen_text = self._extract_full_text(gen_elements)
            ref_text = self._extract_full_text(ref_elements)

            if not gen_text and not ref_text:
                return 1.0, {"overall_similarity": 1.0, "reason": "both_empty"}

            overall_similarity = SequenceMatcher(None, gen_text, ref_text).ratio()

            para_scores = []
            matched_count = 0
            worst_paragraphs = []

            if match_result and hasattr(match_result, "pairs"):
                for pair in match_result.pairs:
                    if pair.gen_para is None or pair.ref_para is None:
                        continue
                    matched_count += 1
                    gen_runs = pair.gen_para.runs or []
                    ref_runs = pair.ref_para.runs or []
                    if not gen_runs and not ref_runs:
                        para_scores.append(1.0)
                        continue

                    # 段落级文本相似度（始终计算）
                    para_text_sim = SequenceMatcher(
                        None, pair.gen_para.text, pair.ref_para.text
                    ).ratio()

                    # Run级比较（当run结构相似时使用）
                    if len(gen_runs) > 0 and len(ref_runs) > 0:
                        run_ratio = min(len(gen_runs), len(ref_runs)) / max(len(gen_runs), len(ref_runs))
                        if run_ratio > 0.3:  # run结构相似时才用run级比较
                            matcher = RunMatcher(gen_runs, ref_runs)
                            run_output = matcher.match()
                            run_sim = self._calc_run_text_similarity(run_output.pairs)
                            # 取run级和段落级的较高者
                            para_scores.append(max(run_sim, para_text_sim))
                        else:
                            # run结构差异大，直接用段落级比较
                            para_scores.append(para_text_sim)
                    else:
                        para_scores.append(para_text_sim)

                    if para_scores[-1] < 0.8:
                        worst_paragraphs.append({
                            "gen_text": pair.gen_para.text[:80],
                            "ref_text": pair.ref_para.text[:80],
                            "similarity": round(para_scores[-1], 4),
                        })

                unmatched_gen = len(match_result.unmatched_gen) if hasattr(match_result, "unmatched_gen") else 0
                unmatched_ref = len(match_result.unmatched_ref) if hasattr(match_result, "unmatched_ref") else 0
            else:
                gen_paras = [e.paragraph for e in gen_elements if e.element_type == ElementType.PARAGRAPH and e.paragraph]
                ref_paras = [e.paragraph for e in ref_elements if e.element_type == ElementType.PARAGRAPH and e.paragraph]
                min_len = min(len(gen_paras), len(ref_paras))
                for i in range(min_len):
                    sim = SequenceMatcher(None, gen_paras[i].text, ref_paras[i].text).ratio()
                    para_scores.append(sim)
                    matched_count += 1
                unmatched_gen = max(0, len(gen_paras) - min_len)
                unmatched_ref = max(0, len(ref_paras) - min_len)

            para_sim = self._mean(para_scores) if para_scores else 0.0
            score = overall_similarity * 0.4 + para_sim * 0.6

            worst_paragraphs.sort(key=lambda x: x["similarity"])
            details = {
                "overall_similarity": round(overall_similarity, 4),
                "paragraph_similarity": round(para_sim, 4),
                "matched_paragraph_count": matched_count,
                "unmatched_gen_count": unmatched_gen,
                "unmatched_ref_count": unmatched_ref,
                "worst_paragraphs": worst_paragraphs[:5],
            }
            return round(min(score, 1.0), 4), details

        except Exception as e:
            return 0.0, {"error": str(e)}

    def _extract_full_text(self, elements: List[ContentElement]) -> str:
        parts = []
        for e in elements:
            if e.element_type == ElementType.PARAGRAPH and e.paragraph:
                parts.append(e.paragraph.text)
            elif e.element_type == ElementType.TABLE and e.table_cells:
                for row in e.table_cells:
                    for cell in row:
                        if cell.text:
                            parts.append(cell.text)
        return "\n".join(parts)

    def _calc_run_text_similarity(self, pairs) -> float:
        if not pairs:
            return 0.0
        total_sim = 0.0
        count = 0
        for p in pairs:
            if p.match_type in ("unmatched_gen", "unmatched_ref"):
                continue
            total_sim += p.text_similarity
            count += 1
        if count == 0:
            return 0.0
        return total_sim / count

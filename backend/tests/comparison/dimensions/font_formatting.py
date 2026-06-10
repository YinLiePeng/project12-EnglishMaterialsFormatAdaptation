"""字体格式对比维度"""

from typing import List, Tuple, Dict, Any
from pathlib import Path

from .base import ComparisonDimension
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.docx.parser import ContentElement, ElementType
from font_utils import fuzzy_font_match, color_similarity, numeric_match
from run_matcher import RunMatcher


class FontFormattingDimension(ComparisonDimension):
    name = "font_formatting"
    weight = 0.12
    description = "字体格式对比（字体名、字号、粗体、斜体、下划线、颜色）"

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

            property_scores: Dict[str, List[float]] = {
                "font_name": [],
                "font_size": [],
                "bold": [],
                "italic": [],
                "underline": [],
                "color": [],
            }
            worst_paragraphs = []

            for pair in match_result.pairs:
                if pair.gen_para is None or pair.ref_para is None:
                    continue

                gen_runs = pair.gen_para.runs or []
                ref_runs = pair.ref_para.runs or []
                if not gen_runs and not ref_runs:
                    for key in property_scores:
                        property_scores[key].append(1.0)
                    continue

                matcher = RunMatcher(gen_runs, ref_runs)
                run_output = matcher.match()

                pair_scores = {k: [] for k in property_scores}

                for rp in run_output.pairs:
                    if rp.gen_run is None or rp.ref_run is None:
                        continue

                    pair_scores["font_name"].append(
                        fuzzy_font_match(rp.gen_run.font_name, rp.ref_run.font_name)
                    )
                    pair_scores["font_size"].append(
                        numeric_match(rp.gen_run.font_size, rp.ref_run.font_size, tolerance=0.5)
                    )
                    pair_scores["bold"].append(
                        1.0 if rp.gen_run.bold == rp.ref_run.bold else 0.0
                    )
                    pair_scores["italic"].append(
                        1.0 if rp.gen_run.italic == rp.ref_run.italic else 0.0
                    )
                    pair_scores["underline"].append(
                        1.0 if rp.gen_run.underline == rp.ref_run.underline else 0.0
                    )
                    pair_scores["color"].append(
                        color_similarity(rp.gen_run.color, rp.ref_run.color)
                    )

                for key in property_scores:
                    if pair_scores[key]:
                        avg = sum(pair_scores[key]) / len(pair_scores[key])
                        property_scores[key].append(avg)

                pair_avg = self._mean([
                    self._mean(pair_scores[k]) for k in pair_scores if pair_scores[k]
                ])
                if pair_avg < 0.8:
                    worst_paragraphs.append({
                        "gen_text": pair.gen_para.text[:60],
                        "ref_text": pair.ref_para.text[:60],
                        "score": round(pair_avg, 4),
                        "details": {
                            k: round(self._mean(pair_scores[k]), 4)
                            for k in pair_scores if pair_scores[k]
                        },
                    })

            property_rates = {}
            for key, scores in property_scores.items():
                property_rates[key] = round(self._mean(scores), 4) if scores else 1.0

            score = self._mean(list(property_rates.values()))
            worst_paragraphs.sort(key=lambda x: x["score"])

            details = {
                "property_match_rates": property_rates,
                "worst_paragraphs": worst_paragraphs[:5],
            }
            return round(min(score, 1.0), 4), details

        except Exception as e:
            return 0.0, {"error": str(e)}

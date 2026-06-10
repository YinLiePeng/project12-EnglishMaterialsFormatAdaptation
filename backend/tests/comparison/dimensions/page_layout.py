"""页面布局对比维度"""

from typing import List, Tuple, Dict, Any
from pathlib import Path

from .base import ComparisonDimension
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from font_utils import numeric_match


class PageLayoutDimension(ComparisonDimension):
    """对比页面布局：页面尺寸、页边距、页眉页脚距离"""

    name = "page_layout"
    weight = 0.05
    description = "对比页面布局参数（纸张大小、页边距、页眉页脚距离）"

    # EMU 转 cm 的除数: 914400 * 2.54 ≈ 2,322,576
    EMU_TO_CM_DIVISOR = 914400 * 2.54

    def compare(
        self,
        gen_elements: List,
        ref_elements: List,
        gen_path: Path,
        ref_path: Path,
        match_result: Any = None,
    ) -> Tuple[float, Dict[str, Any]]:
        from docx import Document as DocxDocument

        gen_props = self._extract_layout(gen_path, DocxDocument)
        ref_props = self._extract_layout(ref_path, DocxDocument)

        if gen_props is None and ref_props is None:
            return 1.0, self._build_empty_details()

        if gen_props is None or ref_props is None:
            return 0.0, self._build_empty_details()

        property_names = [
            "page_width",
            "page_height",
            "left_margin",
            "right_margin",
            "top_margin",
            "bottom_margin",
            "header_distance",
            "footer_distance",
        ]

        prop_scores = {}
        prop_values = {}

        for name in property_names:
            gen_val = gen_props.get(name)
            ref_val = ref_props.get(name)
            score = numeric_match(gen_val, ref_val, tolerance=0.02)
            prop_scores[name] = round(score, 4)
            prop_values[name] = {
                "gen": round(gen_val, 2) if gen_val is not None else None,
                "ref": round(ref_val, 2) if ref_val is not None else None,
            }

        score = sum(prop_scores.values()) / len(prop_scores) if prop_scores else 0.0
        score = max(0.0, min(1.0, score))

        return score, {
            "property_scores": prop_scores,
            "property_values": prop_values,
        }

    def _extract_layout(self, path: Path, DocxDocument) -> Any:
        """从文档第一个 section 提取页面布局参数"""
        try:
            doc = DocxDocument(str(path))
            if not doc.sections:
                return None

            sec = doc.sections[0]
            props = {}

            # 页面宽度和高度
            props["page_width"] = self._emu_to_cm(sec.page_width)
            props["page_height"] = self._emu_to_cm(sec.page_height)

            # 页边距
            props["left_margin"] = self._emu_to_cm(sec.left_margin)
            props["right_margin"] = self._emu_to_cm(sec.right_margin)
            props["top_margin"] = self._emu_to_cm(sec.top_margin)
            props["bottom_margin"] = self._emu_to_cm(sec.bottom_margin)

            # 页眉页脚距离
            props["header_distance"] = self._emu_to_cm(sec.header_distance)
            props["footer_distance"] = self._emu_to_cm(sec.footer_distance)

            return props
        except Exception:
            return None

    def _emu_to_cm(self, emu_value) -> float:
        """将 EMU 值转换为 cm"""
        if emu_value is None:
            return 0.0
        try:
            return float(emu_value) / self.EMU_TO_CM_DIVISOR
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _build_empty_details() -> Dict[str, Any]:
        """构建空的详情字典"""
        return {
            "property_scores": {},
            "property_values": {},
        }

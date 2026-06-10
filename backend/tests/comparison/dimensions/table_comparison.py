"""表格对比维度"""

from difflib import SequenceMatcher
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path

from .base import ComparisonDimension
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.docx.parser import ContentElement, ElementType, TableCellInfo, CellFormatInfo
from font_utils import list_similarity, numeric_match


class TableComparisonDimension(ComparisonDimension):
    name = "table_comparison"
    weight = 0.13
    description = "表格对比（行列数、单元格内容、格式等）"

    def compare(
        self,
        gen_elements: List[ContentElement],
        ref_elements: List[ContentElement],
        gen_path: Path,
        ref_path: Path,
        match_result=None,
    ) -> Tuple[float, Dict[str, Any]]:
        try:
            gen_tables = [e for e in gen_elements if e.element_type == ElementType.TABLE]
            ref_tables = [e for e in ref_elements if e.element_type == ElementType.TABLE]

            if not gen_tables and not ref_tables:
                return 1.0, {"table_count": 0, "reason": "no_tables"}

            count_score = self._count_match(len(gen_tables), len(ref_tables))

            pair_count = min(len(gen_tables), len(ref_tables))
            table_scores = []

            for i in range(pair_count):
                table_score = self._compare_table(gen_tables[i], ref_tables[i])
                table_scores.append(table_score)

            avg_table_score = self._mean(table_scores) if table_scores else 0.0
            score = count_score * 0.2 + avg_table_score * 0.8

            details = {
                "gen_table_count": len(gen_tables),
                "ref_table_count": len(ref_tables),
                "count_score": round(count_score, 4),
                "per_table_scores": [round(s, 4) for s in table_scores],
            }
            return round(min(score, 1.0), 4), details

        except Exception as e:
            return 0.0, {"error": str(e)}

    def _count_match(self, a: int, b: int) -> float:
        if a == 0 and b == 0:
            return 1.0
        return min(a, b) / max(a, b)

    def _compare_table(self, gen_elem: ContentElement, ref_elem: ContentElement) -> float:
        gen_cells = gen_elem.table_cells or []
        ref_cells = ref_elem.table_cells or []
        gen_fmt = gen_elem.table_format
        ref_fmt = ref_elem.table_format

        scores = []

        row_score = self._count_match(len(gen_cells), len(ref_cells))
        scores.append(row_score)

        gen_cols = max((len(row) for row in gen_cells), default=0)
        ref_cols = max((len(row) for row in ref_cells), default=0)
        col_score = self._count_match(gen_cols, ref_cols)
        scores.append(col_score)

        cell_text_scores = self._compare_cell_texts(gen_cells, ref_cells)
        scores.extend(cell_text_scores)

        if gen_fmt and ref_fmt:
            col_width_score = list_similarity(gen_fmt.column_widths, ref_fmt.column_widths)
            scores.append(col_width_score)

        grid_span_scores = self._compare_grid_spans(gen_cells, ref_cells)
        scores.extend(grid_span_scores)

        v_merge_scores = self._compare_v_merges(gen_cells, ref_cells)
        scores.extend(v_merge_scores)

        format_scores = self._compare_cell_formats(gen_cells, ref_cells)
        scores.extend(format_scores)

        return self._mean(scores) if scores else 0.0

    def _compare_cell_texts(
        self,
        gen_cells: List[List[TableCellInfo]],
        ref_cells: List[List[TableCellInfo]],
    ) -> List[float]:
        scores = []
        min_rows = min(len(gen_cells), len(ref_cells))
        for r in range(min_rows):
            gen_row = gen_cells[r]
            ref_row = ref_cells[r]
            min_cols = min(len(gen_row), len(ref_row))
            for c in range(min_cols):
                gen_text = gen_row[c].text or ""
                ref_text = ref_row[c].text or ""
                if not gen_text and not ref_text:
                    scores.append(1.0)
                elif not gen_text or not ref_text:
                    scores.append(0.0)
                else:
                    scores.append(SequenceMatcher(None, gen_text, ref_text).ratio())
        return scores

    def _compare_grid_spans(
        self,
        gen_cells: List[List[TableCellInfo]],
        ref_cells: List[List[TableCellInfo]],
    ) -> List[float]:
        scores = []
        min_rows = min(len(gen_cells), len(ref_cells))
        for r in range(min_rows):
            min_cols = min(len(gen_cells[r]), len(ref_cells[r]))
            for c in range(min_cols):
                gen_gs = gen_cells[r][c].grid_span
                ref_gs = ref_cells[r][c].grid_span
                if gen_gs == ref_gs:
                    scores.append(1.0)
                else:
                    scores.append(min(gen_gs, ref_gs) / max(gen_gs, ref_gs))
        return scores

    def _compare_v_merges(
        self,
        gen_cells: List[List[TableCellInfo]],
        ref_cells: List[List[TableCellInfo]],
    ) -> List[float]:
        scores = []
        min_rows = min(len(gen_cells), len(ref_cells))
        for r in range(min_rows):
            min_cols = min(len(gen_cells[r]), len(ref_cells[r]))
            for c in range(min_cols):
                gen_vm = gen_cells[r][c].v_merge
                ref_vm = ref_cells[r][c].v_merge
                if gen_vm == ref_vm:
                    scores.append(1.0)
                elif gen_vm is None and ref_vm is None:
                    scores.append(1.0)
                else:
                    scores.append(0.0)
        return scores

    def _compare_cell_formats(
        self,
        gen_cells: List[List[TableCellInfo]],
        ref_cells: List[List[TableCellInfo]],
    ) -> List[float]:
        scores = []
        min_rows = min(len(gen_cells), len(ref_cells))
        for r in range(min_rows):
            min_cols = min(len(gen_cells[r]), len(ref_cells[r]))
            for c in range(min_cols):
                gen_cf = gen_cells[r][c].cell_format
                ref_cf = ref_cells[r][c].cell_format
                if gen_cf is None and ref_cf is None:
                    scores.append(1.0)
                    continue
                if gen_cf is None or ref_cf is None:
                    scores.append(0.5)
                    continue

                sub_scores = []

                if gen_cf.vertical_alignment == ref_cf.vertical_alignment:
                    sub_scores.append(1.0)
                else:
                    sub_scores.append(0.0)

                gen_fill = gen_cf.shading_fill or ""
                ref_fill = ref_cf.shading_fill or ""
                if gen_fill == ref_fill:
                    sub_scores.append(1.0)
                elif not gen_fill and not ref_fill:
                    sub_scores.append(1.0)
                else:
                    sub_scores.append(0.0)

                sub_scores.append(self._compare_borders(gen_cf.borders, ref_cf.borders))
                sub_scores.append(self._compare_margins(gen_cf.margins, ref_cf.margins))

                scores.append(self._mean(sub_scores))

        return scores

    def _compare_borders(
        self,
        gen_borders: Optional[Dict],
        ref_borders: Optional[Dict],
    ) -> float:
        if gen_borders is None and ref_borders is None:
            return 1.0
        if gen_borders is None or ref_borders is None:
            return 0.0

        all_sides = set(list(gen_borders.keys()) + list(ref_borders.keys()))
        if not all_sides:
            return 1.0

        match_count = 0
        for side in all_sides:
            g = gen_borders.get(side, {})
            r = ref_borders.get(side, {})
            if g.get("val") == r.get("val") and g.get("sz") == r.get("sz"):
                match_count += 1

        return match_count / len(all_sides)

    def _compare_margins(
        self,
        gen_margins: Optional[Dict],
        ref_margins: Optional[Dict],
    ) -> float:
        if gen_margins is None and ref_margins is None:
            return 1.0
        if gen_margins is None or ref_margins is None:
            return 0.0

        all_sides = set(list(gen_margins.keys()) + list(ref_margins.keys()))
        if not all_sides:
            return 1.0

        scores = []
        for side in all_sides:
            g = gen_margins.get(side, 0.0)
            r = ref_margins.get(side, 0.0)
            scores.append(numeric_match(g, r, tolerance=0.1))

        return self._mean(scores)

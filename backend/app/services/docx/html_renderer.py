import base64
import html as html_lib
from typing import List, Dict, Any, Optional

from .parser import (
    ContentElement,
    ElementType,
    ParagraphInfo,
    ParagraphFormat,
    RunInfo,
    TableCellInfo,
    TableFormatInfo,
)


class DocxHtmlRenderer:
    def render_elements(self, elements: List[ContentElement]) -> str:
        parts: list[str] = []
        for i, el in enumerate(elements):
            if el.element_type == ElementType.PARAGRAPH:
                parts.append(self._render_paragraph(el.paragraph, i))
            elif el.element_type == ElementType.BLANK_LINE:
                parts.append(
                    f'<p class="doc-blank" data-element-index="{i}" '
                    f'data-element-type="blank_line">&nbsp;</p>'
                )
            elif el.element_type == ElementType.TABLE:
                parts.append(self._render_table(el.table_cells, el.table_format, i))
            elif el.element_type == ElementType.IMAGE:
                parts.append(self._render_image_el(el, i))
        return "\n".join(parts)

    def render_template_for_marking(
        self, elements: List[ContentElement]
    ) -> Dict[str, Any]:
        html = self.render_elements(elements)
        element_summaries: list[dict[str, Any]] = []
        for i, el in enumerate(elements):
            summary: dict[str, Any] = {
                "index": i,
                "type": el.element_type.value,
            }
            if el.element_type == ElementType.PARAGRAPH and el.paragraph:
                summary["text_preview"] = (
                    el.paragraph.text[:60] if el.paragraph.text else ""
                )
            elif el.element_type == ElementType.TABLE and el.table_cells:
                summary["rows"] = len(el.table_cells)
                summary["cols"] = max(
                    (c.grid_span for row in el.table_cells for c in row),
                    default=0,
                )
                summary["row_summaries"] = []
                for r_idx, row in enumerate(el.table_cells):
                    row_text_parts: list[str] = []
                    for c in row:
                        if c.text and c.text.strip():
                            row_text_parts.append(c.text.strip()[:30])
                    summary["row_summaries"].append(
                        {
                            "row": r_idx,
                            "text_preview": " | ".join(row_text_parts)[:100],
                            "col_count": len(row),
                        }
                    )
            elif el.element_type == ElementType.BLANK_LINE:
                summary["text_preview"] = ""
            element_summaries.append(summary)

        auto_area = self._detect_main_content_area(elements)

        return {
            "html": html,
            "elements": element_summaries,
            "total_elements": len(elements),
            "auto_detected_area": auto_area,
        }

    def _detect_main_content_area(
        self, elements: List[ContentElement]
    ) -> Optional[Dict[str, Any]]:
        table_elements = [
            (i, el)
            for i, el in enumerate(elements)
            if el.element_type == ElementType.TABLE and el.table_cells
        ]
        if not table_elements:
            max_blank_run = 0
            best_idx = 0
            current_run = 0
            run_start = 0
            for i, el in enumerate(elements):
                if el.element_type == ElementType.BLANK_LINE:
                    if current_run == 0:
                        run_start = i
                    current_run += 1
                else:
                    if current_run > max_blank_run:
                        max_blank_run = current_run
                        best_idx = run_start
                    current_run = 0
            if max_blank_run >= 3:
                return {
                    "element_index": best_idx,
                    "type": "blank_line_group",
                    "reason": f"连续{max_blank_run}个空段落区域，疑似主内容区",
                }
            return None

        tbl_idx, tbl_el = table_elements[-1]
        rows = tbl_el.table_cells

        placeholder_keywords = [
            "放置主要教学内容",
            "放置教学内容",
            "在此处填写",
            "请在此处",
            "内容区域",
            "正文区域",
            "主内容",
        ]

        for r_idx, row in enumerate(rows):
            for c_idx, cell in enumerate(row):
                if not cell.text:
                    continue
                text_lower = cell.text.lower()
                for kw in placeholder_keywords:
                    if kw in text_lower or kw in cell.text:
                        return {
                            "element_index": tbl_idx,
                            "type": "table_cell",
                            "table_index": 0,
                            "row": r_idx,
                            "col": c_idx,
                            "reason": f"单元格包含占位提示文本「{cell.text.strip()[:30]}」",
                        }

        best_row = -1
        best_score = -1
        for r_idx, row in enumerate(rows):
            score = 0
            for cell in row:
                if cell.grid_span > 1:
                    score += cell.grid_span * 2
                if not cell.text or not cell.text.strip():
                    score += 1
                else:
                    score -= len(cell.text.strip()) * 0.1
            if score > best_score:
                best_score = score
                best_row = r_idx

        if best_row >= 0:
            return {
                "element_index": tbl_idx,
                "type": "table_cell",
                "table_index": 0,
                "row": best_row,
                "col": 0,
                "reason": f"表格中空段落最多的行（第{best_row + 1}行）",
            }

        return None

    def _render_paragraph(self, para: Optional[ParagraphInfo], idx: int) -> str:
        if para is None:
            return (
                f'<p class="doc-para" data-element-index="{idx}" '
                f'data-element-type="paragraph">&nbsp;</p>'
            )

        escaped_text = html_lib.escape(para.text) if para.text else "&nbsp;"
        css = self._build_paragraph_css(para.format)
        run_html = self._render_runs(para.runs)

        inner = run_html if run_html else escaped_text
        return (
            f'<p class="doc-para" data-element-index="{idx}" '
            f'data-element-type="paragraph" style="{css}">{inner}</p>'
        )

    def _render_runs(self, runs: List[RunInfo]) -> str:
        if not runs:
            return ""
        parts: list[str] = []
        for run in runs:
            if run.image:
                img_html = self._render_inline_image(run.image)
                if run.text:
                    parts.append(html_lib.escape(run.text))
                parts.append(img_html)
                continue

            escaped = html_lib.escape(run.text) if run.text else ""
            if not escaped:
                continue
            styles: list[str] = []
            if run.font_name:
                styles.append(f"font-family:'{run.font_name}'")
            if run.font_size:
                styles.append(f"font-size:{run.font_size:.1f}pt")
            if run.bold:
                styles.append("font-weight:bold")
            if run.italic:
                styles.append("font-style:italic")
            if run.underline:
                styles.append("text-decoration:underline")
            if run.color and run.color != "000000":
                styles.append(f"color:#{run.color}")

            tag = "span"
            if run.bold:
                tag = "strong"
            elif run.italic:
                tag = "em"

            if styles:
                parts.append(f'<{tag} style="{";".join(styles)}">{escaped}</{tag}>')
            else:
                parts.append(escaped)

        return "".join(parts)

    def _render_inline_image(self, image_info: Dict[str, Any]) -> str:
        data = image_info.get("data")
        ext = image_info.get("ext", "png")
        if not data:
            return "[图片]"
        b64 = base64.b64encode(data).decode("ascii")
        mime_map = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "bmp": "image/bmp",
        }
        mime = mime_map.get(ext, "image/png")
        style = "max-width:100%;height:auto;"
        w_emu = image_info.get("width_emu")
        if w_emu:
            w_pt = w_emu / 12700.0
            style = f"max-width:{w_pt:.0f}pt;height:auto;{style}"
        return f'<img src="data:{mime};base64,{b64}" style="{style}" alt="图片" />'

    def _render_image_el(self, el: ContentElement, idx: int) -> str:
        if not el.image_data:
            return (
                f'<div class="doc-image" data-element-index="{idx}" '
                f'data-element-type="image">[图片]</div>'
            )
        b64 = base64.b64encode(el.image_data).decode("ascii")
        mime_map = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "bmp": "image/bmp",
        }
        ext = el.image_ext or "png"
        mime = mime_map.get(ext, "image/png")
        style = "max-width:100%;height:auto;"
        if el.image_width:
            w_pt = el.image_width / 12700.0
            style = f"max-width:{w_pt:.0f}pt;height:auto;"
        return (
            f'<div class="doc-image" data-element-index="{idx}" '
            f'data-element-type="image">'
            f'<img src="data:{mime};base64,{b64}" style="{style}" alt="图片" />'
            f"</div>"
        )

    def _render_table(
        self,
        cells: Optional[List[List[TableCellInfo]]],
        fmt: Optional[TableFormatInfo],
        idx: int,
    ) -> str:
        if not cells:
            return ""

        table_style = "border-collapse:collapse;width:100%;"
        if fmt and fmt.width:
            table_style += f"max-width:{fmt.width:.1f}cm;"

        header = (
            f'<table class="doc-table" data-element-index="{idx}" '
            f'data-element-type="table" style="{table_style}">'
        )
        rows_html: list[str] = []

        for r_idx, row in enumerate(cells):
            row_html_parts: list[str] = []
            for c_idx, cell in enumerate(row):
                attrs = (
                    f'data-row="{r_idx}" data-col="{c_idx}" '
                    f'data-element-index="{idx}" data-element-type="table_cell"'
                )
                if cell.grid_span > 1:
                    attrs += f' colspan="{cell.grid_span}"'
                if cell.v_merge == "restart":
                    attrs += ' rowspan="2"'
                elif cell.v_merge == "continue":
                    continue

                cell_css = self._build_cell_css(cell)
                inner = html_lib.escape(cell.text) if cell.text else "&nbsp;"
                if cell.runs:
                    run_html = self._render_runs(cell.runs)
                    if run_html:
                        inner = run_html

                row_html_parts.append(f'<td {attrs} style="{cell_css}">{inner}</td>')

            if row_html_parts:
                rows_html.append(f"<tr>{''.join(row_html_parts)}</tr>")

        return f"{header}{''.join(rows_html)}</table>"

    def _build_paragraph_css(self, fmt: ParagraphFormat) -> str:
        parts: list[str] = []
        if fmt.alignment:
            parts.append(f"text-align:{fmt.alignment}")
        if fmt.line_spacing:
            parts.append(f"line-height:{fmt.line_spacing}")
        if fmt.first_line_indent:
            cm = fmt.first_line_indent
            parts.append(f"text-indent:{cm:.2f}cm")
        if fmt.space_before:
            parts.append(f"margin-top:{fmt.space_before:.1f}pt")
        if fmt.space_after:
            parts.append(f"margin-bottom:{fmt.space_after:.1f}pt")
        if fmt.left_indent:
            parts.append(f"margin-left:{fmt.left_indent:.2f}cm")
        return ";".join(parts)

    def _build_cell_css(self, cell: TableCellInfo) -> str:
        parts: list[str] = ["border:1px solid #d0d0d0", "padding:4px 6px"]
        if cell.cell_format:
            cf = cell.cell_format
            if cf.shading_fill:
                parts.append(f"background-color:#{cf.shading_fill}")
            if cf.vertical_alignment:
                va_map = {"top": "top", "center": "middle", "bottom": "bottom"}
                parts.append(
                    f"vertical-align:{va_map.get(cf.vertical_alignment, 'top')}"
                )
            if cf.margins:
                for side, val in cf.margins.items():
                    side_map = {
                        "top": "padding-top",
                        "bottom": "padding-bottom",
                        "left": "padding-left",
                        "right": "padding-right",
                    }
                    prop = side_map.get(side)
                    if prop:
                        parts.append(f"{prop}:{val:.2f}cm")
        return ";".join(parts)


docx_html_renderer = DocxHtmlRenderer()

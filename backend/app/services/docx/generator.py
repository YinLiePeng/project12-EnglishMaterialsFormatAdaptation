from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from pathlib import Path
from typing import List, Dict, Any, Optional
from io import BytesIO

from .parser import ParagraphInfo, FontInfo, ParagraphFormat, RunInfo
from .parser import ContentElement, ElementType, TableCellInfo


class DocxGenerator:
    """DOCX文档生成器"""

    def __init__(self, template_path: Optional[str] = None):
        if template_path and Path(template_path).exists():
            self.doc = Document(template_path)
        else:
            self.doc = Document()

    # ================================================================
    # 核心方法：从 ContentElement 列表生成文档
    # ================================================================

    def generate_from_elements(
        self,
        elements: List[ContentElement],
        style_mapping: Dict[str, Dict[str, Any]],
        style_keys: Optional[Dict[int, str]] = None,
    ):
        """按统一内容元素列表生成新文档

        Args:
            elements: ContentElement 列表（保持原始顺序）
            style_mapping: 样式映射 {style_key: {font: {}, format: {}}}
            style_keys: 可选的段落索引→样式key映射，由结构识别结果生成
        """
        para_counter = 0
        for element in elements:
            if element.element_type == ElementType.PARAGRAPH:
                if element.paragraph is None:
                    continue
                style_key = (
                    style_keys.get(para_counter, "body") if style_keys else "body"
                )
                style_def = style_mapping.get(style_key, style_mapping.get("body", {}))
                self.add_paragraph_with_runs(
                    element.paragraph.runs, style_def, extract_images=True
                )
                para_counter += 1

            elif element.element_type == ElementType.BLANK_LINE:
                self.add_blank_line()

            elif element.element_type == ElementType.TABLE:
                table_style = style_mapping.get("table", style_mapping.get("body", {}))
                self.add_table_from_cells(element.table_cells, table_style)

            elif element.element_type == ElementType.IMAGE:
                self.add_image(element.image_data, element.image_ext)

    def fill_template_from_elements(
        self,
        elements: List[ContentElement],
        marker: str,
        style_mapping: Dict[str, Dict[str, Any]],
        style_keys: Optional[Dict[int, str]] = None,
    ):
        """在模板标记位处填充内容，保持原始元素顺序

        Args:
            elements: ContentElement 列表
            marker: 标记文本（如 {{CONTENT}}）
            style_mapping: 样式映射
            style_keys: 段落索引→样式key映射
        """
        marker_para = None
        for para in self.doc.paragraphs:
            if marker in para.text:
                marker_para = para
                break

        if marker_para is None:
            for alt in ["{{content}}", "{内容}", "【内容】"]:
                for para in self.doc.paragraphs:
                    if alt in para.text:
                        marker_para = para
                        break
                if marker_para:
                    break

        if marker_para is None:
            raise ValueError(f"未找到标记位: {marker}")

        marker_para.clear()
        ref_element = marker_para._element

        para_counter = 0
        first = True
        for element in elements:
            if element.element_type == ElementType.PARAGRAPH:
                if element.paragraph is None:
                    continue
                style_key = (
                    style_keys.get(para_counter, "body") if style_keys else "body"
                )
                style_def = style_mapping.get(style_key, style_mapping.get("body", {}))

                if first:
                    para = marker_para
                    first = False
                else:
                    para = self.doc.add_paragraph()
                    ref_element.addnext(para._element)
                    ref_element = para._element

                self._apply_paragraph_format(para, style_def.get("format", {}))
                self._add_runs_to_paragraph(
                    para, element.paragraph.runs, style_def, extract_images=True
                )
                para_counter += 1

            elif element.element_type == ElementType.BLANK_LINE:
                if first:
                    para = marker_para
                    first = False
                else:
                    para = self.doc.add_paragraph()
                    ref_element.addnext(para._element)
                    ref_element = para._element

            elif element.element_type == ElementType.TABLE:
                table_style = style_mapping.get("table", style_mapping.get("body", {}))
                table = self._create_table_at(element.table_cells, ref_element)
                if table is not None:
                    self._style_table(table, table_style)
                    ref_element = table._tbl
                para_counter += 1

            elif element.element_type == ElementType.IMAGE:
                img_para = self._create_image_paragraph_at(
                    element.image_data, element.image_ext, ref_element
                )
                if img_para is not None:
                    ref_element = img_para._element

    # ================================================================
    # 元素添加方法
    # ================================================================

    def add_paragraph_with_runs(
        self,
        runs: List[RunInfo],
        style_def: Dict[str, Any],
        extract_images: bool = False,
    ):
        """添加段落，保留每个 run 的独立格式（下划线/加粗等）

        Args:
            runs: RunInfo 列表
            style_def: 样式定义
            extract_images: 是否提取 run 中的图片为独立图片元素（简化方案）
        """
        para = self.doc.add_paragraph()
        self._apply_paragraph_format(para, style_def.get("format", {}))
        self._add_runs_to_paragraph(
            para, runs, style_def, extract_images=extract_images
        )
        return para

    def add_blank_line(self):
        """添加空段落"""
        para = self.doc.add_paragraph()
        return para

    def add_table_from_cells(
        self,
        table_cells: Optional[List[List[TableCellInfo]]],
        style_def: Dict[str, Any],
    ):
        """添加表格，应用预设样式到单元格"""
        if not table_cells:
            return
        rows = len(table_cells)
        cols = max((len(r) for r in table_cells), default=0)
        if rows == 0 or cols == 0:
            return

        table = self.doc.add_table(rows=rows, cols=cols)
        table.style = "Table Grid"
        self._fill_table(table, table_cells, style_def)
        return table

    def add_image(self, image_data: Optional[bytes], image_ext: Optional[str]):
        """添加图片"""
        if not image_data:
            return
        stream = BytesIO(image_data)
        try:
            available = self._get_available_width()
            self.doc.add_picture(stream, width=available)
        except Exception:
            self.doc.add_paragraph("[图片]")

    # ================================================================
    # Run 级别格式处理
    # ================================================================

    def _add_runs_to_paragraph(
        self,
        para,
        runs: List[RunInfo],
        style_def: Dict[str, Any],
        extract_images: bool = False,
    ):
        """向段落添加 run 列表（保留 run 级别的图片位置）

        策略：预设样式提供基础字体/字号；原始 run 保留下划线等差异化格式；
        加粗/斜体取预设与原始的并集（标题样式强制备留加粗，正文保留原始加粗词）。

        Args:
            para: 目标段落
            runs: RunInfo 列表
            style_def: 样式定义
            extract_images: 如果为 True，将 run 中的图片提取为独立图片元素（添加在段落后）
        """
        font_def = style_def.get("font", {})
        preset_bold = font_def.get("bold", False)
        preset_italic = font_def.get("italic", False)

        extracted_images = []

        for run_info in runs:
            # 如果 run 包含图片且 extract_images=True，记录图片信息
            if extract_images and run_info.image:
                extracted_images.append(run_info.image)

            # 插入文本 run（如果有文本）
            if run_info.text:
                run = para.add_run(run_info.text)
                if "name" in font_def:
                    run.font.name = font_def["name"]
                if "size" in font_def:
                    run.font.size = Pt(font_def["size"])
                run.font.bold = preset_bold or run_info.bold
                run.font.italic = preset_italic or run_info.italic
                run.font.underline = run_info.underline
                self._apply_color(run, run_info.color)

        # 如果有提取的图片，在段落后添加为独立的图片元素
        if extracted_images:
            for img_data in extracted_images:
                self.add_image(img_data.get("data"), img_data.get("ext"))

    def _add_inline_image_to_paragraph(self, para, image_data: Dict[str, Any]):
        """向段落添加内联图片"""
        try:
            from io import BytesIO

            stream = BytesIO(image_data["data"])
            available = self._get_available_width()
            # 内联图片使用较小宽度（避免过大）
            para.add_picture(stream, width=min(available, Inches(4)))
        except Exception:
            # 如果图片添加失败，添加占位符
            para.add_run("[图片]")

    def _apply_color(self, run, color_hex: str):
        if color_hex and color_hex != "000000" and len(color_hex) == 6:
            try:
                r = int(color_hex[0:2], 16)
                g = int(color_hex[2:4], 16)
                b = int(color_hex[4:6], 16)
                run.font.color.rgb = RGBColor(r, g, b)
            except (ValueError, IndexError):
                pass

    # ================================================================
    # 表格辅助方法
    # ================================================================

    def _fill_table(
        self,
        table,
        table_cells: List[List[TableCellInfo]],
        style_def: Dict[str, Any],
    ):
        font_def = style_def.get("font", {})
        for i, row_cells in enumerate(table_cells):
            for j, cell_info in enumerate(row_cells):
                if j >= len(table.columns):
                    break
                cell = table.cell(i, j)

                # 处理文本 runs
                if cell_info.runs:
                    first_para = True
                    for ci, run_info in enumerate(cell_info.runs):
                        if first_para:
                            para = cell.paragraphs[0]
                            para.clear()
                            first_para = False
                        elif ci > 0 and run_info.text and run_info.text.strip():
                            para = cell.add_paragraph()
                        else:
                            continue
                        run = para.add_run(run_info.text)
                        if "name" in font_def:
                            run.font.name = font_def["name"]
                        if "size" in font_def:
                            run.font.size = Pt(font_def["size"])
                        run.font.bold = run_info.bold
                        run.font.italic = run_info.italic
                        run.font.underline = run_info.underline
                else:
                    cell.text = cell_info.text
                    for para in cell.paragraphs:
                        for run in para.runs:
                            if "name" in font_def:
                                run.font.name = font_def["name"]
                            if "size" in font_def:
                                run.font.size = Pt(font_def["size"])

                # 处理单元格内的图片
                for img_data in cell_info.images:
                    self._add_image_to_cell(cell, img_data)

    def _add_image_to_cell(self, cell, img_data: Dict[str, Any]):
        """向表格单元格添加图片"""
        try:
            from io import BytesIO

            image_bytes = img_data.get("data")
            if not image_bytes:
                return

            stream = BytesIO(image_bytes)
            # 添加图片到单元格的第一个段落
            if cell.paragraphs:
                para = cell.paragraphs[0]
            else:
                para = cell.add_paragraph()

            # 计算合适的宽度（单元格宽度的一定比例）
            cell_width = cell.width
            if cell_width:
                from docx.shared import Inches

                img_width = min(cell_width * 0.8, Inches(6))
                para.add_picture(stream, width=img_width)
            else:
                para.add_picture(stream)
        except Exception:
            # 如果图片添加失败，添加占位文本
            if cell.paragraphs:
                para = cell.paragraphs[0]
            else:
                para = cell.add_paragraph()
            para.add_run("[图片]")

    def _style_table(self, table, style_def: Dict[str, Any]):
        font_def = style_def.get("font", {})
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        if "name" in font_def:
                            run.font.name = font_def["name"]
                        if "size" in font_def:
                            run.font.size = Pt(font_def["size"])

    def _create_table_at(self, table_cells, ref_element):
        if not table_cells:
            return None
        rows = len(table_cells)
        cols = max((len(r) for r in table_cells), default=0)
        if rows == 0 or cols == 0:
            return None
        table = self.doc.add_table(rows=rows, cols=cols)
        table.style = "Table Grid"
        ref_element.addnext(table._tbl)
        return table

    # ================================================================
    # 图片辅助方法
    # ================================================================

    def _create_image_paragraph_at(self, image_data, image_ext, ref_element):
        if not image_data:
            return None
        stream = BytesIO(image_data)
        try:
            available = self._get_available_width()
            self.doc.add_picture(stream, width=available)
            body = self.doc.element.body
            last = body[-1]
            ref_element.addnext(last)
            from docx.text.paragraph import Paragraph

            return Paragraph(last, body)
        except Exception:
            para = self.doc.add_paragraph("[图片]")
            ref_element.addnext(para._element)
            return para

    def _get_available_width(self):
        if self.doc.sections:
            section = self.doc.sections[0]
            return section.page_width - section.left_margin - section.right_margin
        return Cm(15)

    # ================================================================
    # 段落/字体格式方法（向后兼容）
    # ================================================================

    def apply_style(self, para_info: ParagraphInfo, target_style: Dict[str, Any]):
        if not self.doc.paragraphs:
            return
        para = self.doc.paragraphs[-1]
        self._apply_paragraph_format(para, target_style.get("format", {}))
        if para.runs:
            for run in para.runs:
                self._apply_font_format(run, target_style.get("font", {}))

    def add_paragraph_with_style(
        self,
        text: str,
        style_def: Dict[str, Any],
        paragraph_format: Optional[Dict[str, Any]] = None,
    ):
        para = self.doc.add_paragraph(text)
        fmt = paragraph_format or style_def.get("format", {})
        self._apply_paragraph_format(para, fmt)
        if para.runs:
            font_def = style_def.get("font", {})
            for run in para.runs:
                self._apply_font_format(run, font_def)
        return para

    def add_content_from_list(
        self,
        content_list: List[ParagraphInfo],
        style_mapping: Dict[str, Dict[str, Any]],
    ):
        for content in content_list:
            style_key = self._determine_style_key(content)
            style_def = style_mapping.get(style_key, style_mapping.get("body", {}))
            self.add_paragraph_with_style(content.text, style_def)

    def fill_template(
        self,
        marker: str,
        content_list: List[ParagraphInfo],
        style_mapping: Dict[str, Dict[str, Any]],
    ):
        marker_para = None
        marker_index = -1
        for i, para in enumerate(self.doc.paragraphs):
            if marker in para.text:
                marker_para = para
                marker_index = i
                break
        if marker_para is None:
            raise ValueError(f"未找到标记位: {marker}")
        marker_para.clear()
        for i, content in enumerate(content_list):
            if i == 0:
                para = marker_para
                para.text = content.text
            else:
                para = self.doc.add_paragraph(content.text)
            style_key = self._determine_style_key(content)
            style_def = style_mapping.get(style_key, style_mapping.get("body", {}))
            self._apply_paragraph_format(para, style_def.get("format", {}))
            if para.runs:
                for run in para.runs:
                    self._apply_font_format(run, style_def.get("font", {}))

    def save(self, output_path: str):
        self.doc.save(output_path)

    def _apply_paragraph_format(self, para, fmt: Dict[str, Any]):
        pf = para.paragraph_format
        alignment_map = {
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
            "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        }
        if "alignment" in fmt:
            para.alignment = alignment_map.get(
                fmt["alignment"], WD_ALIGN_PARAGRAPH.LEFT
            )
        if "line_spacing" in fmt:
            pf.line_spacing = fmt["line_spacing"]
        if "space_before" in fmt:
            pf.space_before = Pt(fmt["space_before"])
        if "space_after" in fmt:
            pf.space_after = Pt(fmt["space_after"])
        if "first_line_indent" in fmt:
            pf.first_line_indent = Cm(fmt["first_line_indent"])
        if "left_indent" in fmt:
            pf.left_indent = Cm(fmt["left_indent"])
        if "right_indent" in fmt:
            pf.right_indent = Cm(fmt["right_indent"])

    def _apply_font_format(self, run, font_def: Dict[str, Any]):
        font = run.font
        if "name" in font_def:
            font.name = font_def["name"]
        if "size" in font_def:
            font.size = Pt(font_def["size"])
        if "bold" in font_def:
            font.bold = font_def["bold"]
        if "italic" in font_def:
            font.italic = font_def["italic"]
        if "underline" in font_def:
            font.underline = font_def["underline"]
        if "color" in font_def:
            color_hex = font_def["color"]
            if len(color_hex) == 6:
                try:
                    r = int(color_hex[0:2], 16)
                    g = int(color_hex[2:4], 16)
                    b = int(color_hex[4:6], 16)
                    font.color.rgb = RGBColor(r, g, b)
                except (ValueError, IndexError):
                    pass

    def _determine_style_key(self, content: ParagraphInfo) -> str:
        if content.level == 1:
            return "heading1"
        elif content.level == 2:
            return "heading2"
        elif content.level == 3:
            return "heading3"
        import re

        if re.match(r"^\d+[\.\)、]", content.text.strip()):
            return "question_number"
        if re.match(r"^[A-D][\.\)、]", content.text.strip()):
            return "option"
        return "body"

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class RunInfo:
    """单个 run 的文本+格式，保留段内差异化格式（如下划线）"""

    text: str
    font_name: str = "宋体"
    font_size: float = 12.0
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: str = "000000"
    image: Optional[Dict[str, Any]] = None  # run 级别的图片（如有）


@dataclass
class FontInfo:
    """字体信息（向后兼容，取自第一个 run）"""

    name: str = "宋体"
    size: float = 12.0
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: str = "000000"


@dataclass
class ParagraphFormat:
    """段落格式"""

    alignment: str = "left"
    line_spacing: float = 1.5
    space_before: float = 0.0
    space_after: float = 0.0
    first_line_indent: float = 0.0
    left_indent: float = 0.0
    right_indent: float = 0.0


@dataclass
class ParagraphInfo:
    """段落信息"""

    index: int
    text: str
    style_name: str
    font: FontInfo
    format: ParagraphFormat
    level: int = 0
    runs: List[RunInfo] = field(default_factory=list)


@dataclass
class TableCellInfo:
    """表格单元格信息"""

    text: str
    runs: List[RunInfo] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)


class ElementType(Enum):
    """文档元素类型"""

    PARAGRAPH = "paragraph"
    TABLE = "table"
    IMAGE = "image"
    BLANK_LINE = "blank_line"


@dataclass
class ContentElement:
    """文档中的统一内容元素，保持原始交错顺序"""

    element_type: ElementType
    original_index: int

    paragraph: Optional[ParagraphInfo] = None
    table_cells: Optional[List[List[TableCellInfo]]] = None
    image_data: Optional[bytes] = None
    image_ext: Optional[str] = None


class DocxParser:
    """DOCX文档解析器"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.doc = Document(file_path)

    # ================================================================
    # 核心方法：按原文档顺序提取全部内容
    # ================================================================

    def extract_content(self) -> List[ContentElement]:
        """提取文档所有内容（段落+表格+图片+空行），保持原始顺序"""
        self._unwrap_sdt_elements()

        elements: List[ContentElement] = []
        body = self.doc.element.body
        para_idx = 0
        table_idx = 0

        for child_pos, child in enumerate(body):
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

            if tag == "p":
                if para_idx >= len(self.doc.paragraphs):
                    continue
                para = self.doc.paragraphs[para_idx]
                images = self._extract_images_from_element(child)
                text = para.text

                if not text.strip() and not images:
                    elements.append(
                        ContentElement(
                            element_type=ElementType.BLANK_LINE,
                            original_index=child_pos,
                        )
                    )
                elif not text.strip() and images:
                    # 纯图片段落：添加所有图片为独立元素
                    for img in images:
                        elements.append(
                            ContentElement(
                                element_type=ElementType.IMAGE,
                                original_index=child_pos,
                                image_data=img["data"],
                                image_ext=img["ext"],
                            )
                        )
                else:
                    # 文本段落：提取 runs（可能包含 run 级别的图片）
                    runs = self._extract_all_runs(para)
                    fmt = self._extract_paragraph_format(para)
                    level = self._get_heading_level(para)
                    first_font = self._font_from_runs(runs)

                    elements.append(
                        ContentElement(
                            element_type=ElementType.PARAGRAPH,
                            original_index=child_pos,
                            paragraph=ParagraphInfo(
                                index=child_pos,
                                text=text,
                                style_name=(
                                    para.style.name if para.style else "Normal"
                                ),
                                font=first_font,
                                format=fmt,
                                level=level,
                                runs=runs,
                            ),
                        )
                    )

                    # 只添加不属于任何 run 的段落级图片
                    # （通过检查 runs 中是否有图片来判断）
                    runs_with_images = sum(1 for r in runs if r.image)
                    if images and len(images) > runs_with_images:
                        # 有额外的段落级图片，添加它们
                        for i in range(runs_with_images, len(images)):
                            elements.append(
                                ContentElement(
                                    element_type=ElementType.IMAGE,
                                    original_index=child_pos,
                                    image_data=images[i]["data"],
                                    image_ext=images[i]["ext"],
                                )
                            )

                para_idx += 1

            elif tag == "tbl":
                if table_idx >= len(self.doc.tables):
                    continue
                table = self.doc.tables[table_idx]
                cells = self._extract_table_cells(table)

                elements.append(
                    ContentElement(
                        element_type=ElementType.TABLE,
                        original_index=child_pos,
                        table_cells=cells,
                    )
                )
                table_idx += 1

        return elements

    # ================================================================
    # SDT 预处理
    # ================================================================

    def _unwrap_sdt_elements(self):
        """将 w:sdt 结构化标签展开为普通段落/表格，确保正确遍历"""
        body = self.doc.element.body
        changed = True
        while changed:
            changed = False
            sdt_elements = body.findall(qn("w:sdt"))
            for sdt in sdt_elements:
                sdt_content = sdt.find(qn("w:sdtContent"))
                if sdt_content is not None:
                    for child in list(sdt_content):
                        sdt.addprevious(child)
                sdt.getparent().remove(sdt)
                changed = True

    # ================================================================
    # 图片提取
    # ================================================================

    def _extract_images_from_element(self, element) -> List[Dict[str, Any]]:
        """从 XML 元素中提取嵌入图片"""
        images: List[Dict[str, Any]] = []

        for drawing in element.findall(".//" + qn("w:drawing")):
            blip = drawing.find(".//" + qn("a:blip"))
            if blip is None:
                continue
            rId = blip.get(qn("r:embed"))
            if rId is None:
                continue
            try:
                image_part = self.doc.part.related_parts[rId]
                images.append(
                    {
                        "data": image_part.blob,
                        "ext": self._get_image_ext(image_part.content_type),
                    }
                )
            except (KeyError, AttributeError):
                pass

        VML_NS = "urn:schemas-microsoft-com:vml"
        OFFICE_NS = "urn:schemas-microsoft-com:office:office"

        for pict in element.findall(".//{%s}imagedata" % VML_NS):
            rId = pict.get(qn("r:id"))
            if rId is None:
                continue
            try:
                image_part = self.doc.part.related_parts[rId]
                images.append(
                    {
                        "data": image_part.blob,
                        "ext": self._get_image_ext(image_part.content_type),
                    }
                )
            except (KeyError, AttributeError):
                pass

        return images

    def _get_image_ext(self, content_type: str) -> str:
        ct_map = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/gif": "gif",
            "image/tiff": "tiff",
            "image/bmp": "bmp",
            "image/x-emf": "emf",
            "image/x-wmf": "wmf",
            "image/emf": "emf",
            "image/wmf": "wmf",
        }
        return ct_map.get(content_type, "png")

    # ================================================================
    # Run 提取（保留段内差异化格式）
    # ================================================================

    def _extract_all_runs(self, para) -> List[RunInfo]:
        """提取段落中所有 run 的独立格式（包括 run 级别的图片）"""
        runs: List[RunInfo] = []
        for run in para.runs:
            font = run.font
            color = "000000"
            if font.color and font.color.rgb:
                color = str(font.color.rgb)

            # 检查 run 中是否包含图片
            run_image = None
            if hasattr(run, "_element"):
                # 检查 w:drawing 元素
                drawings = run._element.findall(
                    ".//{%s}drawing"
                    % "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                )
                if drawings:
                    # 提取图片信息
                    blip = drawings[0].find(
                        ".//{%s}blip"
                        % "http://schemas.openxmlformats.org/drawingml/2006/main"
                    )
                    if blip is not None:
                        rId = blip.get(
                            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
                        )
                        if rId:
                            try:
                                image_part = self.doc.part.related_parts[rId]
                                run_image = {
                                    "data": image_part.blob,
                                    "ext": self._get_image_ext(image_part.content_type),
                                }
                            except (KeyError, AttributeError):
                                pass

            runs.append(
                RunInfo(
                    text=run.text,
                    font_name=font.name or "宋体",
                    font_size=font.size.pt if font.size else 12.0,
                    bold=font.bold or False,
                    italic=font.italic or False,
                    underline=font.underline or False,
                    color=color,
                    image=run_image,
                )
            )
        if not runs and para.text:
            runs.append(RunInfo(text=para.text))
        return runs

    def _font_from_runs(self, runs: List[RunInfo]) -> FontInfo:
        """从第一个 run 生成 FontInfo（向后兼容）"""
        if runs:
            r = runs[0]
            return FontInfo(
                name=r.font_name,
                size=r.font_size,
                bold=r.bold,
                italic=r.italic,
                underline=r.underline,
                color=r.color,
            )
        return FontInfo()

    # ================================================================
    # 表格提取（保留单元格 run 信息）
    # ================================================================

    def _extract_table_cells(self, table) -> List[List[TableCellInfo]]:
        """提取表格全部单元格文本+run 信息+图片"""
        rows: List[List[TableCellInfo]] = []
        for row in table.rows:
            cells: List[TableCellInfo] = []
            for cell in row.cells:
                cell_runs: List[RunInfo] = []
                cell_images: List[Dict[str, Any]] = []

                for para in cell.paragraphs:
                    # 提取 run 信息
                    for run in para.runs:
                        font = run.font
                        color = "000000"
                        if font.color and font.color.rgb:
                            color = str(font.color.rgb)
                        cell_runs.append(
                            RunInfo(
                                text=run.text,
                                font_name=font.name or "宋体",
                                font_size=font.size.pt if font.size else 12.0,
                                bold=font.bold or False,
                                italic=font.italic or False,
                                underline=font.underline or False,
                                color=color,
                            )
                        )

                    # 提取图片信息
                    images = self._extract_images_from_element(para._element)
                    cell_images.extend(images)

                cells.append(
                    TableCellInfo(text=cell.text, runs=cell_runs, images=cell_images)
                )
            rows.append(cells)
        return rows

    # ================================================================
    # 向后兼容方法
    # ================================================================

    def extract_paragraphs(self) -> List[ParagraphInfo]:
        """提取所有段落信息（向后兼容，现也填充 runs 字段）"""
        paragraphs = []
        for i, para in enumerate(self.doc.paragraphs):
            if not para.text.strip():
                continue
            runs = self._extract_all_runs(para)
            font = self._font_from_runs(runs)
            fmt = self._extract_paragraph_format(para)
            level = self._get_heading_level(para)
            paragraphs.append(
                ParagraphInfo(
                    index=i,
                    text=para.text,
                    style_name=para.style.name if para.style else "Normal",
                    font=font,
                    format=fmt,
                    level=level,
                    runs=runs,
                )
            )
        return paragraphs

    def extract_tables(self) -> List[List[List[str]]]:
        """提取所有表格纯文本内容（向后兼容）"""
        tables = []
        for table in self.doc.tables:
            table_data = []
            for row in table.rows:
                row_data = [cell.text for cell in row.cells]
                table_data.append(row_data)
            tables.append(table_data)
        return tables

    def extract_style_system(self) -> Dict[str, Dict[str, Any]]:
        """提取文档的完整样式体系"""
        styles = {}
        for style in self.doc.styles:
            if style.type == 1:
                style_info = {
                    "name": style.name,
                    "type": "paragraph",
                    "font": self._extract_font_from_style(style),
                    "format": self._extract_format_from_style(style),
                    "base_style": (style.base_style.name if style.base_style else None),
                }
                styles[style.name] = style_info
        return styles

    # ================================================================
    # 内部辅助方法
    # ================================================================

    def _extract_paragraph_format(self, para) -> ParagraphFormat:
        pf = para.paragraph_format
        alignment_map = {
            WD_ALIGN_PARAGRAPH.LEFT: "left",
            WD_ALIGN_PARAGRAPH.CENTER: "center",
            WD_ALIGN_PARAGRAPH.RIGHT: "right",
            WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
            None: "left",
        }
        return ParagraphFormat(
            alignment=alignment_map.get(para.alignment, "left"),
            line_spacing=pf.line_spacing if pf.line_spacing else 1.5,
            space_before=pf.space_before.pt if pf.space_before else 0.0,
            space_after=pf.space_after.pt if pf.space_after else 0.0,
            first_line_indent=(
                pf.first_line_indent.cm if pf.first_line_indent else 0.0
            ),
            left_indent=pf.left_indent.cm if pf.left_indent else 0.0,
            right_indent=pf.right_indent.cm if pf.right_indent else 0.0,
        )

    def _get_heading_level(self, para) -> int:
        style_name = para.style.name if para.style else ""
        if "Heading 1" in style_name or "标题 1" in style_name:
            return 1
        elif "Heading 2" in style_name or "标题 2" in style_name:
            return 2
        elif "Heading 3" in style_name or "标题 3" in style_name:
            return 3
        elif "Title" in style_name or "标题" in style_name:
            return 1
        return 0

    def _extract_font_from_style(self, style) -> Dict[str, Any]:
        font = style.font
        return {
            "name": font.name or "宋体",
            "size": font.size.pt if font.size else 12.0,
            "bold": font.bold or False,
            "italic": font.italic or False,
            "color": (
                str(font.color.rgb) if font.color and font.color.rgb else "000000"
            ),
        }

    def _extract_format_from_style(self, style) -> Dict[str, Any]:
        pf = style.paragraph_format
        alignment_map = {
            WD_ALIGN_PARAGRAPH.LEFT: "left",
            WD_ALIGN_PARAGRAPH.CENTER: "center",
            WD_ALIGN_PARAGRAPH.RIGHT: "right",
            WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
            None: "left",
        }
        return {
            "alignment": alignment_map.get(style.alignment, "left"),
            "line_spacing": pf.line_spacing if pf.line_spacing else 1.5,
            "space_before": pf.space_before.pt if pf.space_before else 0.0,
            "space_after": pf.space_after.pt if pf.space_after else 0.0,
            "first_line_indent": (
                pf.first_line_indent.cm if pf.first_line_indent else 0.0
            ),
            "left_indent": pf.left_indent.cm if pf.left_indent else 0.0,
        }

    def get_text_content(self) -> str:
        return "\n".join(
            [para.text for para in self.doc.paragraphs if para.text.strip()]
        )

    def get_page_count(self) -> int:
        line_count = len([p for p in self.doc.paragraphs if p.text.strip()])
        return max(1, line_count // 30)

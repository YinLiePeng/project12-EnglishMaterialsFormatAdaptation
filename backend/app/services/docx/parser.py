from docx import Document
from docx.shared import Pt, Cm, RGBColor, Twips, Emu, Length
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
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
    """段落格式（含行距规则，完整保留 python-docx 所有间距属性）"""

    alignment: Optional[str] = None
    line_spacing: Optional[float] = None
    line_spacing_rule: Optional[str] = None
    space_before: Optional[float] = None
    space_after: Optional[float] = None
    first_line_indent: Optional[float] = None
    left_indent: Optional[float] = None
    right_indent: Optional[float] = None
    keep_with_next: Optional[bool] = None
    keep_together: Optional[bool] = None
    page_break_before: Optional[bool] = None
    widow_control: Optional[bool] = None


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
class CellFormatInfo:
    """单元格格式信息"""

    vertical_alignment: str = "top"
    shading_fill: Optional[str] = None
    shading_pattern: str = "clear"
    borders: Optional[Dict[str, Dict[str, Any]]] = None
    margins: Optional[Dict[str, float]] = None


@dataclass
class TableCellInfo:
    """表格单元格信息"""

    text: str
    runs: List[RunInfo] = field(default_factory=list)
    paragraph_runs: List[List[RunInfo]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    grid_span: int = 1
    v_merge: Optional[str] = None
    cell_format: Optional[CellFormatInfo] = None


@dataclass
class TableFormatInfo:
    """表格级格式信息"""

    column_widths: List[float] = field(default_factory=list)
    row_heights: List[float] = field(default_factory=list)
    alignment: str = "left"
    width: Optional[float] = None


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
    table_format: Optional[TableFormatInfo] = None
    image_data: Optional[bytes] = None
    image_ext: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None


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
                    fmt = self._extract_paragraph_format(para)
                    elements.append(
                        ContentElement(
                            element_type=ElementType.BLANK_LINE,
                            original_index=child_pos,
                            paragraph=ParagraphInfo(
                                index=child_pos,
                                text="",
                                style_name=(
                                    para.style.name if para.style else "Normal"
                                ),
                                font=FontInfo(),
                                format=fmt,
                            ),
                        )
                    )
                elif not text.strip() and images:
                    for img in images:
                        elements.append(
                            ContentElement(
                                element_type=ElementType.IMAGE,
                                original_index=child_pos,
                                image_data=img["data"],
                                image_ext=img["ext"],
                                image_width=img.get("width_emu"),
                                image_height=img.get("height_emu"),
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

                    runs_with_images = sum(1 for r in runs if r.image)
                    if images and len(images) > runs_with_images:
                        for i in range(runs_with_images, len(images)):
                            elements.append(
                                ContentElement(
                                    element_type=ElementType.IMAGE,
                                    original_index=child_pos,
                                    image_data=images[i]["data"],
                                    image_ext=images[i]["ext"],
                                    image_width=images[i].get("width_emu"),
                                    image_height=images[i].get("height_emu"),
                                )
                            )

                para_idx += 1

            elif tag == "tbl":
                if table_idx >= len(self.doc.tables):
                    continue
                table = self.doc.tables[table_idx]
                cells = self._extract_table_cells(table)
                table_format = self._extract_table_format(table)

                elements.append(
                    ContentElement(
                        element_type=ElementType.TABLE,
                        original_index=child_pos,
                        table_cells=cells,
                        table_format=table_format,
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

    def _extract_image_extent(self, drawing) -> Optional[Dict[str, int]]:
        """从 drawing 元素中提取图片尺寸（EMU）"""
        WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
        for tag in [qn("wp:inline"), qn("wp:anchor")]:
            container = drawing.find(".//" + tag)
            if container is None:
                container = drawing.find(".//{%s}%s" % (WP_NS, tag.split("}")[-1]))
            if container is not None:
                extent = container.find(qn("wp:extent"))
                if extent is None:
                    extent = container.find(".//{%s}extent" % WP_NS)
                if extent is not None:
                    cx = extent.get("cx")
                    cy = extent.get("cy")
                    if cx and cy:
                        return {"width_emu": int(cx), "height_emu": int(cy)}
        extent = drawing.find(".//" + qn("wp:extent"))
        if extent is not None:
            cx = extent.get("cx")
            cy = extent.get("cy")
            if cx and cy:
                return {"width_emu": int(cx), "height_emu": int(cy)}
        return None

    def _extract_images_from_element(self, element) -> List[Dict[str, Any]]:
        """从 XML 元素中提取嵌入图片（含尺寸信息）"""
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
                img_info = {
                    "data": image_part.blob,
                    "ext": self._get_image_ext(image_part.content_type),
                }
                extent = self._extract_image_extent(drawing)
                if extent:
                    img_info["width_emu"] = extent["width_emu"]
                    img_info["height_emu"] = extent["height_emu"]
                images.append(img_info)
            except (KeyError, AttributeError):
                pass

        VML_NS = "urn:schemas-microsoft-com:vml"

        for pict in element.findall(".//{%s}imagedata" % VML_NS):
            rId = pict.get(qn("r:id"))
            if rId is None:
                continue
            try:
                image_part = self.doc.part.related_parts[rId]
                img_info = {
                    "data": image_part.blob,
                    "ext": self._get_image_ext(image_part.content_type),
                }
                parent_shape = pict.getparent()
                while parent_shape is not None:
                    style = parent_shape.get("style", "")
                    if "width" in style or "height" in style:
                        for prop in style.split(";"):
                            prop = prop.strip()
                            if prop.startswith("width:"):
                                try:
                                    val = prop.split(":")[1].strip().rstrip("pt")
                                    img_info["width_emu"] = int(float(val) * 12700)
                                except (ValueError, IndexError):
                                    pass
                            elif prop.startswith("height:"):
                                try:
                                    val = prop.split(":")[1].strip().rstrip("pt")
                                    img_info["height_emu"] = int(float(val) * 12700)
                                except (ValueError, IndexError):
                                    pass
                        break
                    parent_shape = parent_shape.getparent()
                images.append(img_info)
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
        """提取段落中所有 run 的独立格式（包括 run 级别的图片及尺寸）"""
        runs: List[RunInfo] = []
        for run in para.runs:
            font = run.font
            color = "000000"
            if font.color and font.color.rgb:
                color = str(font.color.rgb)

            run_image = None
            if hasattr(run, "_element"):
                drawings = run._element.findall(
                    ".//{%s}drawing"
                    % "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                )
                if drawings:
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
                                img_info = {
                                    "data": image_part.blob,
                                    "ext": self._get_image_ext(image_part.content_type),
                                }
                                extent = self._extract_image_extent(drawings[0])
                                if extent:
                                    img_info["width_emu"] = extent["width_emu"]
                                    img_info["height_emu"] = extent["height_emu"]
                                run_image = img_info
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

    def _extract_cell_format(self, cell) -> CellFormatInfo:
        """提取单元格格式（垂直对齐、底色、边框、内边距）"""
        tc = cell._tc
        tc_pr = tc.find(qn("w:tcPr"))
        if tc_pr is None:
            return CellFormatInfo()

        v_align = "top"
        v_align_el = tc_pr.find(qn("w:vAlign"))
        if v_align_el is not None:
            v_align = v_align_el.get(qn("w:val"), "top")

        shading_fill = None
        shading_pattern = "clear"
        shd = tc_pr.find(qn("w:shd"))
        if shd is not None:
            fill_val = shd.get(qn("w:fill"))
            if fill_val and fill_val.upper() != "AUTO":
                shading_fill = fill_val
            pat_val = shd.get(qn("w:val"))
            if pat_val:
                shading_pattern = pat_val

        borders = None
        tc_borders = tc_pr.find(qn("w:tcBorders"))
        if tc_borders is not None:
            borders = {}
            for side in ["top", "left", "bottom", "right"]:
                border_el = tc_borders.find(qn("w:%s" % side))
                if border_el is not None:
                    borders[side] = {
                        "val": border_el.get(qn("w:val"), "none"),
                        "sz": border_el.get(qn("w:sz"), "0"),
                        "color": border_el.get(qn("w:color"), "000000"),
                    }

        margins = None
        tc_mar = tc_pr.find(qn("w:tcMar"))
        if tc_mar is not None:
            margins = {}
            for side in ["top", "left", "bottom", "right"]:
                mar_el = tc_mar.find(qn("w:%s" % side))
                if mar_el is not None:
                    w_val = mar_el.get(qn("w:w"))
                    w_type = mar_el.get(qn("w:type"), "dxa")
                    if w_val:
                        if w_type == "dxa":
                            margins[side] = int(w_val) / 567.0
                        else:
                            margins[side] = float(w_val)

        return CellFormatInfo(
            vertical_alignment=v_align,
            shading_fill=shading_fill,
            shading_pattern=shading_pattern,
            borders=borders,
            margins=margins,
        )

    def _extract_table_format(self, table) -> TableFormatInfo:
        """提取表格级格式（列宽、行高、对齐方式）"""
        tbl = table._tbl
        tbl_pr = tbl.find(qn("w:tblPr"))

        alignment = "left"
        width = None
        if tbl_pr is not None:
            jc = tbl_pr.find(qn("w:jc"))
            if jc is not None:
                alignment = jc.get(qn("w:val"), "left")
            tbl_w = tbl_pr.find(qn("w:tblW"))
            if tbl_w is not None:
                w_val = tbl_w.get(qn("w:w"))
                w_type = tbl_w.get(qn("w:type"), "auto")
                if w_val and w_type == "dxa":
                    width = int(w_val) / 567.0

        column_widths = []
        tbl_grid = tbl.find(qn("w:tblGrid"))
        if tbl_grid is not None:
            for grid_col in tbl_grid.findall(qn("w:gridCol")):
                w = grid_col.get(qn("w:w"))
                if w:
                    column_widths.append(int(w) / 567.0)

        row_heights = []
        for row in table.rows:
            tr = row._tr
            tr_pr = tr.find(qn("w:trPr"))
            h = None
            if tr_pr is not None:
                tr_height = tr_pr.find(qn("w:trHeight"))
                if tr_height is not None:
                    h_val = tr_height.get(qn("w:val"))
                    if h_val:
                        h = int(h_val) / 567.0
            row_heights.append(h if h is not None else 0.0)

        return TableFormatInfo(
            column_widths=column_widths,
            row_heights=row_heights,
            alignment=alignment,
            width=width,
        )

    def _extract_table_cells(self, table) -> List[List[TableCellInfo]]:
        """提取表格全部单元格文本+run 信息+图片+格式+合并信息"""
        rows: List[List[TableCellInfo]] = []
        seen_tc = set()

        for row in table.rows:
            cells: List[TableCellInfo] = []
            for cell in row.cells:
                tc_id = id(cell._tc)
                if tc_id in seen_tc:
                    cells.append(
                        TableCellInfo(
                            text="",
                            grid_span=1,
                            v_merge="continue",
                        )
                    )
                    continue
                seen_tc.add(tc_id)

                cell_runs: List[RunInfo] = []
                cell_paragraph_runs: List[List[RunInfo]] = []
                cell_images: List[Dict[str, Any]] = []

                for para in cell.paragraphs:
                    para_runs: List[RunInfo] = []
                    for run in para.runs:
                        font = run.font
                        color = "000000"
                        if font.color and font.color.rgb:
                            color = str(font.color.rgb)
                        run_image = None
                        if hasattr(run, "_element"):
                            drawings = run._element.findall(
                                ".//{%s}drawing"
                                % "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                            )
                            if drawings:
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
                                            image_part = self.doc.part.related_parts[
                                                rId
                                            ]
                                            img_info = {
                                                "data": image_part.blob,
                                                "ext": self._get_image_ext(
                                                    image_part.content_type
                                                ),
                                            }
                                            extent = self._extract_image_extent(
                                                drawings[0]
                                            )
                                            if extent:
                                                img_info["width_emu"] = extent[
                                                    "width_emu"
                                                ]
                                                img_info["height_emu"] = extent[
                                                    "height_emu"
                                                ]
                                            run_image = img_info
                                        except (KeyError, AttributeError):
                                            pass

                        run_info = RunInfo(
                            text=run.text,
                            font_name=font.name or "宋体",
                            font_size=font.size.pt if font.size else 12.0,
                            bold=font.bold or False,
                            italic=font.italic or False,
                            underline=font.underline or False,
                            color=color,
                            image=run_image,
                        )
                        cell_runs.append(run_info)
                        para_runs.append(run_info)

                    if para_runs:
                        cell_paragraph_runs.append(para_runs)

                    images = self._extract_images_from_element(para._element)
                    cell_images.extend(images)

                tc = cell._tc
                tc_pr = tc.find(qn("w:tcPr"))
                grid_span = 1
                v_merge = None
                if tc_pr is not None:
                    gs_el = tc_pr.find(qn("w:gridSpan"))
                    if gs_el is not None:
                        try:
                            grid_span = int(gs_el.get(qn("w:val"), "1"))
                        except (ValueError, TypeError):
                            pass
                    vm_el = tc_pr.find(qn("w:vMerge"))
                    if vm_el is not None:
                        vm_val = vm_el.get(qn("w:val"))
                        v_merge = "restart" if vm_val == "restart" else "continue"

                cell_format = self._extract_cell_format(cell)

                cells.append(
                    TableCellInfo(
                        text=cell.text,
                        runs=cell_runs,
                        paragraph_runs=cell_paragraph_runs,
                        images=cell_images,
                        grid_span=grid_span,
                        v_merge=v_merge,
                        cell_format=cell_format,
                    )
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

    # ================================================================
    # 段落格式提取（含样式继承链解析）
    # ================================================================

    def _extract_paragraph_format(self, para) -> ParagraphFormat:
        """提取段落实际生效的格式（沿样式继承链解析，不使用硬编码默认值）"""
        resolved = self._resolve_effective_format(para)
        return resolved

    def _resolve_effective_format(self, para) -> ParagraphFormat:
        """沿样式继承链解析段落实际生效的格式

        解析顺序：段落直接格式 → 引用样式 → 父样式链 → docDefaults → OOXML 规范默认值
        """
        fmt = ParagraphFormat()
        chain_values = self._collect_style_chain_values(para)

        alignment_map = {
            WD_ALIGN_PARAGRAPH.LEFT: "left",
            WD_ALIGN_PARAGRAPH.CENTER: "center",
            WD_ALIGN_PARAGRAPH.RIGHT: "right",
            WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
        }

        fmt.alignment = self._resolve_chain_value(
            chain_values,
            "alignment",
            lambda v: alignment_map.get(v, "left"),
            "left",
        )

        ls_val, lsr_val = self._resolve_line_spacing(chain_values)
        fmt.line_spacing = ls_val
        fmt.line_spacing_rule = lsr_val

        fmt.space_before = self._resolve_chain_value(
            chain_values,
            "space_before",
            lambda v: v.pt if isinstance(v, Length) else float(v),
            0.0,
        )
        fmt.space_after = self._resolve_chain_value(
            chain_values,
            "space_after",
            lambda v: v.pt if isinstance(v, Length) else float(v),
            0.0,
        )
        fmt.first_line_indent = self._resolve_chain_value(
            chain_values,
            "first_line_indent",
            lambda v: v.cm if isinstance(v, Length) else float(v),
            0.0,
        )
        fmt.left_indent = self._resolve_chain_value(
            chain_values,
            "left_indent",
            lambda v: v.cm if isinstance(v, Length) else float(v),
            0.0,
        )
        fmt.right_indent = self._resolve_chain_value(
            chain_values,
            "right_indent",
            lambda v: v.cm if isinstance(v, Length) else float(v),
            0.0,
        )

        fmt.keep_with_next = self._resolve_chain_value(
            chain_values,
            "keep_with_next",
            lambda v: bool(v),
            False,
        )
        fmt.keep_together = self._resolve_chain_value(
            chain_values,
            "keep_together",
            lambda v: bool(v),
            False,
        )
        fmt.page_break_before = self._resolve_chain_value(
            chain_values,
            "page_break_before",
            lambda v: bool(v),
            False,
        )
        fmt.widow_control = self._resolve_chain_value(
            chain_values,
            "widow_control",
            lambda v: bool(v) if v is not None else True,
            True,
        )

        return fmt

    def _collect_style_chain_values(self, para) -> List[Dict[str, Any]]:
        """收集样式继承链上各层级直接设置的原始值

        返回列表，索引 0 是段落直接格式（最高优先级），之后是样式链，最后是 docDefaults。
        """
        chain: List[Dict[str, Any]] = []

        para_fmt = self._read_raw_format_from_pf(para.paragraph_format)
        chain.append(para_fmt)

        if para.style:
            style = para.style
            visited = set()
            while style is not None:
                style_id = getattr(style, "style_id", id(style))
                if style_id in visited:
                    break
                visited.add(style_id)
                style_fmt = self._read_raw_format_from_pf(style.paragraph_format)
                chain.append(style_fmt)
                style = style.base_style

        doc_defaults_fmt = self._read_doc_defaults()
        chain.append(doc_defaults_fmt)

        return chain

    def _read_raw_format_from_pf(self, pf) -> Dict[str, Any]:
        """从 python-docx 的 ParagraphFormat 对象读取所有原始值（不做转换）"""
        return {
            "alignment": pf.alignment,
            "line_spacing": pf.line_spacing,
            "line_spacing_rule": pf.line_spacing_rule,
            "space_before": pf.space_before,
            "space_after": pf.space_after,
            "first_line_indent": pf.first_line_indent,
            "left_indent": pf.left_indent,
            "right_indent": pf.right_indent,
            "keep_with_next": pf.keep_with_next,
            "keep_together": pf.keep_together,
            "page_break_before": pf.page_break_before,
            "widow_control": pf.widow_control,
        }

    def _read_doc_defaults(self) -> Dict[str, Any]:
        """读取文档的 docDefaults 中的段落格式默认值"""
        defaults = {
            "alignment": None,
            "line_spacing": None,
            "line_spacing_rule": None,
            "space_before": None,
            "space_after": None,
            "first_line_indent": None,
            "left_indent": None,
            "right_indent": None,
            "keep_with_next": None,
            "keep_together": None,
            "page_break_before": None,
            "widow_control": None,
        }

        try:
            styles_elem = self.doc.styles.element
            doc_defaults = styles_elem.find(qn("w:docDefaults"))
            if doc_defaults is None:
                return defaults

            ppr_default = doc_defaults.find(qn("w:pPrDefault"))
            if ppr_default is None:
                return defaults

            ppr = ppr_default.find(qn("w:pPr"))
            if ppr is None:
                return defaults

            spacing = ppr.find(qn("w:spacing"))
            if spacing is not None:
                after_attr = spacing.get(qn("w:after"))
                if after_attr is not None:
                    defaults["space_after"] = Twips(int(after_attr))
                before_attr = spacing.get(qn("w:before"))
                if before_attr is not None:
                    defaults["space_before"] = Twips(int(before_attr))
                line_attr = spacing.get(qn("w:line"))
                if line_attr is not None:
                    line_val = int(line_attr)
                    line_rule = spacing.get(qn("w:lineRule"), "auto")
                    if line_rule == "auto":
                        defaults["line_spacing"] = line_val / 240.0
                        defaults["line_spacing_rule"] = "auto"
                    else:
                        defaults["line_spacing"] = Twips(line_val)
                        defaults["line_spacing_rule"] = line_rule

            jc = ppr.find(qn("w:jc"))
            if jc is not None:
                jc_map = {
                    "left": WD_ALIGN_PARAGRAPH.LEFT,
                    "center": WD_ALIGN_PARAGRAPH.CENTER,
                    "right": WD_ALIGN_PARAGRAPH.RIGHT,
                    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
                    "both": WD_ALIGN_PARAGRAPH.JUSTIFY,
                }
                defaults["alignment"] = jc_map.get(jc.get(qn("w:val"), "left"))

            ind = ppr.find(qn("w:ind"))
            if ind is not None:
                fi = ind.get(qn("w:firstLine"))
                if fi is not None:
                    defaults["first_line_indent"] = Twips(int(fi))
                li = ind.get(qn("w:left"))
                if li is not None:
                    defaults["left_indent"] = Twips(int(li))
                ri = ind.get(qn("w:right"))
                if ri is not None:
                    defaults["right_indent"] = Twips(int(ri))

            keep_next = ppr.find(qn("w:keepNext"))
            if keep_next is not None:
                defaults["keep_with_next"] = True
            keep_lines = ppr.find(qn("w:keepLines"))
            if keep_lines is not None:
                defaults["keep_together"] = True
            page_break = ppr.find(qn("w:pageBreakBefore"))
            if page_break is not None:
                defaults["page_break_before"] = True
            widow_ctrl = ppr.find(qn("w:widowControl"))
            if widow_ctrl is not None:
                val = widow_ctrl.get(qn("w:val"))
                defaults["widow_control"] = val != "0" if val else True

        except Exception:
            pass

        return defaults

    @staticmethod
    def _resolve_chain_value(
        chain: List[Dict[str, Any]],
        key: str,
        converter,
        ooxml_default,
    ):
        """沿继承链查找第一个非 None 的值，否则返回 OOXML 规范默认值"""
        for level in chain:
            val = level.get(key)
            if val is not None:
                return converter(val)
        return ooxml_default

    def _resolve_line_spacing(self, chain: List[Dict[str, Any]]):
        """沿继承链解析行距，返回 (line_spacing: float, line_spacing_rule: str)

        line_spacing 统一转为 float：
        - auto (MULTIPLE): 值/240 → 倍数
        - exact: Length → Pt 值
        - atLeast: Length → Pt 值
        全链均无值时返回 OOXML 默认值 (1.0, "auto")
        """
        for level in chain:
            ls = level.get("line_spacing")
            lsr = level.get("line_spacing_rule")
            if ls is not None:
                if isinstance(ls, Length):
                    pt_val = ls.pt
                    if lsr == WD_LINE_SPACING.AT_LEAST:
                        return pt_val, "atLeast"
                    return pt_val, "exact"
                elif lsr == WD_LINE_SPACING.MULTIPLE or lsr is None:
                    return float(ls), "auto"
                else:
                    if lsr == WD_LINE_SPACING.EXACTLY:
                        return float(ls), "exact"
                    elif lsr == WD_LINE_SPACING.AT_LEAST:
                        return float(ls), "atLeast"
                    return float(ls), "auto"
        return 1.0, "auto"

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
        alignment_map = {
            WD_ALIGN_PARAGRAPH.LEFT: "left",
            WD_ALIGN_PARAGRAPH.CENTER: "center",
            WD_ALIGN_PARAGRAPH.RIGHT: "right",
            WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
        }
        pf = style.paragraph_format

        ls_val = pf.line_spacing
        if ls_val is not None:
            if isinstance(ls_val, Length):
                line_spacing = ls_val.pt
            else:
                line_spacing = float(ls_val)
        else:
            line_spacing = 1.0

        return {
            "alignment": alignment_map.get(style.alignment, "left"),
            "line_spacing": line_spacing,
            "space_before": pf.space_before.pt if pf.space_before is not None else 0.0,
            "space_after": pf.space_after.pt if pf.space_after is not None else 0.0,
            "first_line_indent": (
                pf.first_line_indent.cm if pf.first_line_indent is not None else 0.0
            ),
            "left_indent": pf.left_indent.cm if pf.left_indent is not None else 0.0,
        }

    def get_text_content(self) -> str:
        return "\n".join(
            [para.text for para in self.doc.paragraphs if para.text.strip()]
        )

    def get_page_count(self) -> int:
        line_count = len([p for p in self.doc.paragraphs if p.text.strip()])
        return max(1, line_count // 30)

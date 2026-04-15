"""PDF解析器 - 增强版：分栏检测、跨页拼接、段落分组、连字符处理"""

import re
import fitz  # PyMuPDF
import pdfplumber
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PDFTextBlock:
    """PDF文本块"""

    text: str
    font_name: str
    font_size: float
    font_color: str
    is_bold: bool
    is_italic: bool
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    page_num: int


@dataclass
class PDFTable:
    """PDF表格"""

    data: List[List[str]]
    bbox: Tuple[float, float, float, float]
    page_num: int
    row_count: int
    col_count: int


@dataclass
class PDFImage:
    """PDF图片"""

    data: bytes
    bbox: Tuple[float, float, float, float]
    page_num: int
    ext: str


class PDFParser:
    """PDF解析器 - 增强版

    特性：
    - 分栏检测（密度分析算法）
    - 跨页连字符合并（如 comput-er → computer）
    - 段落边界识别（基于行距和字体变化）
    - 对齐方式检测（左/中/右/两端）
    - 图片位置还原
    - 表格增强提取（pdfplumber回退）
    """

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.doc = fitz.open(str(file_path))

    def close(self):
        if self.doc:
            self.doc.close()

    def get_page_count(self) -> int:
        return len(self.doc)

    def extract_text_blocks(self, page_num: int) -> List[PDFTextBlock]:
        """提取带样式信息的文本块"""
        if page_num >= len(self.doc):
            return []

        page = self.doc[page_num]
        blocks = page.get_text("dict")
        text_blocks = []

        for block in blocks.get("blocks", []):
            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue

                    font_name = span.get("font", "Unknown")
                    font_size = span.get("size", 12)
                    font_color_int = span.get("color", 0)
                    font_color = f"{font_color_int:06x}" if font_color_int else "000000"
                    flags = span.get("flags", 0)

                    is_bold = bool(flags & 2**4)
                    is_italic = bool(flags & 2**1)

                    bbox = span.get("bbox", (0, 0, 0, 0))

                    text_blocks.append(
                        PDFTextBlock(
                            text=text,
                            font_name=font_name,
                            font_size=font_size,
                            font_color=font_color,
                            is_bold=is_bold,
                            is_italic=is_italic,
                            bbox=bbox,
                            page_num=page_num,
                        )
                    )

        return text_blocks

    def extract_tables(self, page_num: int) -> List[PDFTable]:
        """提取表格（PyMuPDF优先，pdfplumber回退）"""
        if page_num >= len(self.doc):
            return []

        result = []
        page = self.doc[page_num]

        try:
            tables = page.find_tables()
            for table in tables:
                extracted = table.extract()
                cleaned = []
                for row in extracted:
                    cleaned.append([str(c) if c else "" for c in row])
                result.append(
                    PDFTable(
                        data=cleaned,
                        bbox=table.bbox,
                        page_num=page_num,
                        row_count=table.row_count,
                        col_count=table.col_count,
                    )
                )
        except Exception:
            pass

        if not result:
            try:
                with pdfplumber.open(str(self.file_path)) as pdf:
                    if page_num < len(pdf.pages):
                        pl_page = pdf.pages[page_num]
                        pl_tables = pl_page.extract_tables()
                        for t in pl_tables:
                            if not t:
                                continue
                            cleaned = [[str(c) if c else "" for c in row] for row in t]
                            rows = len(cleaned)
                            cols = max(len(r) for r in cleaned) if cleaned else 0
                            if rows > 0 and cols > 0:
                                result.append(
                                    PDFTable(
                                        data=cleaned,
                                        bbox=(0, 0, 0, 0),
                                        page_num=page_num,
                                        row_count=rows,
                                        col_count=cols,
                                    )
                                )
            except Exception:
                pass

        return result

    def extract_images(self, page_num: int) -> List[PDFImage]:
        """提取图片（含位置信息）"""
        if page_num >= len(self.doc):
            return []

        page = self.doc[page_num]
        image_list = page.get_images()

        result = []
        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]
                base_image = self.doc.extract_image(xref)
                if not base_image:
                    continue

                img_bbox = (0, 0, 0, 0)
                try:
                    page_img_rects = page.get_image_rects(xref)
                    if page_img_rects:
                        r = page_img_rects[0]
                        img_bbox = (r.x0, r.y0, r.x1, r.y1)
                except Exception:
                    pass

                result.append(
                    PDFImage(
                        data=base_image["image"],
                        bbox=img_bbox,
                        page_num=page_num,
                        ext=base_image.get("ext", "png"),
                    )
                )
            except Exception:
                pass

        return result

    def detect_columns(self, page_num: int) -> List[Tuple[float, float, float, float]]:
        """增强版分栏检测 - 基于文本密度间隙分析

        Returns:
            栏区域列表 [(x0, y0, x1, y1), ...]，单栏时返回整个页面
        """
        if page_num >= len(self.doc):
            return []

        page = self.doc[page_num]
        rect = page.rect
        page_width = rect.width
        page_height = rect.height

        blocks = page.get_text("blocks")
        text_blocks = [b for b in blocks if b[6] == 0]

        if len(text_blocks) < 4:
            return [fitz.Rect(rect)]

        all_x0 = sorted(set(b[0] for b in text_blocks))
        all_x1 = sorted(set(b[2] for b in text_blocks))

        if len(all_x0) < 2:
            return [fitz.Rect(rect)]

        center_x = rect.x0 + page_width / 2
        search_zone_min = center_x - page_width * 0.2
        search_zone_max = center_x + page_width * 0.2

        best_gap = 0
        gap_x0 = 0
        gap_x1 = 0

        for x1_val in all_x1:
            if x1_val < search_zone_min:
                continue
            next_x0_candidates = [x for x in all_x0 if x > x1_val]
            if not next_x0_candidates:
                continue
            next_x0 = next_x0_candidates[0]
            if next_x0 > search_zone_max:
                continue
            gap = next_x0 - x1_val
            if gap > best_gap:
                best_gap = gap
                gap_x0 = x1_val
                gap_x1 = next_x0

        min_column_gap = page_width * 0.04
        if best_gap < min_column_gap:
            return [fitz.Rect(rect)]

        col1 = fitz.Rect(rect.x0, rect.y0, gap_x0, rect.y1)
        col2 = fitz.Rect(gap_x1, rect.y0, rect.x1, rect.y1)

        return [col1, col2]

    def extract_all_text(self) -> str:
        """提取所有页面的文本"""
        all_text = []
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text("text")
            if text.strip():
                all_text.append(text)
        return "\n".join(all_text)

    def extract_structured_content(self) -> List[Dict[str, Any]]:
        """提取结构化内容（向后兼容，含更多格式信息）"""
        content_list = []

        for page_num in range(len(self.doc)):
            text_blocks = self.extract_text_blocks(page_num)

            lines = {}
            for block in text_blocks:
                y_key = round(block.bbox[1])
                if y_key not in lines:
                    lines[y_key] = {
                        "text": [],
                        "font_sizes": [],
                        "font_names": [],
                        "is_bold": False,
                        "is_italic": False,
                        "font_colors": [],
                        "bboxes": [],
                    }
                lines[y_key]["text"].append(block.text)
                lines[y_key]["font_sizes"].append(block.font_size)
                lines[y_key]["font_names"].append(block.font_name)
                lines[y_key]["font_colors"].append(block.font_color)
                lines[y_key]["bboxes"].append(block.bbox)
                if block.is_bold:
                    lines[y_key]["is_bold"] = True
                if block.is_italic:
                    lines[y_key]["is_italic"] = True

            page = self.doc[page_num]
            page_rect = page.rect

            for y_key in sorted(lines.keys()):
                line = lines[y_key]
                text = " ".join(line["text"])
                avg_font_size = (
                    sum(line["font_sizes"]) / len(line["font_sizes"])
                    if line["font_sizes"]
                    else 12
                )
                dominant_font = max(
                    set(line["font_names"]), key=line["font_names"].count
                )
                dominant_color = max(
                    set(line["font_colors"]), key=line["font_colors"].count
                )

                all_bboxes = line["bboxes"]
                alignment = self._detect_alignment_from_bboxes(all_bboxes, page_rect)

                content_list.append(
                    {
                        "text": text,
                        "font_name": dominant_font,
                        "font_size": avg_font_size,
                        "font_bold": line["is_bold"],
                        "font_italic": line["is_italic"],
                        "font_color": dominant_color,
                        "alignment": alignment,
                        "page_num": page_num,
                    }
                )

        return content_list

    def convert_to_paragraph_info_list(self) -> List[Dict[str, Any]]:
        """转换为段落信息列表（向后兼容）"""
        return self.extract_structured_content()

    def convert_to_content_elements(self) -> list:
        """将PDF内容转换为ContentElement列表（增强版）

        核心处理流程：
        1. 分栏检测 → 按栏提取文本
        2. 行合并 → 将span级文本合并为逻辑行
        3. 段落分组 → 基于行距和字体变化合并为段落
        4. 连字符处理 → 跨行/跨页的连字符合并
        5. 逐页按Y坐标混合排列段落/表格/图片（保持原文位置）
        """
        from ..docx.parser import (
            ContentElement,
            ElementType,
            ParagraphInfo,
            FontInfo,
            ParagraphFormat,
            TableCellInfo,
            TableFormatInfo,
        )
        from .converter import PDFStyleMapper

        all_lines = []

        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            page_rect = page.rect

            columns = self.detect_columns(page_num)
            is_multi_column = len(columns) > 1

            text_blocks = self.extract_text_blocks(page_num)

            if is_multi_column:
                column_groups = self._assign_blocks_to_columns(text_blocks, columns)
                for col_idx in sorted(column_groups.keys()):
                    col_blocks = column_groups[col_idx]
                    col_lines = self._group_blocks_by_y(col_blocks)
                    for y_key in sorted(col_lines.keys()):
                        line_blocks = col_lines[y_key]
                        all_lines.append(
                            self._build_line_info(
                                line_blocks, page_rect, page_num, col_idx
                            )
                        )
            else:
                col_lines = self._group_blocks_by_y(text_blocks)
                for y_key in sorted(col_lines.keys()):
                    line_blocks = col_lines[y_key]
                    all_lines.append(
                        self._build_line_info(line_blocks, page_rect, page_num, 0)
                    )

        all_lines.sort(key=lambda x: (x["page_num"], x["column_idx"], x["y_key"]))

        paragraphs = self._merge_lines_into_paragraphs(all_lines)
        paragraphs = self._handle_hyphenation(paragraphs)

        # 为每个段落记录其页面和Y位置（用于与表格/图片混合排序）
        para_with_pos = []
        for para in paragraphs:
            if para["lines"]:
                first_line = para["lines"][0]
                y_pos = first_line["y_position"]
                pg = first_line["page_num"]
            else:
                y_pos = 0
                pg = 0
            para_with_pos.append((para, pg, y_pos))

        # 逐页收集表格和图片的位置信息
        table_with_pos = []
        for page_num in range(len(self.doc)):
            tables = self.extract_tables(page_num)
            for table in tables:
                y_pos = table.bbox[1] if table.bbox and table.bbox[1] > 0 else 0
                table_with_pos.append((table, page_num, y_pos))

        image_with_pos = []
        for page_num in range(len(self.doc)):
            images = self.extract_images(page_num)
            for img in images:
                y_pos = img.bbox[1] if img.bbox and img.bbox[1] > 0 else 0
                image_with_pos.append((img, page_num, y_pos))

        # 按 (page_num, y_position) 统一排序所有元素
        unified = []
        for para, pg, y in para_with_pos:
            unified.append(("paragraph", para, pg, y))
        for table, pg, y in table_with_pos:
            unified.append(("table", table, pg, y))
        for img, pg, y in image_with_pos:
            unified.append(("image", img, pg, y))

        unified.sort(key=lambda x: (x[2], x[3]))

        elements = []
        original_index = 0

        for item_type, item_data, pg, y in unified:
            if item_type == "paragraph":
                elements.append(
                    ContentElement(
                        element_type=ElementType.PARAGRAPH,
                        original_index=original_index,
                        paragraph=ParagraphInfo(
                            index=original_index,
                            text=item_data["text"],
                            style_name="Normal",
                            font=item_data["font"],
                            format=item_data["format"],
                        ),
                    )
                )
            elif item_type == "table":
                table_cells = []
                for row in item_data.data:
                    cell_row = [TableCellInfo(text=cell_text) for cell_text in row]
                    table_cells.append(cell_row)
                elements.append(
                    ContentElement(
                        element_type=ElementType.TABLE,
                        original_index=original_index,
                        table_cells=table_cells,
                        table_format=TableFormatInfo(),
                    )
                )
            elif item_type == "image":
                elements.append(
                    ContentElement(
                        element_type=ElementType.IMAGE,
                        original_index=original_index,
                        image_data=item_data.data,
                        image_ext=item_data.ext,
                    )
                )
            original_index += 1

        return elements

    def _group_blocks_by_y(self, blocks: List[PDFTextBlock]) -> Dict[int, List[PDFTextBlock]]:
        """将文本块按Y坐标分组为行"""
        lines: Dict[int, list] = {}
        for block in blocks:
            y_key = round(block.bbox[1])
            if y_key not in lines:
                lines[y_key] = []
            lines[y_key].append(block)
        return lines

    def _assign_blocks_to_columns(
        self,
        blocks: List[PDFTextBlock],
        columns: List,
    ) -> Dict[int, List[PDFTextBlock]]:
        """将文本块分配到对应的栏"""
        column_groups: Dict[int, list] = {}
        for col_idx in range(len(columns)):
            column_groups[col_idx] = []

        for block in blocks:
            block_center_x = (block.bbox[0] + block.bbox[2]) / 2
            best_col = 0
            best_overlap = -1

            for col_idx, col_rect in enumerate(columns):
                if isinstance(col_rect, fitz.Rect):
                    col_x0, col_y0, col_x1, col_y1 = (
                        col_rect.x0,
                        col_rect.y0,
                        col_rect.x1,
                        col_rect.y1,
                    )
                else:
                    col_x0, col_y0, col_x1, col_y1 = col_rect

                if col_x0 <= block_center_x <= col_x1:
                    overlap = min(block.bbox[2], col_x1) - max(block.bbox[0], col_x0)
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_col = col_idx

            column_groups[best_col].append(block)

        return column_groups

    def _build_line_info(
        self,
        blocks: List[PDFTextBlock],
        page_rect,
        page_num: int,
        column_idx: int,
    ) -> Dict[str, Any]:
        """从一行的文本块构建行信息"""
        from ..docx.parser import FontInfo, ParagraphFormat
        from .converter import PDFStyleMapper

        if not blocks:
            return {
                "text": "",
                "font": FontInfo(),
                "format": ParagraphFormat(),
                "page_num": page_num,
                "column_idx": column_idx,
                "y_key": 0,
                "y_position": 0,
                "font_size": 12,
                "is_bold": False,
                "bboxes": [],
            }

        text = " ".join(b.text for b in blocks)
        dominant = max(blocks, key=lambda b: len(b.text))
        mapped_font = PDFStyleMapper.map_font(dominant.font_name)

        y_key = round(blocks[0].bbox[1])
        alignment = self._detect_alignment_from_bboxes(
            [b.bbox for b in blocks], page_rect
        )

        return {
            "text": text.strip(),
            "font": FontInfo(
                name=mapped_font,
                size=round(dominant.font_size, 1),
                bold=dominant.is_bold,
                italic=dominant.is_italic,
                color=dominant.font_color,
            ),
            "format": ParagraphFormat(alignment=alignment),
            "page_num": page_num,
            "column_idx": column_idx,
            "y_key": y_key,
            "y_position": blocks[0].bbox[1],
            "font_size": dominant.font_size,
            "is_bold": dominant.is_bold,
            "bboxes": [b.bbox for b in blocks],
        }

    def _merge_lines_into_paragraphs(self, lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将连续行合并为逻辑段落

        合并规则：
        1. 相同页面、相同栏、Y间距小于阈值 → 同一段落
        2. 字体大小或加粗状态变化 → 新段落
        3. 空行 → 新段落
        """
        if not lines:
            return []

        paragraphs = []
        current_lines = [lines[0]]

        for i in range(1, len(lines)):
            prev = lines[i - 1]
            curr = lines[i]

            same_column = (
                prev["page_num"] == curr["page_num"]
                and prev["column_idx"] == curr["column_idx"]
            )
            is_cross_page_continuation = (
                prev["page_num"] + 1 == curr["page_num"]
                and prev["column_idx"] == curr["column_idx"]
            )

            font_changed = (
                abs(prev.get("font_size", 12) - curr.get("font_size", 12)) > 1.0
                or prev.get("is_bold", False) != curr.get("is_bold", False)
            )

            y_gap_large = False
            if same_column:
                y_gap = curr["y_position"] - prev["y_position"]
                if y_gap > 0:
                    expected_line_height = prev.get("font_size", 12) * 1.8
                    if y_gap > expected_line_height * 1.5:
                        y_gap_large = True

            should_merge = False
            if same_column and not font_changed and not y_gap_large:
                should_merge = True
            elif is_cross_page_continuation and not font_changed:
                if prev["text"] and not prev["text"][-1] in ".!?。！？":
                    should_merge = True

            if should_merge:
                current_lines.append(curr)
            else:
                paragraphs.append(self._finalize_paragraph(current_lines))
                current_lines = [curr]

        if current_lines:
            paragraphs.append(self._finalize_paragraph(current_lines))

        return paragraphs

    def _finalize_paragraph(self, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """将一组行合并为最终段落"""
        from ..docx.parser import FontInfo, ParagraphFormat

        if not lines:
            return {
                "text": "",
                "font": FontInfo(),
                "format": ParagraphFormat(),
                "lines": [],
            }

        text_parts = []
        for line in lines:
            text_parts.append(line["text"])

        text = " ".join(text_parts)

        dominant_line = max(lines, key=lambda l: len(l.get("text", "")))

        font = dominant_line.get("font")
        if font is None:
            font = FontInfo()

        fmt = dominant_line.get("format")
        if fmt is None:
            fmt = ParagraphFormat()

        return {
            "text": text.strip(),
            "font": font,
            "format": fmt,
            "lines": lines,
        }

    def _handle_hyphenation(self, paragraphs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理英语行末连字符

        规则：
        - 行末以单个'-'结尾，且后跟小写字母 → 移除连字符合并
        - 跨页连字符同样处理
        """
        if not paragraphs:
            return paragraphs

        result = []
        i = 0
        while i < len(paragraphs):
            para = paragraphs[i]
            text = para["text"]

            if text.endswith("-") and i + 1 < len(paragraphs):
                next_text = paragraphs[i + 1]["text"]
                if next_text and next_text[0].islower():
                    words = text.rsplit(None, 1)
                    if len(words) > 1:
                        prefix = words[0]
                        hyphenated = words[-1][:-1]
                    else:
                        prefix = ""
                        hyphenated = text[:-1]

                    if prefix:
                        merged_text = f"{prefix} {hyphenated}{next_text}"
                    else:
                        merged_text = f"{hyphenated}{next_text}"

                    para["text"] = merged_text
                    i += 2
                    result.append(para)
                    continue

            result.append(para)
            i += 1

        return result

    def _detect_alignment_from_bboxes(
        self, bboxes: List[Tuple], page_rect
    ) -> str:
        """基于bbox位置检测对齐方式"""
        if not bboxes:
            return "left"

        avg_x0 = sum(b[0] for b in bboxes) / len(bboxes)
        avg_x1 = sum(b[2] for b in bboxes) / len(bboxes)
        page_width = page_rect.width if hasattr(page_rect, "width") else (
            page_rect[2] - page_rect[0]
        )
        page_x0 = page_rect.x0 if hasattr(page_rect, "x0") else page_rect[0]
        page_x1 = page_rect.x1 if hasattr(page_rect, "x1") else page_rect[2]

        left_margin = avg_x0 - page_x0
        right_margin = page_x1 - avg_x1

        if (
            abs(left_margin - right_margin) < page_width * 0.05
            and left_margin > page_width * 0.05
        ):
            return "center"

        if right_margin > left_margin * 1.5 and left_margin > page_width * 0.15:
            return "right"

        return "left"

    def _detect_alignment(self, blocks: list, page_rect) -> str:
        """基于PDFTextBlock列表检测对齐方式（向后兼容）"""
        return self._detect_alignment_from_bboxes(
            [b.bbox for b in blocks], page_rect
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

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
        """将PDF内容转换为ContentElement列表（增强版v2）

        核心改进：
        1. 以PDF line为基本段落单位，避免过度合并
        2. 每个span变成独立RunInfo，保留run级格式差异
        3. 从bbox推导段落格式（行距、缩进、对齐）
        4. 过滤虚假图片（极小装饰性元素）
        5. 表格内文本区域不重复输出为段落
        6. 智能段落合并：仅合并Y间距极小的连续行
        """
        from ..docx.parser import (
            ContentElement,
            ElementType,
            ParagraphInfo,
            FontInfo,
            ParagraphFormat,
            RunInfo,
            TableCellInfo,
            TableFormatInfo,
        )
        from .converter import PDFStyleMapper

        table_regions = self._collect_table_regions()

        all_raw_lines = []

        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            page_rect = page.rect

            columns = self.detect_columns(page_num)
            is_multi_column = len(columns) > 1

            raw_lines = self._extract_raw_lines(page_num, page_rect)

            if is_multi_column:
                col_lines = self._assign_raw_lines_to_columns(raw_lines, columns)
                for col_idx in sorted(col_lines.keys()):
                    for rl in col_lines[col_idx]:
                        rl["column_idx"] = col_idx
                        all_raw_lines.append(rl)
            else:
                for rl in raw_lines:
                    rl["column_idx"] = 0
                    all_raw_lines.append(rl)

        all_raw_lines.sort(
            key=lambda x: (x["page_num"], x["column_idx"], x["y_position"])
        )

        paragraphs = self._smart_merge_lines(all_raw_lines)

        para_with_pos = []
        for para_info in paragraphs:
            first_span = para_info["spans"][0] if para_info["spans"] else None
            y_pos = first_span["bbox"][1] if first_span else 0
            pg = para_info["page_num"]
            para_with_pos.append((para_info, pg, y_pos))

        table_with_pos = []
        for page_num in range(len(self.doc)):
            tables = self.extract_tables(page_num)
            for table in tables:
                y_pos = table.bbox[1] if table.bbox and table.bbox[1] > 0 else 0
                table_with_pos.append((table, page_num, y_pos))

        image_with_pos = []
        for page_num in range(len(self.doc)):
            images = self._extract_meaningful_images(page_num)
            for img in images:
                y_pos = img.bbox[1] if img.bbox and img.bbox[1] > 0 else 0
                image_with_pos.append((img, page_num, y_pos))

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
                if self._is_in_table_region(pg, y, table_regions):
                    continue
                para_element = self._build_paragraph_element(
                    item_data, original_index
                )
                if para_element:
                    elements.append(para_element)
                    original_index += 1
            elif item_type == "table":
                table_cells = self._build_table_cells_with_runs(item_data)
                table_format = self._build_table_format(item_data)
                elements.append(
                    ContentElement(
                        element_type=ElementType.TABLE,
                        original_index=original_index,
                        table_cells=table_cells,
                        table_format=table_format,
                    )
                )
                original_index += 1
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

    def _extract_raw_lines(self, page_num: int, page_rect) -> list:
        """提取页面中的所有原始行，每行包含完整span信息"""
        from .converter import PDFStyleMapper

        if page_num >= len(self.doc):
            return []

        page = self.doc[page_num]
        blocks = page.get_text("dict")
        raw_lines = []

        for block in blocks.get("blocks", []):
            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):
                line_bbox = line.get("bbox", (0, 0, 0, 0))
                spans_data = []

                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if not text.strip():
                        continue

                    font_name = span.get("font", "Unknown")
                    font_size = span.get("size", 12)
                    font_color_int = span.get("color", 0)
                    font_color = f"{font_color_int:06x}" if font_color_int else "000000"
                    flags = span.get("flags", 0)
                    is_bold = bool(flags & 2**4)
                    is_italic = bool(flags & 2**1)
                    bbox = span.get("bbox", (0, 0, 0, 0))

                    mapped_font = PDFStyleMapper.map_font(font_name)

                    spans_data.append({
                        "text": text,
                        "font_name": mapped_font,
                        "original_font_name": font_name,
                        "font_size": round(font_size, 1),
                        "font_color": font_color,
                        "is_bold": is_bold,
                        "is_italic": is_italic,
                        "bbox": bbox,
                    })

                if spans_data:
                    full_text = "".join(s["text"] for s in spans_data).strip()
                    if full_text:
                        line_y = line_bbox[1]
                        line_y_end = line_bbox[3]
                        raw_lines.append({
                            "spans": spans_data,
                            "text": full_text,
                            "page_num": page_num,
                            "y_position": line_y,
                            "y_end": line_y_end,
                            "x_start": line_bbox[0],
                            "x_end": line_bbox[2],
                            "line_height": line_y_end - line_y if line_y_end > line_y else 0,
                        })

        raw_lines.sort(key=lambda x: x["y_position"])

        merged_lines = []
        for rl in raw_lines:
            if merged_lines:
                prev = merged_lines[-1]
                same_y = abs(rl["y_position"] - prev["y_position"]) < 2
                same_page = rl["page_num"] == prev["page_num"]
                if same_y and same_page:
                    gap = rl["x_start"] - prev["x_end"]
                    if gap < 100:
                        tab_span = {
                            "text": "\t",
                            "font_name": prev["spans"][-1]["font_name"] if prev["spans"] else "宋体",
                            "original_font_name": "",
                            "font_size": prev["spans"][-1].get("font_size", 12) if prev["spans"] else 12,
                            "font_color": prev["spans"][-1].get("font_color", "000000") if prev["spans"] else "000000",
                            "is_bold": False,
                            "is_italic": False,
                            "bbox": (prev["x_end"], prev["y_position"], rl["x_start"], prev["y_end"]),
                        }
                        prev["spans"].append(tab_span)
                        prev["spans"].extend(rl["spans"])
                        prev["text"] = prev["text"] + "\t" + rl["text"]
                        prev["x_end"] = max(prev["x_end"], rl["x_end"])
                        prev["y_end"] = max(prev["y_end"], rl["y_end"])
                        prev["line_height"] = max(prev["line_height"], rl["line_height"])
                        continue
            merged_lines.append(rl)

        return merged_lines

    def _assign_raw_lines_to_columns(self, raw_lines: list, columns: list) -> dict:
        """将行分配到对应的栏"""
        col_groups: Dict[int, list] = {i: [] for i in range(len(columns))}
        for rl in raw_lines:
            cx = (rl["x_start"] + rl["x_end"]) / 2
            best_col = 0
            for col_idx, col_rect in enumerate(columns):
                if isinstance(col_rect, fitz.Rect):
                    col_x0, col_x1 = col_rect.x0, col_rect.x1
                else:
                    col_x0, col_x1 = col_rect[0], col_rect[2]
                if col_x0 <= cx <= col_x1:
                    best_col = col_idx
                    break
            col_groups[best_col].append(rl)
        return col_groups

    def _smart_merge_lines(self, raw_lines: list) -> list:
        """智能段落合并

        合并策略：
        1. 同一PDF line内多个span已经是同一行，不拆分
        2. 不同PDF line之间：如果Y间距极小（<行高×0.1），则合并为同一段落
        3. 跨行选项（A/B/C/D在同一行）：如果Y间距小于1行高则合并
        """
        if not raw_lines:
            return []

        result = []
        current_group = [raw_lines[0]]

        for i in range(1, len(raw_lines)):
            prev = current_group[-1]
            curr = raw_lines[i]

            same_page = prev["page_num"] == curr["page_num"]
            same_col = prev.get("column_idx", 0) == curr.get("column_idx", 0)

            should_merge = False
            if same_page and same_col:
                y_gap = curr["y_position"] - prev["y_end"]

                prev_font_size = prev["spans"][0]["font_size"] if prev["spans"] else 12
                curr_font_size = curr["spans"][0]["font_size"] if curr["spans"] else 12
                font_size_similar = abs(prev_font_size - curr_font_size) < 0.5

                prev_bold = any(s["is_bold"] for s in prev["spans"])
                curr_bold = any(s["is_bold"] for s in curr["spans"])
                bold_same = prev_bold == curr_bold

                prev_x_end = prev["x_end"]
                curr_x_start = curr["x_start"]
                horizontal_overlap = prev_x_end > curr_x_start

                x_start_similar = abs(prev["x_start"] - curr["x_start"]) < 5

                expected_lh = prev_font_size * 1.5
                very_tight = y_gap < expected_lh * 0.15 and y_gap >= -2
                tight = y_gap < expected_lh * 0.6 and y_gap >= -2

                if very_tight and font_size_similar and bold_same:
                    should_merge = True
                elif tight and horizontal_overlap and font_size_similar and bold_same:
                    curr_text_stripped = curr["text"].strip()
                    is_option_line = (
                        curr_text_stripped
                        and len(curr_text_stripped) < 60
                        and re.match(r'^[A-D][．.、)）]', curr_text_stripped)
                    )
                    if is_option_line and x_start_similar:
                        should_merge = True

            if should_merge:
                current_group.append(curr)
            else:
                result.append(self._finalize_raw_line_group(current_group))
                current_group = [curr]

        if current_group:
            result.append(self._finalize_raw_line_group(current_group))

        return result

    def _finalize_raw_line_group(self, group: list) -> dict:
        """将一组行合并为段落信息，保留所有span级RunInfo"""
        from ..docx.parser import FontInfo, ParagraphFormat, RunInfo

        all_spans = []
        for line in group:
            all_spans.extend(line["spans"])

        full_text = " ".join(
            "".join(s["text"] for s in line["spans"])
            for line in group
        ).strip()

        first_span = all_spans[0] if all_spans else None
        last_span = all_spans[-1] if all_spans else None

        dominant_span = max(all_spans, key=lambda s: len(s["text"])) if all_spans else None

        page_rect = None
        page_num = group[0]["page_num"] if group else 0
        if page_num < len(self.doc):
            page_rect = self.doc[page_num].rect

        alignment = "left"
        if page_rect and group:
            all_x0 = [line["x_start"] for line in group]
            all_x1 = [line["x_end"] for line in group]
            avg_x0 = sum(all_x0) / len(all_x0)
            avg_x1 = sum(all_x1) / len(all_x1)
            page_w = page_rect.width
            left_m = avg_x0 - page_rect.x0
            right_m = page_rect.x1 - avg_x1

            if abs(left_m - right_m) < page_w * 0.05 and left_m > page_w * 0.05:
                alignment = "center"
            elif right_m > left_m * 2.0 and left_m > page_w * 0.15:
                alignment = "right"

        runs = []
        for span in all_spans:
            runs.append(RunInfo(
                text=span["text"],
                font_name=span["font_name"],
                font_size=span["font_size"],
                bold=span["is_bold"],
                italic=span["is_italic"],
                color=span["font_color"],
            ))

        font_info = FontInfo(
            name=dominant_span["font_name"] if dominant_span else "宋体",
            size=dominant_span["font_size"] if dominant_span else 12.0,
            bold=any(s["is_bold"] for s in all_spans),
            italic=any(s["is_italic"] for s in all_spans),
            color=dominant_span["font_color"] if dominant_span else "000000",
        )

        line_spacing = None
        if len(group) >= 2:
            first_lh = group[0].get("line_height", 0)
            if first_lh > 0:
                font_sz = dominant_span["font_size"] if dominant_span else 12
                ratio = first_lh / font_sz if font_sz > 0 else 1
                if ratio > 1.1:
                    line_spacing = round(ratio, 2)

        left_indent = None
        if page_rect and first_span:
            margin_cm = (first_span["bbox"][0] - page_rect.x0) / 28.35
            if margin_cm > 0.5:
                left_indent = round(margin_cm, 2)

        para_format = ParagraphFormat(
            alignment=alignment,
            line_spacing=line_spacing,
            left_indent=left_indent,
        )

        return {
            "text": full_text,
            "runs": runs,
            "font": font_info,
            "format": para_format,
            "spans": all_spans,
            "page_num": page_num,
            "y_position": group[0]["y_position"] if group else 0,
        }

    def _build_paragraph_element(self, para_data: dict, index: int):
        """从段落数据构建ContentElement"""
        from ..docx.parser import (
            ContentElement,
            ElementType,
            ParagraphInfo,
        )

        text = para_data["text"]
        if not text.strip():
            return None

        return ContentElement(
            element_type=ElementType.PARAGRAPH,
            original_index=index,
            paragraph=ParagraphInfo(
                index=index,
                text=text,
                style_name="Normal",
                font=para_data["font"],
                format=para_data["format"],
                runs=para_data["runs"],
            ),
        )

    def _collect_table_regions(self) -> list:
        """收集所有页面的表格区域bbox，用于过滤段落重复"""
        regions = []
        for page_num in range(len(self.doc)):
            tables = self.extract_tables(page_num)
            for table in tables:
                regions.append({
                    "page_num": page_num,
                    "bbox": table.bbox,
                })
        return regions

    def _is_in_table_region(self, page_num: int, y_pos: float, table_regions: list) -> bool:
        """检查指定位置是否在表格区域内"""
        for tr in table_regions:
            if tr["page_num"] != page_num:
                continue
            bbox = tr["bbox"]
            if not bbox or bbox == (0, 0, 0, 0):
                continue
            margin = 5
            if bbox[1] - margin <= y_pos <= bbox[3] + margin:
                return True
        return False

    def _extract_meaningful_images(self, page_num: int) -> list:
        """提取有意义的图片，过滤掉装饰性/极小元素"""
        all_images = self.extract_images(page_num)
        meaningful = []
        for img in all_images:
            w = img.bbox[2] - img.bbox[0] if img.bbox and len(img.bbox) >= 4 else 0
            h = img.bbox[3] - img.bbox[1] if img.bbox and len(img.bbox) >= 4 else 0
            if w > 20 and h > 20 and len(img.data) > 200:
                meaningful.append(img)
        return meaningful

    def _build_table_cells_with_runs(self, table) -> list:
        """构建表格单元格，尽量保留run级格式信息"""
        from ..docx.parser import TableCellInfo, RunInfo

        cells = []
        for row in table.data:
            cell_row = []
            for cell_text in row:
                cell_row.append(TableCellInfo(text=str(cell_text) if cell_text else ""))
            cells.append(cell_row)
        return cells

    def _build_table_format(self, table) -> "TableFormatInfo":
        """从PDF表格提取格式信息（列宽、尺寸）"""
        from ..docx.parser import TableFormatInfo

        col_widths = []
        if table.bbox and table.bbox != (0, 0, 0, 0) and table.col_count > 0:
            total_w = table.bbox[2] - table.bbox[0]
            avg_col_w = total_w / table.col_count
            col_widths = [round(avg_col_w / 28.35, 2)] * table.col_count

        return TableFormatInfo(
            column_widths=col_widths,
            alignment="center" if table.col_count > 2 else "left",
        )

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

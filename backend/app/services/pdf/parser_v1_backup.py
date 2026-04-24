"""PDF解析器 - v3：自适应段落合并、分栏检测、表格增强、页眉页脚过滤"""

import re
import statistics
import fitz  # PyMuPDF
import pdfplumber
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PDFTextBlock:
    text: str
    font_name: str
    font_size: float
    font_color: str
    is_bold: bool
    is_italic: bool
    bbox: Tuple[float, float, float, float]
    page_num: int


@dataclass
class PDFTable:
    data: List[List[str]]
    bbox: Tuple[float, float, float, float]
    page_num: int
    row_count: int
    col_count: int


@dataclass
class PDFImage:
    data: bytes
    bbox: Tuple[float, float, float, float]
    page_num: int
    ext: str


_PAGE_NUMBER_PATTERN = re.compile(
    r"^[\s]*第?\s*\d+\s*[页頁]?\s*(共\s*\d+\s*[页頁])?[\s]*$"
    r"|^[\s]*Page\s*\d+[\s]*(of\s*\d+)?[\s]*$"
    r"|^[\s]*\-\s*\d+\s*\-[\s]*$"
    r"|^[\s]*\d+\s*/\s*\d+[\s]*$"
    r"|^[\s]*\d+[\s]*$",
    re.IGNORECASE,
)

_HEADER_FOOTER_PATTERN = re.compile(
    r"学科网|中小学教育资源及组卷应用平台|21世纪教育网|百度文库|道客巴巴|豆丁网"
    r"| wenku| docin| doc88",
    re.IGNORECASE,
)

_SEAL_LINE_PATTERN = re.compile(
    r"^[…\.。…\-—]+\s*[○O0]*\s*.*(?:装订|密封|线).*[○O0]*\s*[…\.。…\-—]*$"
    r"|^[…\.。…\-—]+\s*[○O0]+\s*[…\.。…\-—]+$",
)


class PDFParser:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.doc = fitz.open(str(file_path))

    def close(self):
        if self.doc:
            self.doc.close()

    def get_page_count(self) -> int:
        return len(self.doc)

    def extract_text_blocks(self, page_num: int) -> List[PDFTextBlock]:
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

                non_empty_rows = sum(
                    1 for row in cleaned if any(cell.strip() for cell in row)
                )
                if non_empty_rows < 1:
                    continue

                max_text_len = max(
                    (len(cell) for row in cleaned for cell in row), default=0
                )
                avg_cells_per_row = sum(len(r) for r in cleaned) / max(len(cleaned), 1)
                if max_text_len > 200 and avg_cells_per_row <= 2:
                    continue

                table_w = table.bbox[2] - table.bbox[0]
                table_h = table.bbox[3] - table.bbox[1]
                if table_w > 0 and table_h > 0:
                    aspect_ratio = table_h / table_w
                    if aspect_ratio > 8 and table.col_count <= 2:
                        continue
                    if table_w < 50 and table_h > 200:
                        continue

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

    def detect_columns(self, page_num: int) -> List:
        if page_num >= len(self.doc):
            return []

        page = self.doc[page_num]
        rect = page.rect
        page_width = rect.width
        page_height = rect.height

        if page_width > page_height * 1.3:
            return self._detect_a3_columns(page_num)

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

    def _detect_a3_columns(self, page_num: int) -> List:
        page = self.doc[page_num]
        rect = page.rect
        mid_x = rect.x0 + rect.width / 2

        blocks = page.get_text("blocks")
        text_blocks = [b for b in blocks if b[6] == 0]

        left_content = [b for b in text_blocks if b[2] < mid_x]
        right_content = [b for b in text_blocks if b[0] > mid_x]

        if len(left_content) >= 3 and len(right_content) >= 3:
            left_max_x1 = max(b[2] for b in left_content)
            right_min_x0 = min(b[0] for b in right_content)
            gap = right_min_x0 - left_max_x1

            if gap > 0:
                col1 = fitz.Rect(rect.x0, rect.y0, left_max_x1, rect.y1)
                col2 = fitz.Rect(right_min_x0, rect.y0, rect.x1, rect.y1)
                return [col1, col2]

        col1 = fitz.Rect(rect.x0, rect.y0, mid_x - 10, rect.y1)
        col2 = fitz.Rect(mid_x + 10, rect.y0, rect.x1, rect.y1)
        return [col1, col2]

    def extract_all_text(self) -> str:
        all_text = []
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text("text")
            if text.strip():
                all_text.append(text)
        return "\n".join(all_text)

    def extract_structured_content(self) -> List[Dict[str, Any]]:
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
        return self.extract_structured_content()

    def convert_to_content_elements(self) -> list:
        """将PDF内容转换为ContentElement列表（v3自适应版）

        核心改进：
        1. 自适应段落合并：统计主导行间距，智能区分段内换行和段间换行
        2. 页眉页脚/水印/密封线过滤
        3. A3横版页面自动识别并分栏
        4. 表格质量验证（过滤假表格）
        5. 表格区域内文本精确去重
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

        header_footer_regions = self._detect_header_footer_regions()
        table_regions = self._collect_table_regions()

        all_raw_lines = []

        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            page_rect = page.rect

            columns = self.detect_columns(page_num)
            is_multi_column = len(columns) > 1

            raw_lines = self._extract_raw_lines(page_num, page_rect)

            filtered_lines = self._filter_header_footer_lines(
                raw_lines, page_rect, header_footer_regions.get(page_num, [])
            )

            if is_multi_column:
                col_lines = self._assign_raw_lines_to_columns(filtered_lines, columns)
                for col_idx in sorted(col_lines.keys()):
                    for rl in col_lines[col_idx]:
                        rl["column_idx"] = col_idx
                        all_raw_lines.append(rl)
            else:
                for rl in filtered_lines:
                    rl["column_idx"] = 0
                    all_raw_lines.append(rl)

        all_raw_lines.sort(
            key=lambda x: (x["page_num"], x["column_idx"], x["y_position"])
        )

        paragraphs = self._adaptive_merge_lines(all_raw_lines)

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
                para_spans = item_data.get("spans", [])
                x_pos = para_spans[0]["bbox"][0] if para_spans else 0
                x_end = para_spans[-1]["bbox"][2] if para_spans else 0
                if self._is_in_table_region(pg, y, table_regions, x_pos, x_end):
                    continue
                para_element = self._build_paragraph_element(item_data, original_index)
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

    # ================================================================
    # 页眉页脚 / 水印检测
    # ================================================================

    def _detect_header_footer_regions(self) -> Dict[int, list]:
        """检测每页的页眉页脚区域（Y范围列表）"""
        regions = {}
        page_count = len(self.doc)

        if page_count < 2:
            return regions

        footer_texts = {}
        header_texts = {}

        for page_num in range(page_count):
            page = self.doc[page_num]
            page_rect = page.rect
            bottom_zone = page_rect.height * 0.85
            top_zone = page_rect.height * 0.15

            blocks = page.get_text("dict")
            for block in blocks.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    line_bbox = line.get("bbox", (0, 0, 0, 0))
                    line_text = "".join(
                        s.get("text", "") for s in line.get("spans", [])
                    ).strip()
                    if not line_text:
                        continue

                    max_font = max(
                        (s.get("size", 12) for s in line.get("spans", [])), default=12
                    )

                    if max_font < 2:
                        if page_num not in regions:
                            regions[page_num] = []
                        regions[page_num].append(
                            (line_bbox[1], line_bbox[3], "watermark")
                        )
                        continue

                    if line_bbox[1] > bottom_zone:
                        key = line_text.strip()
                        if not _PAGE_NUMBER_PATTERN.match(key):
                            key_clean = re.sub(r"\d+", "N", key).strip()
                        else:
                            key_clean = "__pagenum__"
                        footer_texts.setdefault(key_clean, []).append(
                            (page_num, line_bbox[1], line_bbox[3])
                        )

                    if line_bbox[3] < top_zone and line_bbox[1] < top_zone * 0.5:
                        key = line_text.strip()
                        key_clean = re.sub(r"\d+", "N", key).strip()
                        header_texts.setdefault(key_clean, []).append(
                            (page_num, line_bbox[1], line_bbox[3])
                        )

        threshold = max(2, page_count * 0.4)

        for key, occurrences in footer_texts.items():
            if len(occurrences) >= threshold:
                for page_num, y0, y1 in occurrences:
                    if page_num not in regions:
                        regions[page_num] = []
                    regions[page_num].append((y0, y1, "footer"))

        for key, occurrences in header_texts.items():
            if len(occurrences) >= threshold:
                for page_num, y0, y1 in occurrences:
                    if page_num not in regions:
                        regions[page_num] = []
                    regions[page_num].append((y0, y1, "header"))

        return regions

    def _filter_header_footer_lines(
        self, raw_lines: list, page_rect, hf_regions: list
    ) -> list:
        """过滤页眉页脚/水印/密封线"""
        page_h = page_rect.height if page_rect else 842

        filtered = []
        for rl in raw_lines:
            text = rl["text"].strip()
            dominant_fs = rl["spans"][0]["font_size"] if rl["spans"] else 12

            if dominant_fs < 2:
                continue

            if _SEAL_LINE_PATTERN.match(text):
                continue

            y_pos = rl["y_position"]
            y_end = rl["y_end"]

            is_hf = False
            for region_y0, region_y1, region_type in hf_regions:
                if region_y0 - 3 <= y_pos <= region_y1 + 3:
                    is_hf = True
                    break
                if region_y0 - 3 <= y_end <= region_y1 + 3:
                    is_hf = True
                    break
            if is_hf:
                continue

            if _HEADER_FOOTER_PATTERN.search(text):
                if len(text) < 40 and (y_end < page_h * 0.08 or y_pos > page_h * 0.92):
                    continue

            filtered.append(rl)

        return filtered

    # ================================================================
    # 原始行提取
    # ================================================================

    def _extract_raw_lines(self, page_num: int, page_rect) -> list:
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

                    spans_data.append(
                        {
                            "text": text,
                            "font_name": mapped_font,
                            "original_font_name": font_name,
                            "font_size": round(font_size, 1),
                            "font_color": font_color,
                            "is_bold": is_bold,
                            "is_italic": is_italic,
                            "bbox": bbox,
                        }
                    )

                if spans_data:
                    full_text = "".join(s["text"] for s in spans_data).strip()
                    if full_text:
                        line_y = line_bbox[1]
                        line_y_end = line_bbox[3]
                        raw_lines.append(
                            {
                                "spans": spans_data,
                                "text": full_text,
                                "page_num": page_num,
                                "y_position": line_y,
                                "y_end": line_y_end,
                                "x_start": line_bbox[0],
                                "x_end": line_bbox[2],
                                "line_height": line_y_end - line_y
                                if line_y_end > line_y
                                else 0,
                            }
                        )

        raw_lines.sort(key=lambda x: (x["y_position"], x["x_start"]))

        merged_lines = []
        for rl in raw_lines:
            if merged_lines:
                prev = merged_lines[-1]
                same_y = abs(rl["y_position"] - prev["y_position"]) < 2
                same_page = rl["page_num"] == prev["page_num"]
                if same_y and same_page:
                    gap = rl["x_start"] - prev["x_end"]
                    if gap < 150:
                        sep_char = "\t" if gap > 20 else ""
                        if sep_char:
                            sep_span = {
                                "text": sep_char,
                                "font_name": prev["spans"][-1]["font_name"]
                                if prev["spans"]
                                else "宋体",
                                "original_font_name": "",
                                "font_size": prev["spans"][-1].get("font_size", 12)
                                if prev["spans"]
                                else 12,
                                "font_color": prev["spans"][-1].get(
                                    "font_color", "000000"
                                )
                                if prev["spans"]
                                else "000000",
                                "is_bold": False,
                                "is_italic": False,
                                "bbox": (
                                    prev["x_end"],
                                    prev["y_position"],
                                    rl["x_start"],
                                    prev["y_end"],
                                ),
                            }
                            prev["spans"].append(sep_span)
                        prev["spans"].extend(rl["spans"])
                        prev["text"] = prev["text"] + sep_char + rl["text"]
                        prev["x_end"] = max(prev["x_end"], rl["x_end"])
                        prev["y_end"] = max(prev["y_end"], rl["y_end"])
                        prev["line_height"] = max(
                            prev["line_height"], rl["line_height"]
                        )
                        continue
            merged_lines.append(rl)

        return merged_lines

    # ================================================================
    # 自适应段落合并（核心算法 v3）
    # ================================================================

    _RE_NUMBERED_START = re.compile(r"^[\d一二三四五六七八九十]+[\.．、)）\s]\s*")
    _RE_OPTION_START = re.compile(r"^[A-D][\.．、)）\s]")
    _RE_QUESTION_OPTION = re.compile(r"^\d+[\.．、)）]\s*[A-D][\.．、)）]")

    def _adaptive_merge_lines(self, raw_lines: list) -> list:
        """自适应段落合并（v3.2）

        核心原则：英语教学资料中，大多数PDF行本身就是独立段落。
        只在明确的文本连续性证据下才合并行：
        1. Y间距极小（重叠行或紧贴行）→ 必须合并
        2. 同字体、同粗体、x起始相似、Y间距≤主导间距×1.15
           且有文本连续性证据 → 合并
        3. 额外防护：短行/选项行/编号行不与前文合并
        """
        if not raw_lines:
            return []

        line_gaps = self._compute_dominant_gaps(raw_lines)

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

                prev_fs = prev["spans"][0]["font_size"] if prev["spans"] else 12
                curr_fs = curr["spans"][0]["font_size"] if curr["spans"] else 12
                font_size_similar = abs(prev_fs - curr_fs) < 1.0

                prev_bold = any(s["is_bold"] for s in prev["spans"])
                curr_bold = any(s["is_bold"] for s in curr["spans"])
                bold_same = prev_bold == curr_bold

                x_start_similar = abs(prev["x_start"] - curr["x_start"]) < 15

                page_col_key = (prev["page_num"], prev.get("column_idx", 0))
                dominant_gap = line_gaps.get(page_col_key, prev_fs * 1.3)

                curr_text = curr["text"].strip()
                prev_text = prev["text"].strip()

                is_numbered = bool(self._RE_NUMBERED_START.match(curr_text))
                is_option = bool(self._RE_OPTION_START.match(curr_text))
                is_question_option = bool(self._RE_QUESTION_OPTION.match(curr_text))

                if is_question_option or is_numbered or is_option:
                    pass
                elif y_gap < 0:
                    should_merge = True
                elif y_gap < prev_fs * 0.15 and font_size_similar:
                    should_merge = True
                elif font_size_similar and bold_same and x_start_similar:
                    if y_gap < dominant_gap * 1.05:
                        if (
                            curr_text
                            and not curr_text[0].isupper()
                            and not self._RE_NUMBERED_START.match(curr_text)
                            and not self._RE_OPTION_START.match(curr_text)
                            and not re.match(r"^[（(]\s*\)", curr_text)
                            and prev_text
                            and prev_text[-1] not in ".。！？!?;；:："
                            and not prev_text.endswith("分")
                            and not prev_text.endswith(")")
                            and not prev_text.endswith("）")
                            and not prev_text.endswith("…")
                            and not prev_text.endswith("—")
                        ):
                            if len(prev_text) < 20 and prev_text[-1] in "，,、":
                                pass
                            else:
                                should_merge = True

            if should_merge:
                current_group.append(curr)
            else:
                result.append(self._finalize_raw_line_group(current_group))
                current_group = [curr]

        if current_group:
            result.append(self._finalize_raw_line_group(current_group))

        return result

    def _compute_dominant_gaps(self, raw_lines: list) -> Dict[tuple, float]:
        """计算每个(页面, 栏)的段内基准行间距

        使用P25分位数而非mode，避免小间距文档中mode取到过小值。
        同时过滤掉明显的段间大间距（> font_size * 2.5）。
        """
        gap_groups: Dict[tuple, list] = {}
        font_sizes: Dict[tuple, float] = {}

        for i in range(1, len(raw_lines)):
            prev = raw_lines[i - 1]
            curr = raw_lines[i]

            if prev["page_num"] != curr["page_num"]:
                continue
            if prev.get("column_idx", 0) != curr.get("column_idx", 0):
                continue

            prev_fs = prev["spans"][0]["font_size"] if prev["spans"] else 12
            curr_fs = curr["spans"][0]["font_size"] if curr["spans"] else 12
            if abs(prev_fs - curr_fs) > 1.0:
                continue

            prev_bold = any(s["is_bold"] for s in prev["spans"])
            curr_bold = any(s["is_bold"] for s in curr["spans"])
            if prev_bold != curr_bold:
                continue

            y_gap = curr["y_position"] - prev["y_end"]
            if y_gap > 0:
                key = (prev["page_num"], prev.get("column_idx", 0))
                gap_groups.setdefault(key, []).append(y_gap)
                font_sizes[key] = prev_fs

        result = {}
        for key, gaps in gap_groups.items():
            fs = font_sizes.get(key, 12)
            max_intra = fs * 2.5
            intra_gaps = [g for g in gaps if g <= max_intra]

            if len(intra_gaps) >= 3:
                sorted_gaps = sorted(intra_gaps)
                p50_idx = len(sorted_gaps) // 2
                result[key] = sorted_gaps[p50_idx]
            elif len(intra_gaps) >= 1:
                result[key] = min(intra_gaps)
            else:
                result[key] = fs * 1.2

        return result

    # ================================================================
    # 行分组 → 段落
    # ================================================================

    def _finalize_raw_line_group(self, group: list) -> dict:
        from ..docx.parser import FontInfo, ParagraphFormat, RunInfo

        all_spans = []
        for line in group:
            all_spans.extend(line["spans"])

        full_text = "".join(
            "".join(s["text"] for s in line["spans"]) for line in group
        ).strip()

        first_span = all_spans[0] if all_spans else None
        dominant_span = (
            max(all_spans, key=lambda s: len(s["text"])) if all_spans else None
        )

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
            text_width = avg_x1 - avg_x0
            text_center_ratio = text_width / page_w if page_w > 0 else 0

            if (
                abs(left_m - right_m) < page_w * 0.05
                and left_m > page_w * 0.08
                and text_center_ratio < 0.85
            ):
                alignment = "center"
            elif right_m > left_m * 2.5 and left_m > page_w * 0.25:
                alignment = "right"

        runs = []
        for span in all_spans:
            runs.append(
                RunInfo(
                    text=span["text"],
                    font_name=span["font_name"],
                    font_size=span["font_size"],
                    bold=span["is_bold"],
                    italic=span["is_italic"],
                    color=span["font_color"],
                )
            )

        font_info = FontInfo(
            name=dominant_span["font_name"] if dominant_span else "宋体",
            size=dominant_span["font_size"] if dominant_span else 12.0,
            bold=any(s["is_bold"] for s in all_spans),
            italic=any(s["is_italic"] for s in all_spans),
            color=dominant_span["font_color"] if dominant_span else "000000",
        )

        line_spacing = None
        if len(group) >= 2:
            gaps = []
            for j in range(1, len(group)):
                gap = group[j]["y_position"] - group[j - 1]["y_end"]
                if gap > 0:
                    gaps.append(gap)
            if gaps:
                avg_gap = sum(gaps) / len(gaps)
                font_sz = dominant_span["font_size"] if dominant_span else 12
                line_h = avg_gap + font_sz
                ratio = line_h / font_sz if font_sz > 0 else 1
                if ratio > 1.05:
                    line_spacing = round(ratio, 2)

        left_indent = None
        if page_rect and first_span:
            margin_cm = (first_span["bbox"][0] - page_rect.x0) / 28.35
            if margin_cm > 0.3:
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

    # ================================================================
    # 表格相关
    # ================================================================

    def _collect_table_regions(self) -> list:
        regions = []
        for page_num in range(len(self.doc)):
            tables = self.extract_tables(page_num)
            for table in tables:
                regions.append(
                    {
                        "page_num": page_num,
                        "bbox": table.bbox,
                    }
                )
        return regions

    def _is_in_table_region(
        self,
        page_num: int,
        y_pos: float,
        table_regions: list,
        x_pos: float = -1,
        x_end: float = -1,
    ) -> bool:
        for tr in table_regions:
            if tr["page_num"] != page_num:
                continue
            bbox = tr["bbox"]
            if not bbox or bbox == (0, 0, 0, 0):
                continue
            margin = 5
            if not (bbox[1] - margin <= y_pos <= bbox[3] + margin):
                continue
            if x_pos >= 0 and x_end >= 0:
                para_w = x_end - x_pos
                table_w = bbox[2] - bbox[0]
                overlap_start = max(x_pos, bbox[0])
                overlap_end = min(x_end, bbox[2])
                overlap = max(0, overlap_end - overlap_start)
                if para_w > 0 and overlap / para_w < 0.3:
                    continue
            return True
        return False

    def _extract_meaningful_images(self, page_num: int) -> list:
        all_images = self.extract_images(page_num)
        meaningful = []
        for img in all_images:
            w = img.bbox[2] - img.bbox[0] if img.bbox and len(img.bbox) >= 4 else 0
            h = img.bbox[3] - img.bbox[1] if img.bbox and len(img.bbox) >= 4 else 0
            if w > 20 and h > 20 and len(img.data) > 200:
                meaningful.append(img)
        return meaningful

    def _build_table_cells_with_runs(self, table) -> list:
        from ..docx.parser import TableCellInfo, RunInfo

        cells = []
        for row in table.data:
            cell_row = []
            for cell_text in row:
                cell_row.append(TableCellInfo(text=str(cell_text) if cell_text else ""))
            cells.append(cell_row)
        return cells

    def _build_table_format(self, table) -> "TableFormatInfo":
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

    # ================================================================
    # 辅助方法（向后兼容）
    # ================================================================

    def _group_blocks_by_y(
        self, blocks: List[PDFTextBlock]
    ) -> Dict[int, List[PDFTextBlock]]:
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

    def _assign_raw_lines_to_columns(self, raw_lines: list, columns: list) -> dict:
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

    def _build_line_info(
        self,
        blocks: List[PDFTextBlock],
        page_rect,
        page_num: int,
        column_idx: int,
    ) -> Dict[str, Any]:
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

    def _merge_lines_into_paragraphs(
        self, lines: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
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

            font_changed = abs(
                prev.get("font_size", 12) - curr.get("font_size", 12)
            ) > 1.0 or prev.get("is_bold", False) != curr.get("is_bold", False)

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

    def _handle_hyphenation(
        self, paragraphs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
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

    def _detect_alignment_from_bboxes(self, bboxes: List[Tuple], page_rect) -> str:
        if not bboxes:
            return "left"

        avg_x0 = sum(b[0] for b in bboxes) / len(bboxes)
        avg_x1 = sum(b[2] for b in bboxes) / len(bboxes)
        page_width = (
            page_rect.width
            if hasattr(page_rect, "width")
            else (page_rect[2] - page_rect[0])
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
        return self._detect_alignment_from_bboxes([b.bbox for b in blocks], page_rect)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

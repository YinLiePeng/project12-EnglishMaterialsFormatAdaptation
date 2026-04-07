"""PDF解析器 - 提取PDF内容和样式"""

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
    ext: str  # 图片格式


class PDFParser:
    """PDF解析器"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.doc = fitz.open(str(file_path))

    def close(self):
        """关闭文档"""
        if self.doc:
            self.doc.close()

    def get_page_count(self) -> int:
        """获取页数"""
        return len(self.doc)

    def extract_text_blocks(self, page_num: int) -> List[PDFTextBlock]:
        """提取带样式信息的文本块"""
        if page_num >= len(self.doc):
            return []

        page = self.doc[page_num]
        blocks = page.get_text("dict")
        text_blocks = []

        for block in blocks.get("blocks", []):
            if block.get("type") != 0:  # 只处理文本块
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue

                    # 提取样式信息
                    font_name = span.get("font", "Unknown")
                    font_size = span.get("size", 12)
                    font_color_int = span.get("color", 0)
                    font_color = f"{font_color_int:06x}" if font_color_int else "000000"
                    flags = span.get("flags", 0)

                    # 判断是否加粗、斜体
                    is_bold = bool(flags & 2**4)  # bit 4
                    is_italic = bool(flags & 2**1)  # bit 1

                    # 获取边界框
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
        """提取表格"""
        if page_num >= len(self.doc):
            return []

        page = self.doc[page_num]
        tables = page.find_tables()

        result = []
        for table in tables:
            result.append(
                PDFTable(
                    data=table.extract(),
                    bbox=table.bbox,
                    page_num=page_num,
                    row_count=table.row_count,
                    col_count=table.col_count,
                )
            )

        return result

    def extract_images(self, page_num: int) -> List[PDFImage]:
        """提取图片"""
        if page_num >= len(self.doc):
            return []

        page = self.doc[page_num]
        image_list = page.get_images()

        result = []
        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]
                base_image = self.doc.extract_image(xref)
                if base_image:
                    result.append(
                        PDFImage(
                            data=base_image["image"],
                            bbox=(0, 0, 0, 0),  # 需要更复杂的逻辑获取位置
                            page_num=page_num,
                            ext=base_image.get("ext", "png"),
                        )
                    )
            except Exception as e:
                print(f"提取图片失败: {e}")

        return result

    def detect_columns(self, page_num: int) -> List[Tuple[float, float, float, float]]:
        """检测分栏"""
        if page_num >= len(self.doc):
            return []

        page = self.doc[page_num]
        blocks = page.get_text("blocks")

        if not blocks:
            return [page.rect]  # 返回整个页面

        # 分析blocks的水平位置
        x_positions = []
        for block in blocks:
            if block[6] == 0:  # 只处理文本块
                x_positions.append(block[0])  # x0

        if len(x_positions) < 2:
            return [page.rect]

        # 简单的分栏检测：基于X坐标聚类
        x_positions.sort()
        gaps = []
        for i in range(1, len(x_positions)):
            gap = x_positions[i] - x_positions[i - 1]
            if gap > 50:  # 大于50单位的间隔认为是分栏
                gaps.append((x_positions[i - 1], x_positions[i]))

        if not gaps:
            return [page.rect]

        # 根据间隔创建栏区域
        columns = []
        rect = page.rect
        x_start = rect.x0

        for gap in gaps:
            columns.append((x_start, rect.y0, gap[0], rect.y1))
            x_start = gap[1]

        columns.append((x_start, rect.y0, rect.x1, rect.y1))

        return columns

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
        """提取结构化内容（类似DOCX格式）"""
        content_list = []

        for page_num in range(len(self.doc)):
            text_blocks = self.extract_text_blocks(page_num)

            # 合并同一行的文本块
            lines = {}
            for block in text_blocks:
                y_key = round(block.bbox[1])  # 使用y0作为行标识
                if y_key not in lines:
                    lines[y_key] = {
                        "text": [],
                        "font_sizes": [],
                        "font_names": [],
                        "is_bold": False,
                        "is_center": False,
                    }
                lines[y_key]["text"].append(block.text)
                lines[y_key]["font_sizes"].append(block.font_size)
                lines[y_key]["font_names"].append(block.font_name)
                if block.is_bold:
                    lines[y_key]["is_bold"] = True

            # 转换为段落格式
            for y_key in sorted(lines.keys()):
                line = lines[y_key]
                text = " ".join(line["text"])
                avg_font_size = (
                    sum(line["font_sizes"]) / len(line["font_sizes"])
                    if line["font_sizes"]
                    else 12
                )

                content_list.append(
                    {
                        "text": text,
                        "font_size": avg_font_size,
                        "font_bold": line["is_bold"],
                        "alignment": "left",
                        "page_num": page_num,
                    }
                )

        return content_list

    def convert_to_paragraph_info_list(self) -> List[Dict[str, Any]]:
        """转换为段落信息列表（兼容upload.py调用）"""
        return self.extract_structured_content()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

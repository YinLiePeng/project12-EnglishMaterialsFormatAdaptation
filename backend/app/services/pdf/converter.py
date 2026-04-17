"""PDF转DOCX转换器"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from .parser import PDFParser, PDFTextBlock, PDFTable


class PDFStyleMapper:
    """PDF样式映射器 - 将PDF样式映射为DOCX样式"""

    # 字体映射表
    FONT_MAPPING = {
        "TimesNewRomanPSMT": "Times New Roman",
        "TimesNewRoman": "Times New Roman",
        "Times-Roman": "Times New Roman",
        "ArialMT": "Arial",
        "Arial": "Arial",
        "Helvetica": "Arial",
        "SimSun": "宋体",
        "SimHei": "黑体",
        "KaiTi": "楷体",
        "FangSong": "仿宋",
        "MicrosoftYaHei": "微软雅黑",
    }

    @classmethod
    def map_font(cls, pdf_font: str) -> str:
        """映射PDF字体到DOCX字体"""
        for key, value in cls.FONT_MAPPING.items():
            if key.lower() in pdf_font.lower():
                return value
        return "宋体"  # 默认字体

    @classmethod
    def map_color(cls, pdf_color: str) -> RGBColor:
        """映射PDF颜色到DOCX颜色"""
        try:
            if len(pdf_color) == 6:
                r = int(pdf_color[0:2], 16)
                g = int(pdf_color[2:4], 16)
                b = int(pdf_color[4:6], 16)
                return RGBColor(r, g, b)
        except ValueError:
            pass
        return RGBColor(0, 0, 0)  # 默认黑色

    @classmethod
    def map_paragraph_style(cls, block: PDFTextBlock) -> Dict[str, Any]:
        """映射段落样式"""
        return {
            "font": {
                "name": cls.map_font(block.font_name),
                "size": Pt(block.font_size),
                "bold": block.is_bold,
                "italic": block.is_italic,
                "color": cls.map_color(block.font_color),
            },
            "format": {
                "alignment": WD_ALIGN_PARAGRAPH.LEFT,
                "line_spacing": 1.25,
            },
        }


class PDFToDocxConverter:
    """PDF转DOCX转换器"""

    def __init__(self):
        self.style_mapper = PDFStyleMapper()

    def convert(
        self,
        pdf_path: str,
        output_path: str = None,
        include_tables: bool = True,
        include_images: bool = False,
    ) -> str:
        """将PDF转换为DOCX

        Args:
            pdf_path: PDF文件路径
            output_path: 输出DOCX路径（可选）
            include_tables: 是否包含表格
            include_images: 是否包含图片

        Returns:
            输出文件路径
        """
        pdf_path = Path(pdf_path)
        if not output_path:
            output_path = str(pdf_path.with_suffix(".docx"))

        with PDFParser(str(pdf_path)) as parser:
            doc = Document()

            # 提取内容
            content_list = parser.extract_structured_content()

            # 添加内容到DOCX
            for item in content_list:
                text = item.get("text", "")
                if not text.strip():
                    continue

                font_size = item.get("font_size", 12)
                font_bold = item.get("font_bold", False)

                # 创建段落
                para = doc.add_paragraph(text)

                # 应用样式
                run = para.runs[0] if para.runs else para.add_run(text)
                run.font.size = Pt(font_size)
                run.font.bold = font_bold

            # 添加表格
            if include_tables:
                for page_num in range(parser.get_page_count()):
                    tables = parser.extract_tables(page_num)
                    for table_data in tables:
                        self._add_table_to_docx(doc, table_data)

            # 保存文档
            doc.save(output_path)

        return output_path

    def _add_table_to_docx(self, doc: Document, table_data):
        """添加表格到DOCX"""
        if not table_data.data:
            return

        # 创建表格
        rows = len(table_data.data)
        cols = max(len(row) for row in table_data.data) if table_data.data else 0

        if rows == 0 or cols == 0:
            return

        table = doc.add_table(rows=rows, cols=cols)
        table.style = "Table Grid"

        # 填充表格内容
        for i, row_data in enumerate(table_data.data):
            for j, cell_text in enumerate(row_data):
                if j < cols:
                    table.cell(i, j).text = str(cell_text) if cell_text else ""


def convert_pdf_to_docx(
    pdf_path: str,
    output_path: str = None,
) -> str:
    """便捷函数：将PDF转换为DOCX"""
    converter = PDFToDocxConverter()
    return converter.convert(pdf_path, output_path)

"""PDF解析器 - 基于opendataloader_pdf的JSON输出转换为DOCX

完全替代原有的PyMuPDF/pdfplumber解析方案，使用opendataloader_pdf生成结构化JSON，
然后转换为ContentElement列表供后续处理。
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


@dataclass
class PDFTextBlock:
    """PDF文本块 - 保持向后兼容"""
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
    """PDF表格 - 保持向后兼容"""
    data: List[List[str]]
    bbox: Tuple[float, float, float, float]
    page_num: int
    row_count: int
    col_count: int


@dataclass
class PDFImage:
    """PDF图片 - 保持向后兼容"""
    data: bytes
    bbox: Tuple[float, float, float, float]
    page_num: int
    ext: str


class PDFType:
    """PDF类型枚举 - 保持向后兼容"""
    NATIVE = "native"
    SCANNED = "scanned"
    MIXED = "mixed"


class PDFDetectionResult:
    """PDF检测结果 - 保持向后兼容"""
    def __init__(self, pdf_type, confidence, page_analyses=None, summary=None):
        self.pdf_type = pdf_type if isinstance(pdf_type, str) else pdf_type.value
        self.confidence = confidence
        self.page_analyses = page_analyses or []
        self.summary = summary or {}


class PDFTypeDetector:
    """PDF类型检测器 - opendataloader_pdf解析的PDF都是原生文本型"""
    
    def __init__(self, pdf_parser):
        self.parser = pdf_parser
    
    def detect(self):
        """检测PDF类型 - opendataloader_pdf只处理原生PDF"""
        return PDFDetectionResult(
            pdf_type=PDFType.NATIVE,
            confidence=1.0,
            page_analyses=[],
            summary={
                "type": "native",
                "type_name": "原生可复制PDF",
                "total_pages": self.parser.get_page_count(),
                "processing_hint": "将直接提取文本内容并进行智能排版"
            }
        )


def detect_pdf_type(pdf_parser):
    """便捷函数：检测PDF类型"""
    detector = PDFTypeDetector(pdf_parser)
    return detector.detect()


class FontMapper:
    """PDF字体到DOCX字体映射器"""
    
    FONT_MAPPING = {
        # Times New Roman 系列
        "TimesNewRomanPSMT": "Times New Roman",
        "TimesNewRomanPS-BoldMT": "Times New Roman",
        "TimesNewRomanPS-ItalicMT": "Times New Roman",
        "TimesNewRomanPS-BoldItalicMT": "Times New Roman",
        "TimesNewRoman": "Times New Roman",
        "Times-Roman": "Times New Roman",
        "Times-Bold": "Times New Roman",
        "Times-Italic": "Times New Roman",
        "Times-BoldItalic": "Times New Roman",
        
        # Arial 系列
        "ArialMT": "Arial",
        "Arial-BoldMT": "Arial",
        "Arial-ItalicMT": "Arial",
        "Arial-BoldItalicMT": "Arial",
        "Arial": "Arial",
        "Helvetica": "Arial",
        
        # 中文字体
        "SimSun": "宋体",
        "SimSun-Bold": "宋体",
        "SimSun-ExtB": "宋体",
        "SimHei": "黑体",
        "KaiTi": "楷体",
        "KaiTi_GB2312": "楷体",
        "FangSong": "仿宋",
        "FangSong_GB2312": "仿宋",
        "MicrosoftYaHei": "微软雅黑",
        "MicrosoftYaHei-Bold": "微软雅黑",
        "STSong": "宋体",
        "STHeiti": "黑体",
        "STKaiti": "楷体",
        "STFangsong": "仿宋",
        
        # 其他常见字体
        "CourierNewPSMT": "Courier New",
        "CourierNew": "Courier New",
        "Verdana": "Verdana",
        "Georgia": "Georgia",
        "Tahoma": "Tahoma",
        "Calibri": "Calibri",
        "Calibri-Bold": "Calibri",
        "Cambria": "Cambria",
        "Cambria-Bold": "Cambria",
    }
    
    @classmethod
    def map_font(cls, pdf_font: str) -> str:
        """映射PDF字体到DOCX字体"""
        if not pdf_font:
            return "宋体"
        
        # 直接匹配
        if pdf_font in cls.FONT_MAPPING:
            return cls.FONT_MAPPING[pdf_font]
        
        # 去除子集前缀 (如 AAAAAA+SimSun)
        if "+" in pdf_font:
            pdf_font = pdf_font.split("+", 1)[1]
            if pdf_font in cls.FONT_MAPPING:
                return cls.FONT_MAPPING[pdf_font]
        
        # 模糊匹配
        pdf_font_lower = pdf_font.lower()
        for key, value in cls.FONT_MAPPING.items():
            if key.lower() in pdf_font_lower or pdf_font_lower in key.lower():
                return value
        
        # 默认字体
        return "宋体"
    
    @classmethod
    def is_bold(cls, pdf_font: str) -> bool:
        """判断字体是否为粗体"""
        if not pdf_font:
            return False
        bold_keywords = ["bold", "heavy", "black", "demi"]
        pdf_font_lower = pdf_font.lower()
        return any(kw in pdf_font_lower for kw in bold_keywords)
    
    @classmethod
    def is_italic(cls, pdf_font: str) -> bool:
        """判断字体是否为斜体"""
        if not pdf_font:
            return False
        italic_keywords = ["italic", "oblique", "slant"]
        pdf_font_lower = pdf_font.lower()
        return any(kw in pdf_font_lower for kw in italic_keywords)


class ColorConverter:
    """颜色转换器"""
    
    @classmethod
    def parse_rgb(cls, color_str: str) -> Optional[RGBColor]:
        """解析JSON中的颜色字符串 [R, G, B]"""
        if not color_str:
            return RGBColor(0, 0, 0)
        
        try:
            # 处理 [0.0, 0.0, 0.0] 格式
            match = re.match(r'\[\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\]', color_str)
            if match:
                r = int(float(match.group(1)) * 255)
                g = int(float(match.group(2)) * 255)
                b = int(float(match.group(3)) * 255)
                return RGBColor(r, g, b)
            
            # 处理 6位16进制格式
            color_str = color_str.strip('#')
            if len(color_str) == 6:
                r = int(color_str[0:2], 16)
                g = int(color_str[2:4], 16)
                b = int(color_str[4:6], 16)
                return RGBColor(r, g, b)
        except (ValueError, IndexError):
            pass
        
        return RGBColor(0, 0, 0)


class AlignmentDetector:
    """对齐方式检测器"""
    
    @classmethod
    def detect_from_bbox(cls, bbox: List[float], page_width: float = 595.0) -> str:
        """根据bounding box检测对齐方式"""
        if not bbox or len(bbox) < 4:
            return "left"
        
        x1, y1, x2, y2 = bbox
        element_width = x2 - x1
        left_margin = x1
        right_margin = page_width - x2
        
        # 居中对齐：左右边距大致相等，且元素宽度小于页面宽度的80%
        if abs(left_margin - right_margin) < page_width * 0.1 and element_width < page_width * 0.8:
            return "center"
        
        # 右对齐：右边距明显小于左边距
        if right_margin < left_margin * 0.5 and left_margin > page_width * 0.2:
            return "right"
        
        # 两端对齐：元素宽度接近页面宽度
        if element_width > page_width * 0.85:
            return "justify"
        
        # 默认左对齐
        return "left"
    
    @classmethod
    def get_wd_align(cls, alignment: str):
        """获取docx对齐常量"""
        mapping = {
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
            "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        }
        return mapping.get(alignment, WD_ALIGN_PARAGRAPH.LEFT)


class PDFParser:
    """PDF解析器 - 基于opendataloader_pdf的JSON输出
    
    完全替代原有的PyMuPDF/pdfplumber解析方案。
    """
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.json_data = None
        self.json_path = None
        self.images_dir = None
        self._load_json()
    
    def _load_json(self):
        """加载opendataloader_pdf生成的JSON文件"""
        # 尝试查找同名的JSON文件
        json_path = self.file_path.with_suffix('.json')
        if json_path.exists():
            self.json_path = json_path
            with open(json_path, 'r', encoding='utf-8') as f:
                self.json_data = json.load(f)
        
        # 查找图片目录
        images_dir = Path(str(self.file_path.with_suffix('')) + '_images')
        if images_dir.exists():
            self.images_dir = images_dir
    
    def close(self):
        """关闭解析器"""
        pass
    
    def get_page_count(self) -> int:
        """获取页面数量"""
        if self.json_data:
            return self.json_data.get('number of pages', 0)
        return 0
    
    def extract_text_blocks(self, page_num: int) -> List[PDFTextBlock]:
        """提取带样式信息的文本块 - 保持向后兼容"""
        blocks = []
        if not self.json_data:
            return blocks
        
        for element in self.json_data.get('kids', []):
            if element.get('page number') == page_num and element.get('type') in ['paragraph', 'heading']:
                bbox = element.get('bounding box', [0, 0, 0, 0])
                blocks.append(PDFTextBlock(
                    text=element.get('content', ''),
                    font_name=element.get('font', ''),
                    font_size=element.get('font size', 12),
                    font_color=element.get('text color', ''),
                    is_bold=FontMapper.is_bold(element.get('font', '')),
                    is_italic=FontMapper.is_italic(element.get('font', '')),
                    bbox=tuple(bbox) if len(bbox) == 4 else (0, 0, 0, 0),
                    page_num=page_num
                ))
        
        return blocks
    
    def extract_tables(self, page_num: int) -> List[PDFTable]:
        """提取表格 - 保持向后兼容"""
        tables = []
        if not self.json_data:
            return tables
        
        for element in self.json_data.get('kids', []):
            if element.get('page number') == page_num and element.get('type') == 'table':
                bbox = element.get('bounding box', [0, 0, 0, 0])
                rows_data = []
                for row in element.get('rows', []):
                    row_data = []
                    for cell in row.get('cells', []):
                        cell_text = self._extract_cell_text(cell)
                        row_data.append(cell_text)
                    rows_data.append(row_data)
                
                tables.append(PDFTable(
                    data=rows_data,
                    bbox=tuple(bbox) if len(bbox) == 4 else (0, 0, 0, 0),
                    page_num=page_num,
                    row_count=element.get('number of rows', 0),
                    col_count=element.get('number of columns', 0)
                ))
        
        return tables
    
    def _extract_cell_text(self, cell: Dict) -> str:
        """提取单元格文本"""
        texts = []
        for kid in cell.get('kids', []):
            if kid.get('type') in ['paragraph', 'heading']:
                texts.append(kid.get('content', ''))
            elif kid.get('type') == 'list':
                for item in kid.get('list items', []):
                    texts.append(item.get('content', ''))
            elif kid.get('type') == 'image':
                texts.append('[图片]')
        return '\n'.join(texts)
    
    def _extract_cell_runs(self, cell: Dict) -> list:
        """提取单元格中的runs信息（保留字体格式）"""
        from ..docx.parser import RunInfo
        runs = []
        for kid in cell.get('kids', []):
            if kid.get('type') in ['paragraph', 'heading']:
                run_info = RunInfo(
                    text=kid.get('content', ''),
                    font_name=FontMapper.map_font(kid.get('font', '')),
                    font_size=round(kid.get('font size', 12), 1),
                    bold=FontMapper.is_bold(kid.get('font', '')),
                    italic=FontMapper.is_italic(kid.get('font', '')),
                    color=kid.get('text color', ''),
                )
                runs.append(run_info)
            elif kid.get('type') == 'list':
                for item in kid.get('list items', []):
                    run_info = RunInfo(
                        text=item.get('content', ''),
                        font_name=FontMapper.map_font(item.get('font', '')),
                        font_size=round(item.get('font size', 12), 1),
                        bold=FontMapper.is_bold(item.get('font', '')),
                        italic=FontMapper.is_italic(item.get('font', '')),
                        color=item.get('text color', ''),
                    )
                    runs.append(run_info)
        return runs
    
    def extract_images(self, page_num: int) -> List[PDFImage]:
        """提取图片 - 保持向后兼容"""
        images = []
        if not self.json_data or not self.images_dir:
            return images
        
        for element in self.json_data.get('kids', []):
            if element.get('page number') == page_num and element.get('type') == 'image':
                source = element.get('source', '')
                if source:
                    img_path = self.images_dir / Path(source).name
                    if img_path.exists():
                        with open(img_path, 'rb') as f:
                            img_data = f.read()
                        
                        bbox = element.get('bounding box', [0, 0, 0, 0])
                        images.append(PDFImage(
                            data=img_data,
                            bbox=tuple(bbox) if len(bbox) == 4 else (0, 0, 0, 0),
                            page_num=page_num,
                            ext=img_path.suffix.lstrip('.') or 'png'
                        ))
        
        return images
    
    def extract_all_text(self) -> str:
        """提取所有页面的文本"""
        texts = []
        if not self.json_data:
            return ''
        
        for element in self.json_data.get('kids', []):
            if element.get('type') in ['paragraph', 'heading']:
                texts.append(element.get('content', ''))
        
        return '\n'.join(texts)
    
    def extract_structured_content(self) -> List[Dict[str, Any]]:
        """提取结构化内容（向后兼容）"""
        content_list = []
        if not self.json_data:
            return content_list
        
        for element in self.json_data.get('kids', []):
            if element.get('type') in ['paragraph', 'heading']:
                bbox = element.get('bounding box', [0, 0, 0, 0])
                alignment = AlignmentDetector.detect_from_bbox(bbox)
                
                content_list.append({
                    'text': element.get('content', ''),
                    'font_name': FontMapper.map_font(element.get('font', '')),
                    'font_size': element.get('font size', 12),
                    'font_bold': FontMapper.is_bold(element.get('font', '')),
                    'font_italic': FontMapper.is_italic(element.get('font', '')),
                    'font_color': element.get('text color', ''),
                    'alignment': alignment,
                    'page_num': element.get('page number', 0),
                })
        
        return content_list
    
    def convert_to_paragraph_info_list(self) -> List[Dict[str, Any]]:
        """转换为段落信息列表（向后兼容）"""
        return self.extract_structured_content()
    
    def convert_to_content_elements(self) -> list:
        """将PDF内容转换为ContentElement列表
        
        这是核心方法，生成与原有解析器兼容的ContentElement列表。
        """
        from ..docx.parser import (
            ContentElement, ElementType, ParagraphInfo, 
            FontInfo, ParagraphFormat, TableCellInfo, TableFormatInfo, RunInfo
        )
        
        elements = []
        if not self.json_data:
            return elements
        
        original_index = 0
        
        # 获取所有元素并按页面和Y坐标排序
        all_elements = self.json_data.get('kids', [])
        
        # 过滤掉header/footer中的元素，避免重复
        filtered_elements = []
        header_footer_ids = set()
        
        for elem in all_elements:
            if elem.get('type') in ['header', 'footer']:
                for kid in elem.get('kids', []):
                    header_footer_ids.add(kid.get('id'))
        
        for elem in all_elements:
            if elem.get('id') in header_footer_ids:
                continue
            if elem.get('type') in ['header', 'footer']:
                continue
            filtered_elements.append(elem)
        
        # 按页面和Y坐标排序（PDF坐标系Y从底部开始，所以用-y排序）
        filtered_elements.sort(key=lambda e: (
            e.get('page number', 0),
            -(e.get('bounding box', [0, 0, 0, 0])[1] if len(e.get('bounding box', [])) >= 2 else 0)
        ))
        
        for element in filtered_elements:
            elem_type = element.get('type')
            
            if elem_type in ['paragraph', 'heading']:
                # 处理段落和标题
                bbox = element.get('bounding box', [0, 0, 0, 0])
                alignment = AlignmentDetector.detect_from_bbox(bbox)
                
                font_info = FontInfo(
                    name=FontMapper.map_font(element.get('font', '')),
                    size=round(element.get('font size', 12), 1),
                    bold=FontMapper.is_bold(element.get('font', '')),
                    italic=FontMapper.is_italic(element.get('font', '')),
                    color=element.get('text color', ''),
                )
                
                format_info = ParagraphFormat(alignment=alignment)
                
                # 标题使用对应的style_name
                style_name = 'Normal'
                if elem_type == 'heading':
                    heading_level = element.get('heading level', 1)
                    if heading_level == 1:
                        style_name = 'Heading 1'
                    elif heading_level == 2:
                        style_name = 'Heading 2'
                    elif heading_level == 3:
                        style_name = 'Heading 3'
                    elif heading_level == 4:
                        style_name = 'Heading 4'
                
                # 创建RunInfo，将段落文本和字体信息包装成run
                run_info = RunInfo(
                    text=element.get('content', ''),
                    font_name=font_info.name,
                    font_size=font_info.size,
                    bold=font_info.bold,
                    italic=font_info.italic,
                    color=font_info.color,
                )
                
                para_info = ParagraphInfo(
                    index=original_index,
                    text=element.get('content', ''),
                    style_name=style_name,
                    font=font_info,
                    format=format_info,
                    runs=[run_info],
                )
                
                elements.append(ContentElement(
                    element_type=ElementType.PARAGRAPH,
                    original_index=original_index,
                    paragraph=para_info,
                ))
                original_index += 1
            
            elif elem_type == 'table':
                # 处理表格
                table_cells = []
                for row in element.get('rows', []):
                    cell_row = []
                    for cell in row.get('cells', []):
                        cell_text = self._extract_cell_text(cell)
                        cell_runs = self._extract_cell_runs(cell)
                        cell_row.append(TableCellInfo(
                            text=cell_text,
                            runs=cell_runs,
                            paragraph_runs=[cell_runs] if cell_runs else [],
                        ))
                    table_cells.append(cell_row)
                
                # 提取表格格式信息
                column_widths = []
                row_heights = []
                
                # 尝试从JSON中提取列宽
                if 'columns' in element:
                    for col in element.get('columns', []):
                        width = col.get('width', 0)
                        if width:
                            # 转换为厘米（假设PDF单位是点，1点=0.0352778厘米）
                            column_widths.append(round(width * 0.0352778, 2))
                
                # 尝试从JSON中提取行高
                for row in element.get('rows', []):
                    height = row.get('height', 0)
                    if height:
                        row_heights.append(round(height * 0.0352778, 2))
                
                table_format = TableFormatInfo(
                    column_widths=column_widths,
                    row_heights=row_heights,
                    alignment='left',
                )
                
                elements.append(ContentElement(
                    element_type=ElementType.TABLE,
                    original_index=original_index,
                    table_cells=table_cells,
                    table_format=table_format,
                ))
                original_index += 1
            
            elif elem_type == 'image':
                # 处理图片
                source = element.get('source', '')
                if source and self.images_dir:
                    img_path = self.images_dir / Path(source).name
                    if img_path.exists():
                        with open(img_path, 'rb') as f:
                            img_data = f.read()
                        
                        # 跳过1x1像素的装饰性图片
                        if len(img_data) > 100:  # 简单启发式：小于100字节的可能是装饰
                            # 从bounding box提取图片尺寸（转换为EMU单位，1点=12700 EMU）
                            bbox = element.get('bounding box', [0, 0, 0, 0])
                            width_pt = bbox[2] - bbox[0] if len(bbox) >= 4 else 0
                            height_pt = bbox[3] - bbox[1] if len(bbox) >= 4 else 0
                            width_emu = int(width_pt * 12700) if width_pt > 0 else None
                            height_emu = int(height_pt * 12700) if height_pt > 0 else None
                            
                            elements.append(ContentElement(
                                element_type=ElementType.IMAGE,
                                original_index=original_index,
                                image_data=img_data,
                                image_ext=img_path.suffix.lstrip('.') or 'png',
                                image_width=width_emu,
                                image_height=height_emu,
                            ))
                            original_index += 1
            
            elif elem_type == 'list':
                # 递归处理列表及其嵌套元素
                original_index = self._process_list_element(
                    element, elements, original_index, level=0
                )
        
        return elements
    
    def _process_list_element(self, list_element: Dict, elements: list, 
                              original_index: int, level: int = 0) -> int:
        """递归处理列表元素，包括嵌套列表
        
        Args:
            list_element: 列表元素
            elements: 目标元素列表
            original_index: 当前索引
            level: 嵌套层级（用于缩进）
            
        Returns:
            更新后的索引
        """
        from ..docx.parser import (
            ContentElement, ElementType, ParagraphInfo, 
            FontInfo, ParagraphFormat, RunInfo
        )
        list_items = list_element.get('list items', [])
        numbering_style = list_element.get('numbering style', 'unordered')
        
        for i, item in enumerate(list_items):
            bbox = item.get('bounding box', [0, 0, 0, 0])
            alignment = AlignmentDetector.detect_from_bbox(bbox)
            
            # 构建列表项文本
            content = item.get('content', '')
            if numbering_style == 'arabic numbers':
                if not content or not re.match(r'^\d+[\.\)\\、\s]', content):
                    content = f"{i + 1}. {content}"
            elif numbering_style == 'unordered':
                if not content or not content.startswith(('•', '-', '*', '○', '·')):
                    content = f"• {content}"
            
            # 添加缩进（根据层级）
            indent = "    " * level
            if indent:
                content = indent + content
            
            font_info = FontInfo(
                name=FontMapper.map_font(item.get('font', '')),
                size=round(item.get('font size', 12), 1),
                bold=FontMapper.is_bold(item.get('font', '')),
                italic=FontMapper.is_italic(item.get('font', '')),
                color=item.get('text color', ''),
            )
            
            format_info = ParagraphFormat(alignment=alignment)
            
            # 创建RunInfo
            list_run_info = RunInfo(
                text=content,
                font_name=font_info.name,
                font_size=font_info.size,
                bold=font_info.bold,
                italic=font_info.italic,
                color=font_info.color,
            )
            
            para_info = ParagraphInfo(
                index=original_index,
                text=content,
                style_name='List Paragraph',
                font=font_info,
                format=format_info,
                runs=[list_run_info],
            )
            
            elements.append(ContentElement(
                element_type=ElementType.PARAGRAPH,
                original_index=original_index,
                paragraph=para_info,
            ))
            original_index += 1
            
            # 递归处理列表项中的嵌套元素（仅处理有独立内容的元素）
            for kid in item.get('kids', []):
                kid_type = kid.get('type')
                kid_content = kid.get('content', '').strip()
                
                # 如果kid有自己的内容（不在父item.content中），则单独处理
                if kid_content and kid_content not in content:
                    if kid_type == 'paragraph':
                        original_index = self._process_paragraph_element(
                            kid, elements, original_index, level=level + 1
                        )
                    elif kid_type == 'list':
                        # 递归处理嵌套列表
                        original_index = self._process_list_element(
                            kid, elements, original_index, level=level + 1
                        )
                    elif kid_type == 'heading':
                        original_index = self._process_heading_element(
                            kid, elements, original_index, level=level + 1
                        )
        
        return original_index
    
    def _process_paragraph_element(self, element: Dict, elements: list,
                                   original_index: int, level: int = 0) -> int:
        """处理段落元素
        
        Args:
            element: 段落元素
            elements: 目标元素列表
            original_index: 当前索引
            level: 嵌套层级
            
        Returns:
            更新后的索引
        """
        from ..docx.parser import (
            ContentElement, ElementType, ParagraphInfo, 
            FontInfo, ParagraphFormat, RunInfo
        )
        bbox = element.get('bounding box', [0, 0, 0, 0])
        alignment = AlignmentDetector.detect_from_bbox(bbox)
        
        content = element.get('content', '')
        # 添加缩进
        indent = "    " * level
        if indent and content:
            content = indent + content
        
        font_info = FontInfo(
            name=FontMapper.map_font(element.get('font', '')),
            size=round(element.get('font size', 12), 1),
            bold=FontMapper.is_bold(element.get('font', '')),
            italic=FontMapper.is_italic(element.get('font', '')),
            color=element.get('text color', ''),
        )
        
        run_info = RunInfo(
            text=content,
            font_name=font_info.name,
            font_size=font_info.size,
            bold=font_info.bold,
            italic=font_info.italic,
            color=font_info.color,
        )
        
        para_info = ParagraphInfo(
            index=original_index,
            text=content,
            style_name='Normal',
            font=font_info,
            format=ParagraphFormat(alignment=alignment),
            runs=[run_info],
        )
        
        elements.append(ContentElement(
            element_type=ElementType.PARAGRAPH,
            original_index=original_index,
            paragraph=para_info,
        ))
        return original_index + 1
    
    def _process_heading_element(self, element: Dict, elements: list,
                                 original_index: int, level: int = 0) -> int:
        """处理标题元素
        
        Args:
            element: 标题元素
            elements: 目标元素列表
            original_index: 当前索引
            level: 嵌套层级
            
        Returns:
            更新后的索引
        """
        from ..docx.parser import (
            ContentElement, ElementType, ParagraphInfo, 
            FontInfo, ParagraphFormat, RunInfo
        )
        bbox = element.get('bounding box', [0, 0, 0, 0])
        alignment = AlignmentDetector.detect_from_bbox(bbox)
        
        content = element.get('content', '')
        indent = "    " * level
        if indent and content:
            content = indent + content
        
        heading_level = element.get('heading level', 1)
        style_name = 'Heading 1'
        if heading_level == 2:
            style_name = 'Heading 2'
        elif heading_level == 3:
            style_name = 'Heading 3'
        elif heading_level == 4:
            style_name = 'Heading 4'
        
        font_info = FontInfo(
            name=FontMapper.map_font(element.get('font', '')),
            size=round(element.get('font size', 12), 1),
            bold=FontMapper.is_bold(element.get('font', '')),
            italic=FontMapper.is_italic(element.get('font', '')),
            color=element.get('text color', ''),
        )
        
        run_info = RunInfo(
            text=content,
            font_name=font_info.name,
            font_size=font_info.size,
            bold=font_info.bold,
            italic=font_info.italic,
            color=font_info.color,
        )
        
        para_info = ParagraphInfo(
            index=original_index,
            text=content,
            style_name=style_name,
            font=font_info,
            format=ParagraphFormat(alignment=alignment),
            runs=[run_info],
        )
        
        elements.append(ContentElement(
            element_type=ElementType.PARAGRAPH,
            original_index=original_index,
            paragraph=para_info,
        ))
        return original_index + 1
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class PDFToDocxConverter:
    """PDF转DOCX转换器 - 基于opendataloader_pdf JSON"""
    
    def __init__(self):
        pass
    
    def convert(self, pdf_path: str, output_path: str = None, **kwargs) -> str:
        """将PDF转换为DOCX"""
        pdf_path = Path(pdf_path)
        if not output_path:
            output_path = str(pdf_path.with_suffix('.docx'))
        
        # 首先调用opendataloader_pdf生成JSON（如果还没有）
        json_path = pdf_path.with_suffix('.json')
        if not json_path.exists():
            import opendataloader_pdf
            opendataloader_pdf.convert(
                input_path=[str(pdf_path)],
                output_dir=str(pdf_path.parent),
                format="json"
            )
        
        # 使用JSON生成DOCX
        parser = PDFParser(str(pdf_path))
        elements = parser.convert_to_content_elements()
        
        # 使用DocxGenerator生成文档
        from ..docx.generator import DocxGenerator
        generator = DocxGenerator()
        
        # 构建样式映射（保留原格式）
        style_mapping = {}
        style_keys = {}
        
        for i, elem in enumerate(elements):
            if elem.element_type.name == 'PARAGRAPH' and elem.paragraph:
                style_keys[i] = 'body'
        
        generator.generate_from_elements(
            elements, 
            style_mapping, 
            style_keys, 
            preserve_format=True
        )
        generator.save(output_path)
        
        return output_path


def convert_pdf_to_docx(pdf_path: str, output_path: str = None) -> str:
    """便捷函数：将PDF转换为DOCX"""
    converter = PDFToDocxConverter()
    return converter.convert(pdf_path, output_path)

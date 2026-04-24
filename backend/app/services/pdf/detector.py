"""PDF类型检测器 - 自动判断原生/扫描/混合PDF

对于opendataloader_pdf解析的PDF，统一视为原生文本型PDF
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional


class PDFType(Enum):
    NATIVE = "native"
    SCANNED = "scanned"
    MIXED = "mixed"


@dataclass
class PageAnalysis:
    page_num: int
    pdf_type: PDFType
    text_char_count: int
    image_area_ratio: float
    text_block_count: int
    image_count: int
    confidence: float


@dataclass
class PDFDetectionResult:
    pdf_type: PDFType
    confidence: float
    page_analyses: List[PageAnalysis]
    summary: Dict[str, Any]


class PDFTypeDetector:
    """PDF类型检测器
    
    opendataloader_pdf只处理原生文本型PDF，所以统一返回native类型
    """
    
    def __init__(self, pdf_parser):
        self.parser = pdf_parser
    
    def detect(self) -> PDFDetectionResult:
        """检测PDF类型"""
        page_count = self.parser.get_page_count()
        
        # opendataloader_pdf处理的都是原生PDF
        summary = {
            "type": "native",
            "type_name": "原生可复制PDF",
            "total_pages": page_count,
            "total_text_chars": 0,
            "avg_chars_per_page": 0,
            "native_pages": page_count,
            "scanned_pages": 0,
            "processing_hint": "将直接提取文本内容并进行智能排版"
        }
        
        return PDFDetectionResult(
            pdf_type=PDFType.NATIVE,
            confidence=1.0,
            page_analyses=[],
            summary=summary,
        )


def detect_pdf_type(pdf_parser) -> PDFDetectionResult:
    """便捷函数：检测PDF类型"""
    detector = PDFTypeDetector(pdf_parser)
    return detector.detect()

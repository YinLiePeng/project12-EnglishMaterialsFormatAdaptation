"""PDF类型检测器 - 自动判断原生/扫描/混合PDF"""

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

    通过分析每页的文本量和图片覆盖率判断PDF类型：
    - native: 文本丰富，图片少（正常电子版PDF）
    - scanned: 文本极少或无，大面积图片（扫描件）
    - mixed: 部分页面是原生，部分是扫描
    """

    TEXT_THRESHOLD_CHARS = 50
    IMAGE_AREA_THRESHOLD = 0.5
    NATIVE_PAGE_MIN_CHARS = 100
    SCANDED_PAGE_MAX_CHARS = 30

    def __init__(self, pdf_parser):
        self.parser = pdf_parser

    def detect(self) -> PDFDetectionResult:
        """检测PDF类型"""
        page_count = self.parser.get_page_count()
        page_analyses = []

        for page_num in range(page_count):
            analysis = self._analyze_page(page_num)
            page_analyses.append(analysis)

        overall_type, confidence = self._classify_overall(page_analyses)
        summary = self._build_summary(page_analyses, overall_type)

        return PDFDetectionResult(
            pdf_type=overall_type,
            confidence=confidence,
            page_analyses=page_analyses,
            summary=summary,
        )

    def _analyze_page(self, page_num: int) -> PageAnalysis:
        """分析单个页面的类型"""
        import fitz

        doc = self.parser.doc
        if page_num >= len(doc):
            return PageAnalysis(
                page_num=page_num,
                pdf_type=PDFType.NATIVE,
                text_char_count=0,
                image_area_ratio=0.0,
                text_block_count=0,
                image_count=0,
                confidence=0.0,
            )

        page = doc[page_num]
        page_area = page.rect.width * page.rect.height

        text = page.get_text("text")
        text_char_count = len(text.strip())

        blocks = page.get_text("dict")
        text_block_count = 0
        for block in blocks.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if span.get("text", "").strip():
                            text_block_count += 1

        image_list = page.get_images()
        image_count = len(image_list)

        image_area = 0.0
        for img in image_list:
            try:
                xref = img[0]
                rects = page.get_image_rects(xref)
                for r in rects:
                    image_area += r.width * r.height
            except Exception:
                pass

        image_area_ratio = image_area / page_area if page_area > 0 else 0.0

        page_type, confidence = self._classify_page(
            text_char_count, image_area_ratio, text_block_count, image_count
        )

        return PageAnalysis(
            page_num=page_num,
            pdf_type=page_type,
            text_char_count=text_char_count,
            image_area_ratio=round(image_area_ratio, 3),
            text_block_count=text_block_count,
            image_count=image_count,
            confidence=confidence,
        )

    def _classify_page(
        self,
        text_chars: int,
        image_ratio: float,
        text_blocks: int,
        image_count: int,
    ) -> tuple:
        """分类单个页面"""
        if text_chars >= self.NATIVE_PAGE_MIN_CHARS and text_blocks >= 5:
            if image_ratio < self.IMAGE_AREA_THRESHOLD:
                return PDFType.NATIVE, 0.9
            else:
                return PDFType.NATIVE, 0.7

        if text_chars <= self.SCANDED_PAGE_MAX_CHARS and image_count > 0:
            return PDFType.SCANNED, 0.9

        if text_chars <= self.TEXT_THRESHOLD_CHARS and image_ratio > 0.3:
            return PDFType.SCANNED, 0.85

        if text_chars > self.TEXT_THRESHOLD_CHARS and text_blocks > 2:
            return PDFType.NATIVE, 0.8

        if image_count > 0 and text_blocks < 3:
            return PDFType.SCANNED, 0.75

        return PDFType.NATIVE, 0.5

    def _classify_overall(
        self, page_analyses: List[PageAnalysis]
    ) -> tuple:
        """综合所有页面分析，判断整体PDF类型"""
        if not page_analyses:
            return PDFType.NATIVE, 0.5

        native_count = sum(1 for p in page_analyses if p.pdf_type == PDFType.NATIVE)
        scanned_count = sum(1 for p in page_analyses if p.pdf_type == PDFType.SCANNED)

        total = len(page_analyses)

        if native_count == total:
            avg_conf = sum(p.confidence for p in page_analyses) / total
            return PDFType.NATIVE, round(avg_conf, 2)

        if scanned_count == total:
            avg_conf = sum(p.confidence for p in page_analyses) / total
            return PDFType.SCANNED, round(avg_conf, 2)

        if scanned_count > native_count:
            return PDFType.SCANNED, 0.7

        return PDFType.MIXED, 0.75

    def _build_summary(
        self, page_analyses: List[PageAnalysis], overall_type: PDFType
    ) -> Dict[str, Any]:
        """构建检测摘要"""
        type_names = {
            PDFType.NATIVE: "原生可复制PDF",
            PDFType.SCANNED: "扫描版PDF",
            PDFType.MIXED: "混合型PDF",
        }

        total_chars = sum(p.text_char_count for p in page_analyses)
        avg_chars = total_chars / len(page_analyses) if page_analyses else 0

        return {
            "type": overall_type.value,
            "type_name": type_names.get(overall_type, "未知"),
            "total_pages": len(page_analyses),
            "total_text_chars": total_chars,
            "avg_chars_per_page": round(avg_chars, 1),
            "native_pages": sum(1 for p in page_analyses if p.pdf_type == PDFType.NATIVE),
            "scanned_pages": sum(1 for p in page_analyses if p.pdf_type == PDFType.SCANNED),
            "processing_hint": self._get_processing_hint(overall_type),
        }

    def _get_processing_hint(self, pdf_type: PDFType) -> str:
        """获取处理提示"""
        hints = {
            PDFType.NATIVE: "将直接提取文本内容并进行智能排版",
            PDFType.SCANNED: "将使用OCR识别图片中的文字内容",
            PDFType.MIXED: "将混合使用文本提取和OCR识别",
        }
        return hints.get(pdf_type, "")


def detect_pdf_type(pdf_parser) -> PDFDetectionResult:
    """便捷函数：检测PDF类型"""
    detector = PDFTypeDetector(pdf_parser)
    return detector.detect()

"""OCR处理流水线 - 扫描版PDF处理

流程：PDF页面渲染 → OCR识别 → 文本结构化 → ContentElement转换
"""

from typing import List, Optional

from . import BaseOCRService, OCRResult, get_ocr_service
from ..pdf.detector import PDFType, PDFDetectionResult


async def process_scanned_pdf(
    pdf_path: str,
    pdf_detection: Optional[PDFDetectionResult] = None,
    ocr_service: Optional[BaseOCRService] = None,
    progress_callback=None,
) -> list:
    """处理扫描版PDF：OCR识别 → ContentElement列表

    Args:
        pdf_path: PDF文件路径
        pdf_detection: PDF类型检测结果（可选，用于混合PDF的页面级路由）
        ocr_service: OCR服务实例（可选，默认使用配置的引擎）
        progress_callback: 进度回调函数 async callback(page, total, message)

    Returns:
        ContentElement列表
    """
    if ocr_service is None:
        ocr_service = get_ocr_service()

    scanned_pages = None
    if pdf_detection:
        scanned_pages = [
            p.page_num
            for p in pdf_detection.page_analyses
            if p.pdf_type == PDFType.SCANNED
        ]

    if progress_callback:
        await progress_callback(0, 0, f"正在使用{ocr_service.get_name()}识别PDF内容...")

    ocr_result = await ocr_service.recognize_pdf(pdf_path, page_range=scanned_pages)

    if not ocr_result.total_text.strip():
        return []

    if progress_callback:
        await progress_callback(0, 0, "OCR识别完成，正在结构化处理...")

    elements = _ocr_result_to_content_elements(ocr_result)

    return elements


def _ocr_result_to_content_elements(ocr_result: OCRResult) -> list:
    """将OCR识别结果转换为ContentElement列表"""
    from ..docx.parser import (
        ContentElement,
        ElementType,
        ParagraphInfo,
        FontInfo,
        ParagraphFormat,
    )

    elements = []
    original_index = 0

    for page in ocr_result.pages:
        if not page.text.strip():
            continue

        paragraphs = page.text.split("\n\n")

        for para_text in paragraphs:
            para_text = para_text.strip()
            if not para_text:
                continue

            lines = para_text.split("\n")
            lines = [l.strip() for l in lines if l.strip()]
            merged_text = " ".join(lines)

            if not merged_text:
                continue

            font_info = FontInfo(
                name="宋体",
                size=12.0,
            )

            format_info = ParagraphFormat(alignment="left")

            para_info = ParagraphInfo(
                index=original_index,
                text=merged_text,
                style_name="Normal",
                font=font_info,
                format=format_info,
            )

            elements.append(
                ContentElement(
                    element_type=ElementType.PARAGRAPH,
                    original_index=original_index,
                    paragraph=para_info,
                )
            )
            original_index += 1

    return elements

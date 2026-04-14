import pytest
from conftest import get_native_pdfs, get_image_pdfs, native_pdf_path, image_pdf_path


NATIVE_PDFS = get_native_pdfs()
IMAGE_PDFS = get_image_pdfs()


def test_detect_native_pdf():
    """测试原生PDF被正确检测为native类型"""
    from app.services.pdf.parser import PDFParser
    from app.services.pdf.detector import PDFType, detect_pdf_type

    for fname in NATIVE_PDFS[:5]:
        path = native_pdf_path(fname)
        parser = PDFParser(path)
        result = detect_pdf_type(parser)
        parser.close()

        assert result.pdf_type == PDFType.NATIVE, \
            f"{fname[:40]} 应为native, 实际={result.pdf_type.value}, 置信度={result.confidence}"
        assert result.confidence > 0.5
        assert result.summary["total_pages"] > 0
        assert result.summary["total_text_chars"] > 0


def test_detect_scanned_pdf():
    """测试图片型PDF被正确检测为scanned类型"""
    from app.services.pdf.parser import PDFParser
    from app.services.pdf.detector import PDFType, detect_pdf_type

    for fname in IMAGE_PDFS[:5]:
        path = image_pdf_path(fname)
        parser = PDFParser(path)
        result = detect_pdf_type(parser)
        parser.close()

        assert result.pdf_type == PDFType.SCANNED, \
            f"{fname[:40]} 应为scanned, 实际={result.pdf_type.value}, 置信度={result.confidence}"
        assert result.summary["avg_chars_per_page"] < 100, \
            f"扫描PDF每页平均字符应<100, 实际={result.summary['avg_chars_per_page']}"


def test_detection_result_structure():
    """测试检测结果结构完整性"""
    from app.services.pdf.parser import PDFParser
    from app.services.pdf.detector import detect_pdf_type

    path = native_pdf_path(NATIVE_PDFS[0])
    parser = PDFParser(path)
    result = detect_pdf_type(parser)
    parser.close()

    assert result.pdf_type is not None
    assert 0 <= result.confidence <= 1.0
    assert len(result.page_analyses) > 0
    assert "type" in result.summary
    assert "type_name" in result.summary
    assert "processing_hint" in result.summary
    assert "total_pages" in result.summary

    for pa in result.page_analyses:
        assert pa.page_num >= 0
        assert 0 <= pa.confidence <= 1.0

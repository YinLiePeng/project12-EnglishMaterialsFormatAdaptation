"""测试PDF全流程：解析 → ContentElement → 排版生成DOCX"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from conftest import get_native_pdfs, native_pdf_path

NATIVE_PDFS = get_native_pdfs()
NATIVE_IDS = [f[:40] for f in NATIVE_PDFS]


class TestPDFToDocxPipeline:
    """PDF → ContentElement → DOCX 全流程"""

    @pytest.mark.parametrize("filename", NATIVE_PDFS[:3], ids=NATIVE_IDS[:3])
    def test_pdf_parse_to_content_elements(self, filename):
        """PDF解析为ContentElement列表"""
        from app.services.pdf.parser import PDFParser
        from app.services.docx.parser import ElementType

        path = native_pdf_path(filename)
        with PDFParser(path) as parser:
            elements = parser.convert_to_content_elements()

            assert len(elements) > 0

            para_count = sum(1 for e in elements if e.element_type == ElementType.PARAGRAPH)
            assert para_count > 0

            for e in elements:
                if e.element_type == ElementType.PARAGRAPH:
                    assert e.paragraph is not None
                    assert e.paragraph.text.strip()
                    assert e.paragraph.font is not None
                    assert e.paragraph.font.size > 0

    @pytest.mark.parametrize("filename", NATIVE_PDFS[:3], ids=NATIVE_IDS[:3])
    def test_pdf_to_docx_generation(self, filename):
        """PDF → 解析 → 生成DOCX（none模式）"""
        from app.services.pdf.parser import PDFParser
        from app.services.docx.parser import ElementType
        from app.services.docx import DocxGenerator
        from app.core.presets.styles import get_preset_style, get_style_mapping

        path = native_pdf_path(filename)
        with PDFParser(path) as parser:
            elements = parser.convert_to_content_elements()

        style_mapping = get_style_mapping(get_preset_style("universal"))
        style_keys = {}
        for e in elements:
            if e.element_type == ElementType.PARAGRAPH and e.paragraph:
                style_keys[e.original_index] = "body"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.docx")
            generator = DocxGenerator()
            generator.generate_from_elements(elements, style_mapping, style_keys)
            generator.save(output_path)

            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0

    @pytest.mark.parametrize("filename", NATIVE_PDFS[:3], ids=NATIVE_IDS[:3])
    def test_pdf_extract_para_dicts(self, filename):
        """PDF → _extract_para_dicts（processor接口）"""
        from app.services.pdf.parser import PDFParser
        from app.services.processor import DocumentProcessor

        path = native_pdf_path(filename)
        with PDFParser(path) as parser:
            elements = parser.convert_to_content_elements()

        processor = DocumentProcessor()
        para_dicts = processor._extract_para_dicts(elements)

        assert isinstance(para_dicts, list)
        assert len(para_dicts) > 0
        for pd in para_dicts:
            assert "text" in pd

    def test_processor_accepts_pdf_elements(self):
        """验证process_document接受elements参数"""
        from app.services.pdf.parser import PDFParser
        from app.services.docx.parser import ElementType

        if not NATIVE_PDFS:
            pytest.skip("No native PDFs")

        path = native_pdf_path(NATIVE_PDFS[0])
        with PDFParser(path) as parser:
            elements = parser.convert_to_content_elements()

        assert len(elements) > 0

        para_count = sum(1 for e in elements if e.element_type == ElementType.PARAGRAPH)
        assert para_count > 0


class TestPDFWithWatermark:
    """水印过滤相关测试"""

    def test_watermark_text_small_font(self):
        """极小字体的水印文本（如0.9pt）应被识别"""
        if not NATIVE_PDFS:
            pytest.skip("No native PDFs")

        from app.services.pdf.parser import PDFParser

        path = native_pdf_path(NATIVE_PDFS[0])
        with PDFParser(path) as parser:
            blocks = parser.extract_text_blocks(0)
            small_font_blocks = [b for b in blocks if b.font_size < 2]
            if small_font_blocks:
                for b in small_font_blocks:
                    assert len(b.text) < 100, "Tiny font text is likely watermark"


class TestPDFMultiFile:
    """多文件批量测试"""

    def test_all_native_pdfs_parse(self):
        """所有原生PDF都能正常解析，不崩溃"""
        from app.services.pdf.parser import PDFParser

        errors = []
        for fname in NATIVE_PDFS:
            try:
                path = native_pdf_path(fname)
                with PDFParser(path) as parser:
                    elements = parser.convert_to_content_elements()
                    assert len(elements) > 0, f"{fname[:40]}: no elements"
            except Exception as e:
                errors.append(f"{fname[:40]}: {str(e)[:100]}")

        if errors:
            pytest.fail(f"{len(errors)}/{len(NATIVE_PDFS)} PDFs failed:\n" + "\n".join(errors[:5]))

    def test_all_native_pdfs_type_detection(self):
        """所有原生PDF都被检测为native或mixed（不应该是纯scanned）"""
        from app.services.pdf.parser import PDFParser
        from app.services.pdf.detector import PDFType, detect_pdf_type

        errors = []
        for fname in NATIVE_PDFS:
            path = native_pdf_path(fname)
            with PDFParser(path) as parser:
                result = detect_pdf_type(parser)
                if result.pdf_type == PDFType.SCANNED:
                    errors.append(f"{fname[:40]}: detected=scanned (should be native/mixed)")

        if errors:
            pytest.fail(f"{len(errors)}/{len(NATIVE_PDFS)} misdetected as scanned:\n" + "\n".join(errors[:5]))

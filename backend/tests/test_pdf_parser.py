import pytest
import os
from conftest import get_native_pdfs, get_image_pdfs, native_pdf_path, image_pdf_path


NATIVE_PDFS = get_native_pdfs()
IMAGE_PDFS = get_image_pdfs()

NATIVE_IDS = [f[:40] for f in NATIVE_PDFS]
IMAGE_IDS = [f[:40] for f in IMAGE_PDFS]


@pytest.mark.parametrize("filename", NATIVE_PDFS, ids=NATIVE_IDS)
def test_native_pdf_basic_parsing(filename):
    """测试原生PDF基本解析：能打开、能提取文本块、页数正确"""
    from app.services.pdf.parser import PDFParser

    path = native_pdf_path(filename)
    parser = PDFParser(path)

    try:
        assert parser.get_page_count() > 0, f"页数应>0, 实际={parser.get_page_count()}"

        total_blocks = 0
        for page_num in range(parser.get_page_count()):
            blocks = parser.extract_text_blocks(page_num)
            total_blocks += len(blocks)
            for b in blocks:
                assert b.text, f"page={page_num}有空文本块"
                assert b.font_size > 0, f"page={page_num}字体大小<=0"
                assert len(b.bbox) == 4, f"page={page_num} bbox维度不对"

        assert total_blocks > 0, "总文本块应>0"
    finally:
        parser.close()


@pytest.mark.parametrize("filename", NATIVE_PDFS[:3], ids=NATIVE_IDS[:3])
def test_native_pdf_content_elements(filename):
    """测试原生PDF转ContentElement：元素类型、段落文本非空"""
    from app.services.pdf.parser import PDFParser

    path = native_pdf_path(filename)
    parser = PDFParser(path)

    try:
        elements = parser.convert_to_content_elements()

        assert len(elements) > 0, "应生成ContentElement"

        para_count = 0
        table_count = 0
        image_count = 0
        for e in elements:
            assert e.element_type is not None
            if e.element_type.value == "paragraph":
                assert e.paragraph is not None, "段落元素应有paragraph"
                assert e.paragraph.text.strip(), f"段落{e.original_index}文本为空"
                assert e.paragraph.font is not None
                assert e.paragraph.font.size > 0
                para_count += 1
            elif e.element_type.value == "table":
                assert e.table_cells is not None
                table_count += 1
            elif e.element_type.value == "image":
                assert e.image_data is not None
                image_count += 1

        assert para_count > 0, "应有至少一个段落元素"
    finally:
        parser.close()


@pytest.mark.parametrize("filename", NATIVE_PDFS[:3], ids=NATIVE_IDS[:3])
def test_native_pdf_paragraph_info_list(filename):
    """测试原生PDF转paragraph_info_list（向后兼容）"""
    from app.services.pdf.parser import PDFParser

    path = native_pdf_path(filename)
    parser = PDFParser(path)

    try:
        result = parser.convert_to_paragraph_info_list()

        assert isinstance(result, list)
        assert len(result) > 0
        for item in result:
            assert "text" in item
            assert "font_size" in item or "font_bold" in item
            assert item["text"].strip(), f"段落文本为空: {item}"
    finally:
        parser.close()


@pytest.mark.parametrize("filename", NATIVE_PDFS[:5], ids=NATIVE_IDS[:5])
def test_native_pdf_tables(filename):
    """测试原生PDF表格提取"""
    from app.services.pdf.parser import PDFParser

    path = native_pdf_path(filename)
    parser = PDFParser(path)

    try:
        for page_num in range(parser.get_page_count()):
            tables = parser.extract_tables(page_num)
            for t in tables:
                assert t.data is not None
                assert t.row_count >= 0
                assert t.col_count >= 0
    finally:
        parser.close()


@pytest.mark.parametrize("filename", NATIVE_PDFS[:5], ids=NATIVE_IDS[:5])
def test_native_pdf_images(filename):
    """测试原生PDF图片提取"""
    from app.services.pdf.parser import PDFParser

    path = native_pdf_path(filename)
    parser = PDFParser(path)

    try:
        for page_num in range(parser.get_page_count()):
            images = parser.extract_images(page_num)
            for img in images:
                assert img.data is not None
                assert len(img.data) > 0
                assert img.ext in ("png", "jpeg", "jpg", "bmp", "gif")
    finally:
        parser.close()


@pytest.mark.parametrize("filename", NATIVE_PDFS[:3], ids=NATIVE_IDS[:3])
def test_native_pdf_column_detection(filename):
    """测试分栏检测不崩溃"""
    from app.services.pdf.parser import PDFParser

    path = native_pdf_path(filename)
    parser = PDFParser(path)

    try:
        for page_num in range(parser.get_page_count()):
            columns = parser.detect_columns(page_num)
            assert len(columns) >= 1, f"page={page_num} 应至少返回1栏"
    finally:
        parser.close()


@pytest.mark.parametrize("filename", IMAGE_PDFS[:3], ids=IMAGE_IDS[:3])
def test_image_pdf_no_text(filename):
    """测试图片型PDF应无文本"""
    from app.services.pdf.parser import PDFParser

    path = image_pdf_path(filename)
    parser = PDFParser(path)

    try:
        total_text = parser.extract_all_text()
        assert len(total_text.strip()) == 0, "图片型PDF应无文本"
    finally:
        parser.close()


@pytest.mark.parametrize("filename", IMAGE_PDFS[:3], ids=IMAGE_IDS[:3])
def test_image_pdf_has_images(filename):
    """测试图片型PDF应有图片"""
    from app.services.pdf.parser import PDFParser

    path = image_pdf_path(filename)
    parser = PDFParser(path)

    try:
        total_images = 0
        for page_num in range(parser.get_page_count()):
            images = parser.extract_images(page_num)
            total_images += len(images)
        assert total_images > 0, "图片型PDF应有图片"
    finally:
        parser.close()

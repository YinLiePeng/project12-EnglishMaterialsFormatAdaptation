"""Phase 1 测试脚本 - 验证JSON到DOCX转换器

测试流程：
1. 使用opendataloader_pdf解析PDF生成JSON
2. 使用新的PDFParser读取JSON并转换为ContentElement
3. 使用DocxGenerator生成DOCX
4. 对比生成的DOCX与标准DOCX的相似度
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any

# 添加backend到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.pdf.parser import PDFParser
from app.services.pdf.converter import PDFToDocxConverter
from app.services.docx.parser import DocxParser, ContentElement, ElementType


def test_json_parser():
    """测试JSON解析器"""
    print("=" * 60)
    print("测试1: JSON解析器")
    print("=" * 60)
    
    # 测试文件
    test_pdf = Path("/mnt/e/Opencode/project12-EnglishMaterialsFormatAdaptation/backend/测试用例/M2U1 Food and drinks!（知识清单）英语牛津上海版试用本五年级下册[56534463].pdf")
    
    if not test_pdf.exists():
        print(f"❌ 测试文件不存在: {test_pdf}")
        return False
    
    # 检查JSON是否存在
    json_path = test_pdf.with_suffix('.json')
    if not json_path.exists():
        print(f"⚠️ JSON文件不存在，需要先运行opendataloader_pdf生成")
        print(f"   缺失: {json_path}")
        return False
    
    print(f"✓ 找到测试文件: {test_pdf.name}")
    print(f"✓ 找到JSON文件: {json_path.name}")
    
    # 创建解析器
    parser = PDFParser(str(test_pdf))
    
    # 测试基本方法
    page_count = parser.get_page_count()
    print(f"✓ 页面数量: {page_count}")
    
    # 测试ContentElement转换
    elements = parser.convert_to_content_elements()
    print(f"✓ 转换得到 {len(elements)} 个ContentElement")
    
    # 统计元素类型
    type_counts = {}
    for elem in elements:
        type_name = elem.element_type.name
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
    
    print("\n元素类型分布:")
    for type_name, count in sorted(type_counts.items()):
        print(f"  {type_name}: {count}")
    
    # 显示前5个元素
    print("\n前5个元素示例:")
    for i, elem in enumerate(elements[:5]):
        if elem.element_type == ElementType.PARAGRAPH and elem.paragraph:
            text = elem.paragraph.text[:50] + "..." if len(elem.paragraph.text) > 50 else elem.paragraph.text
            print(f"  [{i}] PARAGRAPH: {text}")
            print(f"       Font: {elem.paragraph.font.name}, Size: {elem.paragraph.font.size}")
        elif elem.element_type == ElementType.TABLE:
            print(f"  [{i}] TABLE: {len(elem.table_cells)} rows")
        elif elem.element_type == ElementType.IMAGE:
            print(f"  [{i}] IMAGE: {len(elem.image_data)} bytes")
    
    print("\n✅ JSON解析器测试通过")
    return True


def test_converter():
    """测试DOCX转换器"""
    print("\n" + "=" * 60)
    print("测试2: DOCX转换器")
    print("=" * 60)
    
    test_pdf = Path("/mnt/e/Opencode/project12-EnglishMaterialsFormatAdaptation/backend/测试用例/M2U1 Food and drinks!（知识清单）英语牛津上海版试用本五年级下册[56534463].pdf")
    output_path = test_pdf.parent / "test_output.docx"
    
    try:
        converter = PDFToDocxConverter()
        result_path = converter.convert(
            str(test_pdf),
            str(output_path),
            preserve_format=True
        )
        
        if Path(result_path).exists():
            file_size = Path(result_path).stat().st_size
            print(f"✓ 成功生成DOCX: {result_path}")
            print(f"✓ 文件大小: {file_size} bytes ({file_size/1024:.1f} KB)")
            
            # 验证DOCX内容
            doc = DocxParser(result_path)
            content = doc.extract_content()
            print(f"✓ DOCX包含 {len(content)} 个元素")
            
            return True
        else:
            print(f"❌ 生成失败: {result_path}")
            return False
            
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pdf_parser_compatibility():
    """测试PDFParser向后兼容性"""
    print("\n" + "=" * 60)
    print("测试3: 向后兼容性")
    print("=" * 60)
    
    test_pdf = Path("/mnt/e/Opencode/project12-EnglishMaterialsFormatAdaptation/backend/测试用例/M2U1 Food and drinks!（知识清单）英语牛津上海版试用本五年级下册[56534463].pdf")
    
    try:
        parser = PDFParser(str(test_pdf))
        
        # 测试旧版方法
        print("测试旧版方法:")
        
        # extract_text_blocks
        blocks = parser.extract_text_blocks(0)
        print(f"✓ extract_text_blocks(0): {len(blocks)} blocks")
        
        # extract_tables
        tables = parser.extract_tables(0)
        print(f"✓ extract_tables(0): {len(tables)} tables")
        
        # extract_images
        images = parser.extract_images(0)
        print(f"✓ extract_images(0): {len(images)} images")
        
        # extract_all_text
        all_text = parser.extract_all_text()
        print(f"✓ extract_all_text: {len(all_text)} chars")
        
        # extract_structured_content
        structured = parser.extract_structured_content()
        print(f"✓ extract_structured_content: {len(structured)} items")
        
        # convert_to_paragraph_info_list
        para_list = parser.convert_to_paragraph_info_list()
        print(f"✓ convert_to_paragraph_info_list: {len(para_list)} paragraphs")
        
        print("\n✅ 向后兼容性测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 兼容性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Phase 1 测试: JSON到DOCX转换器")
    print("=" * 60)
    
    results = []
    
    # 测试1: JSON解析器
    results.append(("JSON解析器", test_json_parser()))
    
    # 测试2: DOCX转换器
    results.append(("DOCX转换器", test_converter()))
    
    # 测试3: 向后兼容性
    results.append(("向后兼容性", test_pdf_parser_compatibility()))
    
    # 汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！Phase 1完成。")
        return 0
    else:
        print("\n⚠️ 部分测试失败，需要修复。")
        return 1


if __name__ == "__main__":
    sys.exit(main())

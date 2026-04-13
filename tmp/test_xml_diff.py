import sys

sys.path.insert(0, "backend")
import shutil, zipfile, os
from lxml import etree

# 1. 用当前代码生成输出
from app.services.docx.parser import DocxParser
from app.services.docx.generator import DocxGenerator
from app.core.presets.styles import get_style_mapping, get_preset_style

parser = DocxParser("测试用例/空模板排版/高一下3月13-原文件.docx")
elements = parser.extract_content()

marker_position = {
    "element_index": 1,
    "type": "table_cell",
    "table_index": 0,
    "row": 4,
    "col": 0,
}
style_mapping = get_style_mapping(get_preset_style("universal"))

generator = DocxGenerator("测试用例/空模板排版/模板.docx")
generator.fill_template_from_elements(
    elements,
    "{{CONTENT}}",
    style_mapping,
    {},
    preserve_format=False,
    marker_position=marker_position,
)
generator.save("tmp/output_current.docx")


# 2. 对比两个文件的 XML 差异
def format_xml(xml_bytes):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.fromstring(xml_bytes, parser)
    return etree.tostring(tree, pretty_print=True, encoding="unicode")


def compare_zip_xml(file1, file2):
    with zipfile.ZipFile(file1) as z1, zipfile.ZipFile(file2) as z2:
        # 关注的 XML 文件
        xml_files = [
            "word/document.xml",
            "word/styles.xml",
            "word/header1.xml",
            "word/header2.xml",
            "word/header3.xml",
            "[Content_Types].xml",
            "word/_rels/document.xml.rels",
        ]

        print("=" * 60)
        print("XML 差异报告: 模板.docx vs output_current.docx")
        print("=" * 60)

        total_diff_files = 0
        for name in xml_files:
            if name in z1.namelist() or name in z2.namelist():
                xml1 = z1.read(name) if name in z1.namelist() else b""
                xml2 = z2.read(name) if name in z2.namelist() else b""

                if xml1 != xml2:
                    fmt1 = format_xml(xml1).splitlines()
                    fmt2 = format_xml(xml2).splitlines()

                    import difflib

                    diff = list(
                        difflib.unified_diff(
                            fmt1, fmt2, lineterm="", fromfile="模板", tofile="输出"
                        )
                    )

                    # Count actual diff lines (excluding headers)
                    diff_content = [
                        l for l in diff if l.startswith("+") or l.startswith("-")
                    ]
                    # Remove file header lines
                    diff_content = [
                        l
                        for l in diff_content
                        if not l.startswith("+++") and not l.startswith("---")
                    ]

                    print(f"\n{'=' * 60}")
                    print(f"DIFF: {name}  ({len(diff_content)} 行差异)")
                    print(f"{'=' * 60}")

                    for line in diff[:120]:
                        print(line)
                    if len(diff) > 120:
                        print(f"\n... (共 {len(diff)} 行差异，仅显示前120行)")
                    total_diff_files += 1
                else:
                    print(f"\nSAME: {name}  (完全一致)")
            else:
                print(f"\nMISSING: {name}  (文件不存在)")

        # Also check for files in output that aren't in template
        extra_files = set(z2.namelist()) - set(z1.namelist())
        missing_files = set(z1.namelist()) - set(z2.namelist())

        if extra_files:
            print(f"\n{'=' * 60}")
            print(f"输出文件中多出的文件 (相比模板):")
            for f in sorted(extra_files):
                print(f"  + {f}")

        if missing_files:
            print(f"\n{'=' * 60}")
            print(f"输出文件中缺失的文件 (相比模板):")
            for f in sorted(missing_files):
                print(f"  - {f}")

        print(f"\n{'=' * 60}")
        print(f"总结: {total_diff_files} 个 XML 文件有差异")
        print(f"{'=' * 60}")


compare_zip_xml("测试用例/空模板排版/模板.docx", "tmp/output_current.docx")

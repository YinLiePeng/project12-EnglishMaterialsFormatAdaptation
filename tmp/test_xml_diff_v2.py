import sys

sys.path.insert(0, "backend")
import zipfile, os, difflib
from lxml import etree

# ============================================================
# Step 0: Already generated output_current.docx from previous run
# ============================================================
if not os.path.exists("tmp/output_current.docx"):
    print("ERROR: tmp/output_current.docx not found. Run the generation first.")
    sys.exit(1)


# ============================================================
# Helper functions
# ============================================================
def format_xml(xml_bytes):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.fromstring(xml_bytes, parser)
    return etree.tostring(tree, pretty_print=True, encoding="unicode")


def count_real_diffs(fmt1_lines, fmt2_lines):
    """Count actual content diff lines (excluding diff headers)"""
    diff = list(
        difflib.unified_diff(
            fmt1_lines, fmt2_lines, lineterm="", fromfile="A", tofile="B"
        )
    )
    content_diffs = [l for l in diff if l.startswith("+") or l.startswith("-")]
    content_diffs = [
        l for l in content_diffs if not l.startswith("+++") and not l.startswith("---")
    ]
    return content_diffs, diff


# ============================================================
# Step 1: Comprehensive comparison
# ============================================================
template_file = "测试用例/空模板排版/模板.docx"
output_file = "tmp/output_current.docx"

with zipfile.ZipFile(template_file) as z1, zipfile.ZipFile(output_file) as z2:
    xml_files = sorted(set(z1.namelist()) | set(z2.namelist()))
    xml_files = [f for f in xml_files if f.endswith(".xml") or f.endswith(".rels")]

    print("=" * 70)
    print("详细 XML 差异报告: 模板.docx vs output_current.docx")
    print("=" * 70)

    for name in xml_files:
        has1 = name in z1.namelist()
        has2 = name in z2.namelist()

        if not has1:
            print(f"\n{'=' * 70}")
            print(f"NEW FILE (仅输出中有): {name}")
            continue
        if not has2:
            print(f"\n{'=' * 70}")
            print(f"MISSING FILE (仅模板中有): {name}")
            continue

        xml1 = z1.read(name)
        xml2 = z2.read(name)

        if xml1 == xml2:
            print(f"\nIDENTICAL: {name}")
            continue

        # Raw bytes differ - check if meaningful
        try:
            fmt1 = format_xml(xml1).splitlines()
            fmt2 = format_xml(xml2).splitlines()
        except Exception as e:
            print(f"\nPARSE ERROR: {name}: {e}")
            continue

        content_diffs, full_diff = count_real_diffs(fmt1, fmt2)

        if not content_diffs:
            print(f"\nWHITESPACE ONLY: {name} (原始字节不同，但格式化后完全一致)")
            continue

        print(f"\n{'=' * 70}")
        print(f"DIFF: {name}  ({len(content_diffs)} 行内容差异)")
        print(f"{'=' * 70}")

        # Show all diffs for small files, first 150 for large
        if len(full_diff) <= 200:
            for line in full_diff:
                print(line)
        else:
            for line in full_diff[:150]:
                print(line)
            print(f"\n... (共 {len(full_diff)} 行差异，仅显示前150行)")

    # ============================================================
    # Step 2: Specific sectPr analysis in document.xml
    # ============================================================
    print(f"\n{'=' * 70}")
    print("sectPr (节属性) 详细分析")
    print(f"{'=' * 70}")

    doc1_xml = format_xml(z1.read("word/document.xml"))
    doc2_xml = format_xml(z2.read("word/document.xml"))

    # Extract all sectPr elements
    tree1 = etree.fromstring(z1.read("word/document.xml"))
    tree2 = etree.fromstring(z2.read("word/document.xml"))

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    sectprs1 = tree1.findall(".//w:sectPr", ns)
    sectprs2 = tree2.findall(".//w:sectPr", ns)

    print(f"\n模板中 sectPr 数量: {len(sectprs1)}")
    print(f"输出中 sectPr 数量: {len(sectprs2)}")

    for i, (s1, s2) in enumerate(zip(sectprs1, sectprs2)):
        s1_str = etree.tostring(s1, pretty_print=True, encoding="unicode")
        s2_str = etree.tostring(s2, pretty_print=True, encoding="unicode")
        if s1_str == s2_str:
            print(f"\n  sectPr[{i}]: 完全一致")
        else:
            print(f"\n  sectPr[{i}]: 有差异!")
            diff = list(
                difflib.unified_diff(
                    s1_str.splitlines(),
                    s2_str.splitlines(),
                    lineterm="",
                    fromfile=f"模板 sectPr[{i}]",
                    tofile=f"输出 sectPr[{i}]",
                )
            )
            for line in diff:
                print(f"    {line}")

    # ============================================================
    # Step 3: Header/footer reference analysis
    # ============================================================
    print(f"\n{'=' * 70}")
    print("页眉页脚引用分析 (headerReference / footerReference)")
    print(f"{'=' * 70}")

    for label, tree in [("模板", tree1), ("输出", tree2)]:
        refs = tree.findall(".//w:sectPr/w:headerReference", ns)
        foot_refs = tree.findall(".//w:sectPr/w:footerReference", ns)
        print(f"\n{label}:")
        for r in refs + foot_refs:
            tag = "headerReference" if "headerReference" in r.tag else "footerReference"
            print(f"  {tag}: type={r.get(qn('w:type'))}, r:id={r.get(qn('r:id'))}")

    # ============================================================
    # Step 4: Non-XML files comparison
    # ============================================================
    print(f"\n{'=' * 70}")
    print("非 XML 文件对比")
    print(f"{'=' * 70}")

    all_files = sorted(set(z1.namelist()) | set(z2.namelist()))
    for f in all_files:
        if f.endswith("/"):
            continue
        has1 = f in z1.namelist()
        has2 = f in z2.namelist()
        if not has1:
            print(f"  + {f} (仅输出)")
        elif not has2:
            print(f"  - {f} (仅模板)")
        else:
            d1 = z1.read(f)
            d2 = z2.read(f)
            if d1 != d2:
                print(f"  ~ {f} (内容不同, {len(d1)} vs {len(d2)} bytes)")
            # else: identical, skip

    from lxml import etree
    from lxml.etree import ElementTree

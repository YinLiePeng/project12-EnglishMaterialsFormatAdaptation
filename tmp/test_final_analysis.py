import sys

sys.path.insert(0, "backend")
import zipfile, difflib
from lxml import etree


def qn(tag):
    ns_map = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    prefix, local = tag.split(":")
    return "{%s}%s" % (ns_map[prefix], local)


ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

template_file = "测试用例/空模板排版/模板.docx"
output_file = "tmp/output_current.docx"


def format_xml(xml_bytes):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.fromstring(xml_bytes, parser)
    return etree.tostring(tree, pretty_print=True, encoding="unicode")


# ============================================================
# 1. 总结所有 XML 文件差异
# ============================================================
print("=" * 70)
print("完整差异总结")
print("=" * 70)

with zipfile.ZipFile(template_file) as z1, zipfile.ZipFile(output_file) as z2:
    all_xml = sorted(set(z1.namelist()) | set(z2.namelist()))
    all_xml = [f for f in all_xml if f.endswith(".xml") or f.endswith(".rels")]

    for name in all_xml:
        has1 = name in z1.namelist()
        has2 = name in z2.namelist()

        if not has1 or not has2:
            status = "NEW (仅输出)" if not has1 else "MISSING (仅模板)"
            print(f"  {status}: {name}")
            continue

        xml1 = z1.read(name)
        xml2 = z2.read(name)

        if xml1 == xml2:
            print(f"  IDENTICAL: {name}")
            continue

        try:
            fmt1 = format_xml(xml1).splitlines()
            fmt2 = format_xml(xml2).splitlines()
        except:
            print(f"  BINARY/PARSE ERROR: {name}")
            continue

        if fmt1 == fmt2:
            print(f"  WHITESPACE ONLY: {name}")
            continue

        diff = list(
            difflib.unified_diff(
                fmt1, fmt2, lineterm="", fromfile="模板", tofile="输出"
            )
        )
        content_diffs = [
            l
            for l in diff
            if (l.startswith("+") or l.startswith("-"))
            and not l.startswith("+++")
            and not l.startswith("---")
        ]
        print(f"  CONTENT DIFF: {name} ({len(content_diffs)} 行)")

# ============================================================
# 2. 详细分析 document.xml 差异 (排除内容填充部分)
# ============================================================
print(f"\n{'=' * 70}")
print("document.xml 差异分类分析")
print(f"{'=' * 70}")

with zipfile.ZipFile(template_file) as z1, zipfile.ZipFile(output_file) as z2:
    tree1 = etree.fromstring(z1.read("word/document.xml"))
    tree2 = etree.fromstring(z2.read("word/document.xml"))

    body1 = tree1.find(qn("w:body"))
    body2 = tree2.find(qn("w:body"))

    # Check body-level structure
    children1 = list(body1)
    children2 = list(body2)

    print(f"\n模板 body 顶级子元素: {len(children1)}")
    print(f"输出 body 顶级子元素: {len(children2)}")

    print("\n模板 body 顶级结构:")
    for i, c in enumerate(children1):
        tag = etree.QName(c.tag).localname
        text = "".join(c.itertext()).strip()[:50]
        print(f'  [{i}] <w:{tag}> "{text}"')

    print("\n输出 body 顶级结构:")
    for i, c in enumerate(children2):
        tag = etree.QName(c.tag).localname
        text = "".join(c.itertext()).strip()[:50]
        print(f'  [{i}] <w:{tag}> "{text}"')

# ============================================================
# 3. 表格外的差异: 只看模板中存在但输出中改变的部分
# ============================================================
print(f"\n{'=' * 70}")
print("表格外的结构性差异 (排除内容填充)")
print(f"{'=' * 70}")

with zipfile.ZipFile(template_file) as z1, zipfile.ZipFile(output_file) as z2:
    doc1 = format_xml(z1.read("word/document.xml")).splitlines()
    doc2 = format_xml(z2.read("word/document.xml")).splitlines()

    # Extract the template's first 524 lines (before content insertion point)
    # and compare with the output's first part
    # The content starts at line 527 in the diff output

    # Find where the content cell starts in template
    # Template line around 524 is the last <w:p> in the empty cell
    # Let's find lines up to sectPr

    # In template: find the <w:sectPr> line
    sectpr_idx1 = None
    sectpr_idx2 = None
    for i, line in enumerate(doc1):
        if "<w:sectPr" in line:
            sectpr_idx1 = i
            break
    for i, line in enumerate(doc2):
        if "<w:sectPr" in line:
            sectpr_idx2 = i
            break

    print(f"模板 sectPr 位于第 {sectpr_idx1} 行 (共 {len(doc1)} 行)")
    print(f"输出 sectPr 位于第 {sectpr_idx2} 行 (共 {len(doc2)} 行)")

    # Compare the sectPr section (last ~30 lines)
    sectpr_section1 = doc1[sectpr_idx1:]
    sectpr_section2 = doc2[sectpr_idx2:]

    if sectpr_section1 == sectpr_section2:
        print("sectPr 及后续内容: 完全一致 ✓")
    else:
        print("sectPr 及后续内容: 有差异!")
        for line in difflib.unified_diff(
            sectpr_section1,
            sectpr_section2,
            lineterm="",
            fromfile="模板",
            tofile="输出",
        ):
            print(f"  {line}")

# ============================================================
# 4. 检查新增的空表格
# ============================================================
print(f"\n{'=' * 70}")
print("新增空表格分析")
print(f"{'=' * 70}")

with zipfile.ZipFile(output_file) as zf:
    tree = etree.fromstring(zf.read("word/document.xml"))
    body = tree.find(qn("w:body"))
    tables = body.findall("w:tbl", ns)

    print(f"模板中表格数: 1")
    print(f"输出中表格数: {len(tables)}")

    for i, tbl in enumerate(tables):
        rows = tbl.findall("w:tr", ns)
        text = "".join(tbl.itertext()).strip()[:60]
        tbl_xml = etree.tostring(tbl, pretty_print=True, encoding="unicode")
        print(f'\n  表格[{i}]: {len(rows)} 行, 文本="{text}"')
        print(f"  XML 大小: {len(tbl_xml)} 字符")
        if len(rows) == 1:
            # Show the full XML of the small table
            lines = tbl_xml.splitlines()
            for line in lines[:15]:
                print(f"    {line}")
            if len(lines) > 15:
                print(f"    ... ({len(lines)} lines total)")

# ============================================================
# 5. 原因分析：为什么多了2个空表格
# ============================================================
print(f"\n{'=' * 70}")
print("原因分析")
print(f"{'=' * 70}")

with zipfile.ZipFile(template_file) as z1:
    tree = etree.fromstring(z1.read("word/document.xml"))
    body = tree.find(qn("w:body"))
    tables = body.findall("w:tbl", ns)
    tbl = tables[0]
    rows = tbl.findall("w:tr", ns)
    row4 = rows[4]
    cell0 = row4.findall("w:tc", ns)[0]
    paras = cell0.findall("w:p", ns)

    print(f"\n模板表格[0]行[4]列[0] 原始内容:")
    for i, p in enumerate(paras):
        text = "".join(p.itertext()).strip()
        # Check if this paragraph has a table embedded
        sub_tbls = p.findall(".//w:tbl", ns)
        extra = f" [包含 {len(sub_tbls)} 个子表格]" if sub_tbls else ""
        print(f'  段落[{i}]: "{text}"{extra}')

    # Check the raw XML for nested structures
    cell_xml = etree.tostring(cell0, pretty_print=True, encoding="unicode")
    if "<w:tbl>" in cell_xml[cell_xml.find("</w:p>") :]:
        print("\n注意: 模板单元格内有嵌套结构")

# ============================================================
# 6. Content_Types.xml 差异分析
# ============================================================
print(f"\n{'=' * 70}")
print("[Content_Types].xml 差异 (已知)")
print(f"{'=' * 70}")
with zipfile.ZipFile(template_file) as z1, zipfile.ZipFile(output_file) as z2:
    ct1 = format_xml(z1.read("[Content_Types].xml")).splitlines()
    ct2 = format_xml(z2.read("[Content_Types].xml")).splitlines()
    for line in difflib.unified_diff(
        ct1, ct2, lineterm="", fromfile="模板", tofile="输出"
    ):
        print(line)
    print("\n原因: python-docx 保存时重新排列了 <Default> 元素顺序，不影响功能")

import sys

sys.path.insert(0, "backend")
import zipfile
from lxml import etree
from lxml import etree as ET

template_file = "测试用例/空模板排版/模板.docx"
output_file = "tmp/output_current.docx"


def qn(tag):
    ns_map = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    prefix, local = tag.split(":")
    return "{%s}%s" % (ns_map[prefix], local)


with zipfile.ZipFile(template_file) as z1, zipfile.ZipFile(output_file) as z2:
    ns = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }

    for label, zf in [("模板", z1), ("输出", z2)]:
        tree = etree.fromstring(zf.read("word/document.xml"))
        print(f"\n{'=' * 60}")
        print(f"{label} - 页眉页脚引用:")
        print(f"{'=' * 60}")

        sectprs = tree.findall(".//w:sectPr", ns)
        print(f"  sectPr 数量: {len(sectprs)}")

        for i, sp in enumerate(sectprs):
            print(f"\n  --- sectPr[{i}] ---")
            for child in sp:
                tag = etree.QName(child.tag).localname
                if tag in ("headerReference", "footerReference"):
                    rtype = child.get(qn("w:type"))
                    rid = child.get(qn("r:id"))
                    print(f"    {tag}: type={rtype}, r:id={rid}")
                elif tag == "pgSz":
                    w = child.get(qn("w:w"))
                    h = child.get(qn("w:h"))
                    orient = child.get(qn("w:orient"), "portrait")
                    print(f"    pgSz: w={w}, h={h}, orient={orient}")
                elif tag == "pgMar":
                    top = child.get(qn("w:top"))
                    bottom = child.get(qn("w:bottom"))
                    left = child.get(qn("w:left"))
                    right = child.get(qn("w:right"))
                    header = child.get(qn("w:header"))
                    footer = child.get(qn("w:footer"))
                    print(
                        f"    pgMar: top={top}, bottom={bottom}, left={left}, right={right}, header={header}, footer={footer}"
                    )
                elif tag == "cols":
                    print(f"    cols: {etree.tostring(child, encoding='unicode')}")
                elif tag == "docGrid":
                    type_val = child.get(qn("w:type"))
                    linepitch = child.get(qn("w:linePitch"))
                    print(f"    docGrid: type={type_val}, linePitch={linepitch}")
                else:
                    print(
                        f"    {tag}: {etree.tostring(child, encoding='unicode').strip()}"
                    )

    # ============================================================
    # Also check: what's at the END of document.xml in both files
    # ============================================================
    print(f"\n{'=' * 60}")
    print("document.xml 尾部对比 (最后30个元素)")
    print(f"{'=' * 60}")

    for label, zf in [("模板", z1), ("输出", z2)]:
        tree = etree.fromstring(zf.read("word/document.xml"))
        body = tree.find(qn("w:body"))
        children = list(body)
        print(f"\n{label} body 子元素总数: {len(children)}")
        print(f"最后10个子元素:")
        for i, child in enumerate(children[-10:]):
            tag = etree.QName(child.tag).localname
            idx = len(children) - 10 + i
            if tag == "p":
                text = "".join(child.itertext()).strip()[:60]
                print(f'  [{idx}] <w:p> "{text}"')
            elif tag == "tbl":
                print(f"  [{idx}] <w:tbl>")
            elif tag == "sectPr":
                print(f"  [{idx}] <w:sectPr>")
            else:
                print(f"  [{idx}] <w:{tag}>")

import sys

sys.path.insert(0, "backend")
import zipfile
from lxml import etree


def qn(tag):
    ns_map = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    prefix, local = tag.split(":")
    return "{%s}%s" % (ns_map[prefix], local)


ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

template_file = "测试用例/空模板排版/模板.docx"
output_file = "tmp/output_current.docx"

for label, f in [("模板", template_file), ("输出", output_file)]:
    with zipfile.ZipFile(f) as zf:
        tree = etree.fromstring(zf.read("word/document.xml"))
        body = tree.find(qn("w:body"))

        # Direct children tables
        direct = body.findall("w:tbl", ns)
        # All descendant tables
        all_tbl = body.findall(".//w:tbl", ns)

        print(f"\n{label}:")
        print(f"  body 直属表格: {len(direct)}")
        print(f"  所有表格(含嵌套): {len(all_tbl)}")

        for i, tbl in enumerate(all_tbl):
            rows = tbl.findall("w:tr", ns)
            text = "".join(tbl.itertext()).strip()[:60]
            # Find parent
            parent = tbl.getparent()
            parent_tag = (
                etree.QName(parent.tag).localname if parent is not None else "?"
            )
            print(f'  表格[{i}]: {len(rows)}行, 父={parent_tag}, 文本="{text}"')

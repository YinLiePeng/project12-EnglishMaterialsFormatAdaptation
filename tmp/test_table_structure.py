import sys

sys.path.insert(0, "backend")
import zipfile
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

for label, f in [("模板", template_file), ("输出", output_file)]:
    with zipfile.ZipFile(f) as zf:
        tree = etree.fromstring(zf.read("word/document.xml"))
        body = tree.find(qn("w:body"))

        print(f"\n{'=' * 60}")
        print(f"{label} - 结构概览")
        print(f"{'=' * 60}")

        tables = body.findall(".//w:tbl", ns)
        print(f"表格数量: {len(tables)}")

        for ti, tbl in enumerate(tables):
            rows = tbl.findall("w:tr", ns)
            print(f"\n  表格[{ti}]: {len(rows)} 行")
            for ri, row in enumerate(rows):
                cells = row.findall("w:tc", ns)
                cell_info = []
                for ci, cell in enumerate(cells):
                    paras = cell.findall("w:p", ns)
                    text = ""
                    for p in paras:
                        text += "".join(p.itertext()).strip()
                    text = text[:40]
                    cell_info.append(f'[{ci}] {len(paras)}p "{text}"')
                print(f"    行[{ri}]: {', '.join(cell_info)}")

# Now compare the template table cell content vs output table cell content
# Focus on row 4, col 0 (where content was inserted)
print(f"\n{'=' * 60}")
print("关键对比: 表格[0]行[4]列[0] (内容插入位置)")
print(f"{'=' * 60}")

for label, f in [("模板", template_file), ("输出", output_file)]:
    with zipfile.ZipFile(f) as zf:
        tree = etree.fromstring(zf.read("word/document.xml"))
        body = tree.find(qn("w:body"))
        tbl = body.findall(".//w:tbl", ns)[0]
        rows = tbl.findall("w:tr", ns)
        row = rows[4]
        cell = row.findall("w:tc", ns)[0]
        paras = cell.findall("w:p", ns)

        print(f"\n{label}: 行[4]列[0] 有 {len(paras)} 个段落")
        # Show first 5 and last 5
        if len(paras) <= 10:
            for i, p in enumerate(paras):
                text = "".join(p.itertext()).strip()[:80]
                print(f'  [{i}] "{text}"')
        else:
            for i, p in enumerate(paras[:3]):
                text = "".join(p.itertext()).strip()[:80]
                print(f'  [{i}] "{text}"')
            print(f"  ... 省略 {len(paras) - 6} 个段落 ...")
            for i, p in enumerate(paras[-3:], len(paras) - 3):
                text = "".join(p.itertext()).strip()[:80]
                print(f'  [{i}] "{text}"')

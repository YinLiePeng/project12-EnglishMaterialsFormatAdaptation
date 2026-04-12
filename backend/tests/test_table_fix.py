"""验证表格单元格内 run 段落边界修复的端到端测试"""

import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from app.services.docx.parser import DocxParser, ElementType
from app.services.docx.generator import DocxGenerator
from app.services.docx.parser import TableCellInfo


def test_table_cell_paragraph_runs():
    sample = (
        Path(__file__).parent.parent.parent
        / "测试用例"
        / "无模板排版"
        / "高一下3月13-原文件.docx"
    )
    if not sample.exists():
        print(f"样例文件不存在: {sample}")
        return False

    parser = DocxParser(str(sample))
    elements = parser.extract_content()

    tables = [e for e in elements if e.element_type == ElementType.TABLE]
    if not tables:
        print("文档中未找到表格")
        return False

    print(f"共找到 {len(tables)} 个表格\n")

    all_ok = True
    for t_idx, table_elem in enumerate(tables):
        print(f"--- 表格 {t_idx + 1} ---")
        for r_idx, row in enumerate(table_elem.table_cells):
            for c_idx, cell in enumerate(row):
                if cell.v_merge == "continue":
                    continue

                has_paragraph_runs = len(cell.paragraph_runs) > 0
                has_runs = len(cell.runs) > 0

                if has_runs:
                    print(
                        f"  Cell[{r_idx},{c_idx}]: "
                        f"text={cell.text[:60]!r}... "
                        f"runs={len(cell.runs)} "
                        f"paragraph_groups={len(cell.paragraph_runs)}"
                    )
                else:
                    print(
                        f"  Cell[{r_idx},{c_idx}]: text={cell.text[:60]!r}... (no runs)"
                    )

                if has_paragraph_runs:
                    total_runs_from_groups = sum(len(g) for g in cell.paragraph_runs)
                    if total_runs_from_groups != len(cell.runs):
                        print(
                            f"    WARNING: paragraph_runs 总run数({total_runs_from_groups}) "
                            f"!= runs数({len(cell.runs)})"
                        )
                        all_ok = False
                    else:
                        for pg_idx, pg in enumerate(cell.paragraph_runs):
                            texts = [r.text or "" for r in pg]
                            joined = "".join(texts)
                            print(
                                f"    段落{pg_idx}: {len(pg)} runs -> {joined[:80]!r}"
                            )
    return all_ok


def test_table_roundtrip():
    sample = (
        Path(__file__).parent.parent.parent
        / "测试用例"
        / "无模板排版"
        / "高一下3月13-原文件.docx"
    )
    if not sample.exists():
        print(f"样例文件不存在: {sample}")
        return False

    parser = DocxParser(str(sample))
    elements = parser.extract_content()

    output_dir = Path(__file__).parent.parent / "data" / "test_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / "table_fix_test_preserve.docx")

    generator = DocxGenerator()
    generator.generate_from_elements(elements, {}, preserve_format=True)
    generator.save(output_path)
    print(f"\n保留格式输出: {output_path}")

    output_path2 = str(output_dir / "table_fix_test_style.docx")
    style_def = {
        "body": {"font": {"name": "宋体", "size": 12}, "format": {}},
        "table": {"font": {"name": "宋体", "size": 12}, "format": {}},
    }
    generator2 = DocxGenerator()
    generator2.generate_from_elements(elements, style_def, preserve_format=False)
    generator2.save(output_path2)
    print(f"样式模式输出: {output_path2}")

    reparsed = DocxParser(output_path)
    re_elements = reparsed.extract_content()
    re_tables = [e for e in re_elements if e.element_type == ElementType.TABLE]

    print(f"\n=== 回归验证 ===")
    print(
        f"原始表格数: {len([e for e in elements if e.element_type == ElementType.TABLE])}"
    )
    print(f"回解析表格数: {len(re_tables)}")

    ok = True
    for t_idx, (orig_t, re_t) in enumerate(
        zip(
            [e for e in elements if e.element_type == ElementType.TABLE],
            re_tables,
        )
    ):
        for r_idx, (orig_row, re_row) in enumerate(
            zip(orig_t.table_cells, re_t.table_cells)
        ):
            for c_idx, (orig_cell, re_cell) in enumerate(zip(orig_row, re_row)):
                if orig_cell.v_merge == "continue":
                    continue

                orig_text = orig_cell.text.strip()
                re_text = re_cell.text.strip()

                if orig_text != re_text:
                    print(
                        f"  MISMATCH 表{t_idx} Cell[{r_idx},{c_idx}]: "
                        f"原文={orig_text[:60]!r} 回解析={re_text[:60]!r}"
                    )
                    ok = False

                re_para_count = len(re_cell.paragraph_runs)
                orig_para_count = len(orig_cell.paragraph_runs)
                if re_para_count != orig_para_count:
                    print(
                        f"  段落数不一致 表{t_idx} Cell[{r_idx},{c_idx}]: "
                        f"原文={orig_para_count} 回解析={re_para_count} "
                        f"text={orig_text[:40]!r}"
                    )
                    ok = False

    if ok:
        print("  所有表格单元格文本和段落数验证通过!")

    return ok


if __name__ == "__main__":
    print("=" * 60)
    print("1. 测试 paragraph_runs 解析")
    print("=" * 60)
    ok1 = test_table_cell_paragraph_runs()

    print("\n" + "=" * 60)
    print("2. 测试表格写入回环")
    print("=" * 60)
    ok2 = test_table_roundtrip()

    print("\n" + "=" * 60)
    if ok1 and ok2:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)

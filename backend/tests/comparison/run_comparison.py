"""DOCX对比入口脚本

用法:
    cd backend
    python tests/comparison/run_comparison.py
"""

import asyncio
import sys
import os
import time
import json
from pathlib import Path

# 设置路径
SCRIPT_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from pipeline_runner import PipelineRunner
from docx_comparator import DocxComparator
from report_generator import ReportGenerator, FileComparisonResult


# 路径配置
PDF_DIR = BACKEND_DIR.parent / "测试用例" / "原生PDF"
REF_DIR = BACKEND_DIR.parent / "测试用例" / "网上下载的英语资料样例"
OUTPUT_DIR = BACKEND_DIR / "data" / "comparison_output"
REPORT_PATH = OUTPUT_DIR / "comparison_report.json"


def find_reference_docx(pdf_stem: str) -> Path:
    """查找对应的参考DOCX文件"""
    # 精确匹配
    ref = REF_DIR / f"{pdf_stem}.docx"
    if ref.exists():
        return ref

    # 模糊匹配
    for candidate in REF_DIR.glob("*.docx"):
        if pdf_stem[:30] in candidate.stem or candidate.stem[:30] in pdf_stem:
            return candidate

    return None


def progress_callback(index: int, total: int, filename: str, success: bool, time_or_error):
    """进度回调"""
    short_name = filename[:50] + "..." if len(filename) > 50 else filename
    if success:
        print(f"[{index:2d}/{total}] {short_name:<55} 处理完成 {time_or_error:.1f}s")
    else:
        print(f"[{index:2d}/{total}] {short_name:<55} 处理失败: {time_or_error}")


async def main():
    """主函数"""
    print("=" * 120)
    print("DOCX对比测试 - PDF处理流程 + 与参考文件全面对比")
    print("=" * 120)
    print(f"PDF目录: {PDF_DIR}")
    print(f"参考目录: {REF_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print()

    # 检查目录
    if not PDF_DIR.exists():
        print(f"错误: PDF目录不存在: {PDF_DIR}")
        return 1
    if not REF_DIR.exists():
        print(f"错误: 参考目录不存在: {REF_DIR}")
        return 1

    # 获取PDF文件列表
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        print("错误: 没有找到PDF文件")
        return 1

    print(f"找到 {len(pdf_files)} 个PDF文件\n")

    # 匹配参考文件
    file_pairs = []
    for pdf in pdf_files:
        ref = find_reference_docx(pdf.stem)
        if ref:
            file_pairs.append((pdf, ref))
        else:
            print(f"警告: 未找到参考文件: {pdf.name}")

    print(f"成功匹配 {len(file_pairs)}/{len(pdf_files)} 个文件\n")

    if not file_pairs:
        print("错误: 没有匹配的文件对")
        return 1

    # Step 1: 批量处理PDF
    print("-" * 120)
    print("Step 1: 批量处理PDF → DOCX")
    print("-" * 120)

    runner = PipelineRunner(OUTPUT_DIR)
    pdf_paths = [pdf for pdf, _ in file_pairs]
    pipeline_results = await runner.run_all(pdf_paths, progress_callback)

    # Step 2: 批量对比
    print()
    print("-" * 120)
    print("Step 2: 对比生成文件与参考文件")
    print("-" * 120)

    comparator = DocxComparator()
    reporter = ReportGenerator()
    comparison_results = []

    for i, (pdf, ref) in enumerate(file_pairs, 1):
        gen_path, proc_time, error = pipeline_results.get(pdf.name, (None, 0.0, "未处理"))

        if error:
            result = FileComparisonResult(
                file_name=pdf.name,
                ref_name=ref.name,
                overall_score=0.0,
                dimension_scores={},
                dimension_details={},
                processing_time=proc_time,
                comparison_time=0.0,
                success=False,
                error=error,
            )
            comparison_results.append(result)
            short_name = pdf.name[:50] + "..." if len(pdf.name) > 50 else pdf.name
            print(f"[{i:2d}/{len(file_pairs)}] {short_name:<55} 跳过(处理失败)")
            continue

        # 执行对比
        result = comparator.compare(gen_path, ref)
        result.processing_time = proc_time
        comparison_results.append(result)

        short_name = pdf.name[:50] + "..." if len(pdf.name) > 50 else pdf.name
        print(
            f"[{i:2d}/{len(file_pairs)}] {short_name:<55} "
            f"总分:{result.overall_score*100:5.1f}% "
            f"匹配率:{result.paragraph_match_rate*100:5.1f}% "
            f"对比:{result.comparison_time:.1f}s"
        )

    # Step 3: 生成报告
    print()
    print("-" * 120)
    print("Step 3: 生成报告")
    print("-" * 120)

    report = reporter.generate_aggregate_report(comparison_results)
    reporter.save_report(report, REPORT_PATH)
    reporter.print_console_summary(comparison_results)

    # 打印失败的文件
    failed = [r for r in comparison_results if not r.success]
    if failed:
        print(f"\n失败的文件 ({len(failed)}):")
        for r in failed:
            print(f"  - {r.file_name}: {r.error}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

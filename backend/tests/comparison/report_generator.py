"""报告生成器 - JSON + 控制台输出"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


@dataclass
class FileComparisonResult:
    """单个文件的对比结果"""
    file_name: str
    ref_name: str
    overall_score: float
    dimension_scores: Dict[str, float]  # name -> score
    dimension_details: Dict[str, Any]   # name -> details
    processing_time: float
    comparison_time: float
    success: bool
    error: Optional[str] = None
    paragraph_match_rate: float = 0.0


class ReportGenerator:
    """报告生成器"""

    # 维度中文名映射
    DIM_NAMES_ZH = {
        "text_content": "文字内容",
        "paragraph_structure": "段落结构",
        "font_formatting": "字体格式",
        "paragraph_formatting": "段落格式",
        "list_numbering": "列表编号",
        "table_comparison": "表格",
        "image_comparison": "图片",
        "headers_footers": "页眉页脚",
        "page_layout": "页面布局",
        "document_structure": "文档结构",
        "style_system": "样式体系",
    }

    def generate_file_report(self, result: FileComparisonResult) -> Dict[str, Any]:
        """生成单个文件的详细报告"""
        return {
            "file_name": result.file_name,
            "ref_name": result.ref_name,
            "overall_score": round(result.overall_score, 4),
            "paragraph_match_rate": round(result.paragraph_match_rate, 4),
            "processing_time_s": round(result.processing_time, 2),
            "comparison_time_s": round(result.comparison_time, 2),
            "success": result.success,
            "error": result.error,
            "dimensions": {
                name: {
                    "score": round(score, 4),
                    "details": result.dimension_details.get(name, {}),
                }
                for name, score in result.dimension_scores.items()
            },
        }

    def generate_aggregate_report(
        self, results: List[FileComparisonResult]
    ) -> Dict[str, Any]:
        """生成聚合报告"""
        successful = [r for r in results if r.success]

        if not successful:
            return {
                "summary": {
                    "total_files": len(results),
                    "successful": 0,
                    "failed": len(results),
                    "error": "所有文件处理失败",
                },
                "files": [self.generate_file_report(r) for r in results],
            }

        # 总体统计
        overall_scores = [r.overall_score for r in successful]
        proc_times = [r.processing_time for r in successful]
        comp_times = [r.comparison_time for r in successful]
        match_rates = [r.paragraph_match_rate for r in successful]

        # 各维度统计
        dimension_averages = {}
        all_dims = set()
        for r in successful:
            all_dims.update(r.dimension_scores.keys())

        for dim_name in sorted(all_dims):
            scores = [r.dimension_scores.get(dim_name, 0.0) for r in successful]
            dimension_averages[dim_name] = {
                "avg": round(sum(scores) / len(scores), 4),
                "min": round(min(scores), 4),
                "max": round(max(scores), 4),
                "zh_name": self.DIM_NAMES_ZH.get(dim_name, dim_name),
            }

        return {
            "summary": {
                "total_files": len(results),
                "successful": len(successful),
                "failed": len(results) - len(successful),
                "avg_overall_score": round(sum(overall_scores) / len(overall_scores), 4),
                "min_overall_score": round(min(overall_scores), 4),
                "max_overall_score": round(max(overall_scores), 4),
                "avg_paragraph_match_rate": round(sum(match_rates) / len(match_rates), 4),
                "avg_processing_time": round(sum(proc_times) / len(proc_times), 2),
                "avg_comparison_time": round(sum(comp_times) / len(comp_times), 2),
                "total_processing_time": round(sum(proc_times), 2),
            },
            "dimension_averages": dimension_averages,
            "files": [self.generate_file_report(r) for r in results],
        }

    def print_console_summary(self, results: List[FileComparisonResult]):
        """打印控制台摘要"""
        successful = [r for r in results if r.success]
        if not successful:
            print("\n没有成功的文件，无法生成摘要。")
            return

        # 获取所有维度名
        all_dims = []
        for r in successful:
            for d in r.dimension_scores:
                if d not in all_dims:
                    all_dims.append(d)

        # 计算列宽
        name_width = 50
        score_width = 7

        # 打印表头
        print("\n" + "=" * 120)
        print("DOCX对比报告摘要")
        print("=" * 120)
        print(f"处理文件数: {len(results)} | 成功: {len(successful)} | 失败: {len(results) - len(successful)}")
        print("-" * 120)

        # 表头
        header = f"{'文件名':<{name_width}} {'总分':>{score_width}}"
        dim_short_names = {
            "text_content": "文字",
            "paragraph_structure": "段落",
            "font_formatting": "字体",
            "paragraph_formatting": "格式",
            "list_numbering": "编号",
            "table_comparison": "表格",
            "image_comparison": "图片",
            "headers_footers": "页眉",
            "page_layout": "页面",
            "document_structure": "结构",
            "style_system": "样式",
        }
        for dim in all_dims:
            short = dim_short_names.get(dim, dim[:4])
            header += f" {short:>{score_width}}"
        header += f" {'匹配率':>{score_width}}"
        print(header)
        print("-" * 120)

        # 每行数据
        for r in sorted(successful, key=lambda x: x.overall_score, reverse=True):
            name = r.file_name[:name_width]
            if len(r.file_name) > name_width:
                name = r.file_name[: name_width - 3] + "..."
            line = f"{name:<{name_width}} {r.overall_score*100:>{score_width}.1f}"
            for dim in all_dims:
                score = r.dimension_scores.get(dim, 0.0)
                line += f" {score*100:>{score_width}.1f}"
            line += f" {r.paragraph_match_rate*100:>{score_width}.1f}"
            print(line)

        # 平均值
        print("-" * 120)
        avg_line = f"{'平均':<{name_width}} {sum(r.overall_score for r in successful)/len(successful)*100:>{score_width}.1f}"
        for dim in all_dims:
            scores = [r.dimension_scores.get(dim, 0.0) for r in successful]
            avg_line += f" {sum(scores)/len(scores)*100:>{score_width}.1f}"
        avg_line += f" {sum(r.paragraph_match_rate for r in successful)/len(successful)*100:>{score_width}.1f}"
        print(avg_line)

        # 最低值
        min_line = f"{'最低':<{name_width}} {min(r.overall_score for r in successful)*100:>{score_width}.1f}"
        for dim in all_dims:
            scores = [r.dimension_scores.get(dim, 0.0) for r in successful]
            min_line += f" {min(scores)*100:>{score_width}.1f}"
        min_line += f" {min(r.paragraph_match_rate for r in successful)*100:>{score_width}.1f}"
        print(min_line)

        print("=" * 120)

    def save_report(self, report: Dict[str, Any], output_path: Path):
        """保存JSON报告"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n报告已保存: {output_path}")

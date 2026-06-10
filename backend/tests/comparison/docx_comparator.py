"""核心DOCX对比器"""

import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.docx.parser import DocxParser, ContentElement, ElementType
from paragraph_matcher import ParagraphMatcher
from scoring import ScoringEngine, OverallScore
from report_generator import FileComparisonResult

# 导入所有维度
from dimensions.text_content import TextContentDimension
from dimensions.paragraph_structure import ParagraphStructureDimension
from dimensions.font_formatting import FontFormattingDimension
from dimensions.paragraph_formatting import ParagraphFormattingDimension
from dimensions.list_numbering import ListNumberingDimension
from dimensions.table_comparison import TableComparisonDimension
from dimensions.image_comparison import ImageComparisonDimension
from dimensions.headers_footers import HeadersFootersDimension
from dimensions.page_layout import PageLayoutDimension
from dimensions.document_structure import DocumentStructureDimension
from dimensions.style_system import StyleSystemDimension


class DocxComparator:
    """DOCX文件对比器"""

    def __init__(self):
        dims = [
            TextContentDimension(),
            ParagraphStructureDimension(),
            FontFormattingDimension(),
            ParagraphFormattingDimension(),
            ListNumberingDimension(),
            TableComparisonDimension(),
            ImageComparisonDimension(),
            HeadersFootersDimension(),
            PageLayoutDimension(),
            DocumentStructureDimension(),
            StyleSystemDimension(),
        ]
        # 设置权重
        weight_map = {
            "text_content": 0.20,
            "paragraph_structure": 0.10,
            "font_formatting": 0.12,
            "paragraph_formatting": 0.10,
            "list_numbering": 0.05,
            "table_comparison": 0.13,
            "image_comparison": 0.08,
            "headers_footers": 0.05,
            "page_layout": 0.05,
            "document_structure": 0.07,
            "style_system": 0.05,
        }
        for d in dims:
            d.weight = weight_map.get(d.name, d.weight)
        self.dimensions = dims

    def compare(self, generated_path: Path, reference_path: Path) -> FileComparisonResult:
        """执行完整对比

        Args:
            generated_path: 生成的DOCX文件路径
            reference_path: 参考DOCX文件路径

        Returns:
            FileComparisonResult对象
        """
        start_time = time.time()

        try:
            # Step 1: 解析两个文件
            gen_parser = DocxParser(str(generated_path))
            gen_elements = gen_parser.extract_content()

            ref_parser = DocxParser(str(reference_path))
            ref_elements = ref_parser.extract_content()

            # Step 2: 段落匹配
            matcher = ParagraphMatcher(gen_elements, ref_elements)
            match_result = matcher.match()

            # Step 3: 执行各维度对比
            dimension_results = []
            dimension_scores = {}
            dimension_details = {}

            for dim in self.dimensions:
                try:
                    score, details = dim.compare(
                        gen_elements, ref_elements,
                        generated_path, reference_path,
                        match_result=match_result,
                    )
                    dimension_results.append((dim.name, score, dim.weight, details))
                    dimension_scores[dim.name] = score
                    dimension_details[dim.name] = details
                except Exception as e:
                    # 单个维度失败不影响其他维度
                    dimension_results.append((dim.name, 0.0, dim.weight, {"error": str(e)}))
                    dimension_scores[dim.name] = 0.0
                    dimension_details[dim.name] = {"error": str(e)}

            # Step 4: 计算加权总分
            overall = ScoringEngine.calculate(dimension_results)

            comparison_time = time.time() - start_time

            return FileComparisonResult(
                file_name=generated_path.name,
                ref_name=reference_path.name,
                overall_score=overall.overall,
                dimension_scores=dimension_scores,
                dimension_details=dimension_details,
                processing_time=0.0,  # 由调用方填充
                comparison_time=comparison_time,
                success=True,
                paragraph_match_rate=match_result.match_rate,
            )

        except Exception as e:
            comparison_time = time.time() - start_time
            return FileComparisonResult(
                file_name=generated_path.name,
                ref_name=reference_path.name,
                overall_score=0.0,
                dimension_scores={},
                dimension_details={},
                processing_time=0.0,
                comparison_time=comparison_time,
                success=False,
                error=str(e),
            )

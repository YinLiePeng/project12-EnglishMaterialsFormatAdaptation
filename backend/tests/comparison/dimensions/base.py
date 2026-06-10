"""对比维度基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.docx.parser import ContentElement, ElementType


class ComparisonDimension(ABC):
    """对比维度基类"""

    name: str = "base"
    weight: float = 0.0
    description: str = ""

    @abstractmethod
    def compare(
        self,
        gen_elements: List[ContentElement],
        ref_elements: List[ContentElement],
        gen_path: Path,
        ref_path: Path,
        match_result: Any = None,
    ) -> Tuple[float, Dict[str, Any]]:
        """执行对比

        Args:
            gen_elements: 生成文件的ContentElement列表
            ref_elements: 参考文件的ContentElement列表
            gen_path: 生成文件路径（用于需要python-docx直接读取的场景）
            ref_path: 参考文件路径
            match_result: 段落匹配结果（ParagraphMatcherOutput）

        Returns:
            (score, details): 分数 [0.0, 1.0] 和详细信息
        """
        pass

    @staticmethod
    def _mean(values: List[float]) -> float:
        """计算平均值"""
        if not values:
            return 0.0
        return sum(values) / len(values)

    @staticmethod
    def _safe_div(a: float, b: float) -> float:
        """安全除法"""
        if b == 0:
            return 1.0
        return a / b

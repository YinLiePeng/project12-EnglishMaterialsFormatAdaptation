"""加权评分引擎"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


@dataclass
class DimensionScore:
    """单个维度的评分"""
    name: str
    score: float  # [0.0, 1.0]
    weight: float
    weighted_score: float
    details: Dict[str, Any]


@dataclass
class OverallScore:
    """总评分"""
    overall: float  # 加权总分 [0.0, 1.0]
    dimensions: List[DimensionScore] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": round(self.overall, 4),
            "dimensions": {
                d.name: {
                    "score": round(d.score, 4),
                    "weight": d.weight,
                    "weighted_score": round(d.weighted_score, 4),
                    "details": d.details,
                }
                for d in self.dimensions
            },
        }


class ScoringEngine:
    """评分引擎"""

    @staticmethod
    def calculate(
        dimension_results: List[tuple],  # List[(name, score, weight, details)]
    ) -> OverallScore:
        """计算加权总分

        Args:
            dimension_results: [(维度名, 分数, 权重, 详情)]

        Returns:
            OverallScore对象
        """
        dimensions = []
        total_weighted = 0.0
        total_weight = 0.0

        for name, score, weight, details in dimension_results:
            # 确保分数在有效范围内
            score = max(0.0, min(1.0, score or 0.0))
            weighted = score * weight

            dimensions.append(
                DimensionScore(
                    name=name,
                    score=score,
                    weight=weight,
                    weighted_score=weighted,
                    details=details or {},
                )
            )

            total_weighted += weighted
            total_weight += weight

        # 归一化（如果权重总和不为1）
        if total_weight > 0:
            overall = total_weighted / total_weight
        else:
            overall = 0.0

        return OverallScore(overall=overall, dimensions=dimensions)

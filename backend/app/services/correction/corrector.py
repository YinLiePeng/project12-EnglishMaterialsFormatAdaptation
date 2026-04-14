"""内容纠错器 - 三层纠错机制"""

import json
import re
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from ..llm.client import DeepSeekClient
from .dictionary import dictionary_manager
from ...core.config import get_prompts


class CorrectionType(str, Enum):
    """纠错类型"""

    SPELLING = "spelling"  # 拼写错误
    PUNCTUATION = "punctuation"  # 标点错误
    WHITESPACE = "whitespace"  # 空格/换行问题
    MOJIBAKE = "mojibake"  # 乱码字符
    SUSPECTED = "suspected"  # 疑似问题


class CorrectionAction(str, Enum):
    """纠错操作"""

    REPLACE = "replace"  # 替换（自动修正）
    ANNOTATE = "annotate"  # 标注（仅标注不修正）
    KEEP = "keep"  # 保留


@dataclass
class CorrectionItem:
    """单条纠错结果"""

    type: CorrectionType
    original: str
    replacement: str
    action: CorrectionAction
    reason: str
    confidence: float
    position: Optional[Dict[str, Any]] = None

    @property
    def paragraph_index(self) -> int:
        return self.position.get("paragraph", 0) if self.position else 0

    @property
    def original_text(self) -> str:
        return self.original

    @property
    def corrected_text(self) -> str:
        return self.replacement

    @property
    def correction_type(self) -> "CorrectionType":
        return self.type


@dataclass
class CorrectionResult:
    """纠错结果集合"""

    corrections: List[CorrectionItem] = field(default_factory=list)


class ContentCorrector:
    """内容纠错器"""

    def __init__(self):
        self.llm_client = DeepSeekClient()
        # 加载词典
        dictionary_manager.load_all()

    async def correct(
        self, paragraphs: List[Dict[str, Any]], use_llm: bool = True
    ) -> CorrectionResult:
        """纠错处理

        Args:
            paragraphs: 段落列表
            use_llm: 是否使用大模型

        Returns:
            CorrectionResult 纠错结果集合
        """
        results: List[CorrectionItem] = []

        # 第一级：大模型识别错误
        if use_llm:
            llm_results = await self._llm_correct(paragraphs)
            results.extend(llm_results)

        # 第二级：硬规则验证
        results = self._apply_hard_rules(results, paragraphs)

        # 第三级：核心区域权限检查
        results = self._check_core_area_permissions(results, paragraphs)

        return CorrectionResult(corrections=results)

    async def correct_with_llm(
        self, paragraphs: List[Dict[str, Any]], llm_client=None
    ) -> CorrectionResult:
        """纠错处理（兼容upload.py调用）

        Args:
            paragraphs: 段落列表
            llm_client: 大模型客户端（可选）

        Returns:
            CorrectionResult 纠错结果集合
        """
        use_llm = llm_client is not None
        return await self.correct(paragraphs, use_llm=use_llm)

    async def _llm_correct(
        self, paragraphs: List[Dict[str, Any]]
    ) -> List[CorrectionItem]:
        """使用大模型识别错误"""
        # 构建内容文本
        content_lines = []
        for i, para in enumerate(paragraphs):
            text = para.get("text", "")[:300]
            content_lines.append(f"[{i}] {text}")

        content = "\n".join(content_lines)

        try:
            # 从配置中获取提示词
            prompts = get_prompts()
            correction_prompt = prompts.get(
                "correction", "你是一个英语教学资料纠错助手"
            )

            response = await self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "你是一个英语教学资料纠错助手"},
                    {
                        "role": "user",
                        "content": correction_prompt.format(content=content),
                    },
                ],
                temperature=0.2,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )

            data = json.loads(response)
            return self._parse_llm_results(data)

        except Exception as e:
            print(f"大模型纠错失败: {e}")
            return []

    def _parse_llm_results(self, data: Dict[str, Any]) -> List[CorrectionItem]:
        """解析大模型返回的结果"""
        results = []

        for item in data.get("results", []):
            type_str = item.get("type", "suspected")
            original = item.get("original", "")
            replacement = item.get("replacement", "")
            action_str = item.get("action", "annotate")
            reason = item.get("reason", "")
            position = item.get("position", {})

            # 转换类型
            correction_type = CorrectionType.SUSPECTED
            for ct in CorrectionType:
                if ct.value == type_str:
                    correction_type = ct
                    break

            # 转换操作
            if action_str == "replace":
                action = CorrectionAction.REPLACE
            elif action_str == "annotate":
                action = CorrectionAction.ANNOTATE
            else:
                action = CorrectionAction.KEEP

            results.append(
                CorrectionItem(
                    type=correction_type,
                    original=original,
                    replacement=replacement,
                    action=action,
                    reason=reason,
                    confidence=data.get("confidence", 0.8),
                    position=position,
                )
            )

        return results

    def _apply_hard_rules(
        self, results: List[CorrectionItem], paragraphs: List[Dict[str, Any]]
    ) -> List[CorrectionItem]:
        """应用硬规则验证"""
        validated_results = []

        for result in results:
            if (
                result.type == CorrectionType.SPELLING
                and result.action == CorrectionAction.REPLACE
            ):
                # 拼写错误需要双重词典验证
                if dictionary_manager.can_auto_correct(result.original):
                    validated_results.append(result)
                else:
                    # 降级为仅标注
                    result.action = CorrectionAction.ANNOTATE
                    result.reason += "（未通过词典验证）"
                    validated_results.append(result)
            else:
                validated_results.append(result)

        return validated_results

    def _check_core_area_permissions(
        self, results: List[CorrectionItem], paragraphs: List[Dict[str, Any]]
    ) -> List[CorrectionItem]:
        """检查核心区域权限"""
        # 核心区域识别规则
        question_patterns = [
            re.compile(r"^\d+[\.\)、]"),  # 题号
            re.compile(r"^[\(（]\d+[）\)]"),  # (1)
        ]

        option_patterns = [
            re.compile(r"^[A-D][\.\)、]"),  # A.
            re.compile(r"^[\(（][A-D][）\)]"),  # (A)
        ]

        validated_results = []

        for result in results:
            para_index = result.position.get("paragraph", 0) if result.position else 0
            if para_index >= len(paragraphs):
                validated_results.append(result)
                continue

            para_text = paragraphs[para_index].get("text", "")

            # 检查是否在核心区域
            is_core_area = False
            for pattern in question_patterns:
                if pattern.match(para_text.strip()):
                    is_core_area = True
                    break

            for pattern in option_patterns:
                if pattern.match(para_text.strip()):
                    is_core_area = True
                    break

            # 核心区域内限制修改类型
            if is_core_area:
                # 只允许修正标点、空格、乱码
                allowed_types = [
                    CorrectionType.PUNCTUATION,
                    CorrectionType.WHITESPACE,
                    CorrectionType.MOJIBAKE,
                ]

                if result.type not in allowed_types:
                    result.action = CorrectionAction.ANNOTATE
                    result.reason += "（核心区域禁止修改）"

            validated_results.append(result)

        return validated_results


# 全局内容纠错器实例
content_corrector = ContentCorrector()

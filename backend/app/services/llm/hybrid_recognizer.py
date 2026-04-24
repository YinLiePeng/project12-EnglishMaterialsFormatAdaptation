"""混合内容结构识别器（规则引擎 + 大模型）"""

from typing import List, Dict, Any
from .client import deepseek_client, DeepSeekClient
from .models import ContentType as LLMContentType
from ..docx.rule_engine import (
    RuleEngine,
    ContentStructure,
    ContentType as RuleContentType,
)


class HybridStructureRecognizer:
    """混合内容结构识别器

    策略：
    1. 先用规则引擎快速识别
    2. 对置信度低的段落，使用大模型进行语义分析
    3. 合并结果，取置信度高的
    """

    def __init__(self):
        self.rule_engine = RuleEngine()
        self.llm_client = deepseek_client

    async def recognize(
        self, paragraphs: List[Dict[str, Any]], use_llm: bool = False
    ) -> List[ContentStructure]:
        """识别内容结构

        Args:
            paragraphs: 段落信息列表
            use_llm: 是否启用大模型

        Returns:
            内容结构识别结果列表
        """
        # 第一层：规则引擎识别
        rule_results = self._rule_based_recognize(paragraphs)

        # 如果不启用大模型，直接返回规则结果
        if not use_llm:
            return rule_results

        # 找出置信度低的段落（需要大模型判断）
        low_confidence_indices = [
            i for i, r in enumerate(rule_results) if r.confidence < 0.8
        ]

        # 如果所有段落置信度都高，不需要调用大模型
        if not low_confidence_indices:
            return rule_results

        # 第二层：大模型识别
        try:
            llm_results = await self.llm_client.recognize_structure(paragraphs)

            if llm_results and llm_results.results:
                # 合并结果
                rule_results = self._merge_results(
                    rule_results,
                    llm_results.results,
                    low_confidence_indices,
                    paragraphs,
                )
        except Exception as e:
            print(f"大模型识别失败，使用规则引擎结果: {e}")

        return rule_results

    def _rule_based_recognize(self, paragraphs: List[Dict]) -> List[ContentStructure]:
        """基于规则的识别"""
        results = []

        for i, para in enumerate(paragraphs):
            text = para.get("text", "")
            font_size = para.get("font_size", 12)
            font_bold = para.get("font_bold", False)
            alignment = para.get("alignment", "left")

            content_type, confidence = self.rule_engine.identify_content_type(
                text, font_size, font_bold, alignment
            )

            style_hint = self.rule_engine._get_style_hint(content_type)

            results.append(
                ContentStructure(
                    index=i,
                    text=text,
                    content_type=content_type,
                    confidence=confidence,
                    style_hint=style_hint,
                )
            )

        return results

    def _merge_results(
        self,
        rule_results: List[ContentStructure],
        llm_results: list,
        low_confidence_indices: List[int],
        paragraphs: List[Dict],
    ) -> List[ContentStructure]:
        """合并规则引擎和大模型的结果

        策略：对于低置信度段落，如果大模型置信度更高，则使用大模型结果
        """
        # 创建LLM结果的索引映射
        llm_map = {r.index: r for r in llm_results}

        for i in low_confidence_indices:
            if i in llm_map:
                llm_result = llm_map[i]
                rule_result = rule_results[i]

                # 如果大模型置信度更高，使用大模型结果
                if llm_result.confidence > rule_result.confidence:
                    # 转换内容类型
                    content_type = self._convert_content_type(llm_result.content_type)
                    style_hint = self.rule_engine._get_style_hint(content_type)

                    rule_results[i] = ContentStructure(
                        index=i,
                        text=paragraphs[i].get("text", ""),
                        content_type=content_type,
                        confidence=llm_result.confidence,
                        style_hint=style_hint,
                    )

        return rule_results

    def _convert_content_type(self, llm_type: LLMContentType) -> RuleContentType:
        """将LLM的内容类型转换为规则引擎的内容类型"""
        mapping = {
            LLMContentType.TITLE: RuleContentType.TITLE,
            LLMContentType.HEADING: RuleContentType.HEADING,
            LLMContentType.QUESTION_NUMBER: RuleContentType.QUESTION_NUMBER,
            LLMContentType.OPTION: RuleContentType.OPTION,
            LLMContentType.BODY: RuleContentType.BODY,
            LLMContentType.ANSWER: RuleContentType.ANSWER,
            LLMContentType.ANALYSIS: RuleContentType.ANALYSIS,
        }
        return mapping.get(llm_type, RuleContentType.BODY)


# 全局混合识别器实例
hybrid_recognizer = HybridStructureRecognizer()

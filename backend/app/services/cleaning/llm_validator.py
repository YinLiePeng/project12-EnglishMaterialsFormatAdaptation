"""大模型清洗校验器"""

import json
from typing import List, Dict, Any, Optional
from ..llm.client import DeepSeekClient
from .cleaner import CleanResult, CleanAction
from ...core.config import get_prompts


class LLMCleanValidator:
    """大模型清洗校验器"""

    def __init__(self):
        self.client = DeepSeekClient()

    async def validate(self, paragraphs: List[Dict[str, Any]]) -> List[CleanResult]:
        """使用大模型校验清洗结果

        Args:
            paragraphs: 段落列表

        Returns:
            清洗结果列表
        """
        # 构建内容文本
        content_lines = []
        for i, para in enumerate(paragraphs):
            text = para.get("text", "")[:200]  # 限制长度
            content_lines.append(f"[{i}] {text}")

        content = "\n".join(content_lines)

        # 调用大模型
        try:
            # 从配置中获取提示词
            prompts = get_prompts()
            cleaning_prompt = prompts.get("cleaning", "你是一个教学资料清洗助手")

            response = await self.client.chat_completion(
                messages=[
                    {"role": "system", "content": "你是一个教学资料清洗助手"},
                    {
                        "role": "user",
                        "content": cleaning_prompt.format(content=content),
                    },
                ],
                temperature=0.2,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )

            # 解析响应
            data = json.loads(response)
            return self._parse_results(data, paragraphs)

        except Exception as e:
            print(f"大模型清洗校验失败: {e}")
            return []

    def _parse_results(
        self, data: Dict[str, Any], paragraphs: List[Dict[str, Any]]
    ) -> List[CleanResult]:
        """解析大模型返回的结果"""
        results = []

        for item in data.get("results", []):
            content = item.get("content", "")
            action_str = item.get("action", "annotate")
            reason = item.get("reason", "")
            position = item.get("position", {})

            # 转换操作类型
            if action_str == "delete":
                action = CleanAction.DELETE
            elif action_str == "annotate":
                action = CleanAction.ANNOTATE
            else:
                action = CleanAction.KEEP

            # 获取置信度
            confidence = data.get("confidence", 0.8)

            results.append(
                CleanResult(
                    text=content,
                    action=action,
                    reason=reason,
                    confidence=confidence,
                    position=position,
                )
            )

        return results


# 全局大模型清洗校验器实例
llm_clean_validator = LLMCleanValidator()

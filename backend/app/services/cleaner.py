"""内容清洗服务 - 规则过滤 + 大模型校验"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from ..core.config import get_prompts


class CleanAction(str, Enum):
    """清洗动作"""

    KEEP = "keep"  # 保留
    DELETE = "delete"  # 删除
    MARK = "mark"  # 标记（添加批注）


@dataclass
class CleanResult:
    """清洗结果"""

    index: int
    original_text: str
    cleaned_text: str
    action: CleanAction
    reason: str
    confidence: float = 1.0


class ContentCleaner:
    """内容清洗器"""

    # 垃圾内容规则
    GARBAGE_RULES = {
        # URL规则
        "URL": re.compile(r"https?://[^\s]+|www\.[^\s]+"),
        # 邮箱规则
        "邮箱": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        # 电话号码规则
        "电话": re.compile(
            r"(\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}"
        ),
        # 版权声明
        "版权": re.compile(
            r"版权所有|©|Copyright|All\s+rights\s+reserved", re.IGNORECASE
        ),
        # 免责声明
        "免责": re.compile(r"免责声明|声明：|Disclaimer", re.IGNORECASE),
        # 二维码转译文本
        "二维码": re.compile(
            r"扫码|扫描二维码|微信关注|关注我们|公众号", re.IGNORECASE
        ),
        # 广告关键词
        "广告": re.compile(
            r"立即购买|优惠|限时|点击这里|免费试用|注册送|下单立减", re.IGNORECASE
        ),
        # 网站水印
        "水印": re.compile(
            r"更多内容请访问|来源：|出自：|资料来源|下载地址", re.IGNORECASE
        ),
        # 乱码字符（20个以上连续非ASCII非中文字符）
        "乱码": re.compile(r"[^\x00-\x7F\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef]{20,}"),
        # 文件路径
        "文件路径": re.compile(r"[A-Z]:\\[^\s]+|/[^\s]+/[^\s]+"),
        # 版本号/文件名
        "版本": re.compile(r"v\d+\.\d+\.\d+|\.exe|\.zip|\.rar", re.IGNORECASE),
    }

    def __init__(self, enable_llm: bool = False):
        self.enable_llm = enable_llm

    def clean_by_rules(self, paragraphs: List[Dict[str, Any]]) -> List[CleanResult]:
        """基于规则的内容清洗"""
        results = []

        for i, para in enumerate(paragraphs):
            text = para.get("text", "")
            action, reason = self._check_garbage(text)

            results.append(
                CleanResult(
                    index=i,
                    original_text=text,
                    cleaned_text="" if action == CleanAction.DELETE else text,
                    action=action,
                    reason=reason,
                    confidence=1.0,
                )
            )

        return results

    async def clean_with_llm(
        self, paragraphs: List[Dict[str, Any]], llm_client=None
    ) -> List[CleanResult]:
        """基于规则 + 大模型的内容清洗"""
        # 先用规则过滤
        rule_results = self.clean_by_rules(paragraphs)

        # 如果没有大模型客户端，直接返回规则结果
        if not llm_client or not self.enable_llm:
            return rule_results

        # 对于规则判断为保留的内容，使用大模型进行二次校验
        try:
            llm_results = await self._llm_verify(rule_results, paragraphs, llm_client)

            # 合并结果
            for i, llm_result in enumerate(llm_results):
                if llm_result and llm_result.action != CleanAction.KEEP:
                    rule_results[i] = llm_result

        except Exception as e:
            print(f"大模型校验失败，使用规则结果: {e}")

        return rule_results

    def _check_garbage(self, text: str) -> tuple:
        """检查是否为垃圾内容"""
        if not text.strip():
            return CleanAction.DELETE, "空内容"

        for rule_name, pattern in self.GARBAGE_RULES.items():
            if pattern.search(text):
                return CleanAction.DELETE, f"匹配{rule_name}规则"

        return CleanAction.KEEP, ""

    async def _llm_verify(
        self,
        rule_results: List[CleanResult],
        paragraphs: List[Dict[str, Any]],
        llm_client,
    ) -> List[Optional[CleanResult]]:
        """使用大模型进行垃圾内容校验"""
        # 构建需要校验的内容
        to_verify = []
        for i, result in enumerate(rule_results):
            if result.action == CleanAction.KEEP:
                to_verify.append(
                    {
                        "index": i,
                        "text": paragraphs[i].get("text", "")[:200],  # 限制长度
                    }
                )

        if not to_verify:
            return [None] * len(rule_results)

        # 构建内容文本
        content_text = "\n".join([f"[{v['index']}] {v['text']}" for v in to_verify])

        # 从配置中获取提示词
        prompts = get_prompts()
        cleaning_prompt = prompts.get("cleaning", "你是一个教学资料清洗助手")

        try:
            import json

            response = await llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "你是一个内容审核专家"},
                    {
                        "role": "user",
                        "content": cleaning_prompt.format(content=content_text),
                    },
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            data = json.loads(response)

            # 创建结果列表
            results = [None] * len(rule_results)

            for item in data.get("results", []):
                idx = item.get("index")
                if idx is not None and 0 <= idx < len(rule_results):
                    action_str = item.get("action", "keep")
                    action = (
                        CleanAction.DELETE
                        if action_str == "delete"
                        else (
                            CleanAction.MARK
                            if action_str == "mark"
                            else CleanAction.KEEP
                        )
                    )

                    results[idx] = CleanResult(
                        index=idx,
                        original_text=paragraphs[idx].get("text", ""),
                        cleaned_text=""
                        if action == CleanAction.DELETE
                        else paragraphs[idx].get("text", ""),
                        action=action,
                        reason=item.get("reason", "大模型判断"),
                        confidence=item.get("confidence", 0.8),
                    )

            return results

        except Exception as e:
            print(f"大模型校验失败: {e}")
            return [None] * len(rule_results)

    def apply_cleaning(
        self, paragraphs: List[Dict[str, Any]], clean_results: List[CleanResult]
    ) -> List[Dict[str, Any]]:
        """应用清洗结果"""
        cleaned_paragraphs = []

        for i, (para, result) in enumerate(zip(paragraphs, clean_results)):
            if result.action == CleanAction.DELETE:
                # 跳过删除的内容
                continue
            elif result.action == CleanAction.MARK:
                # 标记的内容保留，但添加标记
                para["clean_mark"] = result.reason
                cleaned_paragraphs.append(para)
            else:
                cleaned_paragraphs.append(para)

        return cleaned_paragraphs


# 全局内容清洗器实例
content_cleaner = ContentCleaner()

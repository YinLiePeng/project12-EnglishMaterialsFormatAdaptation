"""内容清洗规则引擎"""

import re
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


class CleanAction(str, Enum):
    """清洗操作类型"""

    DELETE = "delete"  # 删除
    KEEP = "keep"  # 保留
    ANNOTATE = "annotate"  # 仅标注


@dataclass
class CleanResult:
    """清洗结果"""

    text: str
    action: CleanAction
    reason: str
    confidence: float
    position: Optional[Dict[str, int]] = None


class ContentCleaner:
    """内容清洗器 - 基于规则的垃圾内容识别"""

    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict[str, re.Pattern]:
        """加载垃圾内容识别规则"""
        return {
            # URL规则
            "url": re.compile(r"https?://[^\s]+", re.IGNORECASE),
            # 邮箱规则
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            # 电话号码规则
            "phone": re.compile(
                r"(\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}"
            ),
            # 版权声明规则
            "copyright": re.compile(
                r"版权所有|©|Copyright|All rights reserved|版权", re.IGNORECASE
            ),
            # 免责声明规则
            "disclaimer": re.compile(r"免责声明|声明|Disclaimer", re.IGNORECASE),
            # 二维码相关规则
            "qrcode": re.compile(
                r"扫码|扫描二维码|微信关注|关注我们|长按识别", re.IGNORECASE
            ),
            # 广告关键词规则
            "advertisement": re.compile(
                r"立即购买|优惠|限时|点击这里|免费试用|注册送|领取|优惠券|折扣|促销",
                re.IGNORECASE,
            ),
            # 网站水印规则
            "watermark": re.compile(
                r"更多内容请访问|来源：|出自：|资料来源|下载地址|原文链接",
                re.IGNORECASE,
            ),
            # 乱码规则（连续20个以上非ASCII非中文字符）
            "garbled": re.compile(r"[^\x00-\x7F\u4e00-\u9fa5]{20,}"),
            # 多余空白规则
            "excessive_whitespace": re.compile(r"\n{3,}|\s{5,}"),
            # 网站名称/平台标识
            "platform_name": re.compile(
                r"百度文库|道客巴巴|豆丁网|原创力文档|淘豆网", re.IGNORECASE
            ),
        }

    def clean_text(self, text: str) -> List[CleanResult]:
        """清洗单个文本

        Args:
            text: 待清洗的文本

        Returns:
            清洗结果列表
        """
        results = []

        for rule_name, pattern in self.rules.items():
            matches = pattern.finditer(text)
            for match in matches:
                matched_text = match.group()
                start = match.start()
                end = match.end()

                # 根据规则类型确定处理方式
                action, reason, confidence = self._get_action_for_rule(
                    rule_name, matched_text
                )

                results.append(
                    CleanResult(
                        text=matched_text,
                        action=action,
                        reason=reason,
                        confidence=confidence,
                        position={"start": start, "end": end},
                    )
                )

        return results

    def _get_action_for_rule(self, rule_name: str, matched_text: str) -> tuple:
        """根据规则类型确定处理方式"""
        # 高置信度删除的规则
        high_confidence_delete = [
            "url",
            "email",
            "phone",
            "qrcode",
            "advertisement",
            "garbled",
        ]
        if rule_name in high_confidence_delete:
            return (
                CleanAction.DELETE,
                f"匹配{self._get_rule_description(rule_name)}规则",
                0.9,
            )

        # 中等置信度的规则
        medium_confidence = ["copyright", "disclaimer", "watermark", "platform_name"]
        if rule_name in medium_confidence:
            return (
                CleanAction.ANNOTATE,
                f"疑似{self._get_rule_description(rule_name)}",
                0.7,
            )

        # 默认保留
        return (CleanAction.KEEP, "不确定内容", 0.5)

    def _get_rule_description(self, rule_name: str) -> str:
        """获取规则描述"""
        descriptions = {
            "url": "网址链接",
            "email": "邮箱地址",
            "phone": "电话号码",
            "copyright": "版权声明",
            "disclaimer": "免责声明",
            "qrcode": "二维码相关",
            "advertisement": "广告内容",
            "watermark": "网站水印",
            "garbled": "乱码字符",
            "excessive_whitespace": "多余空白",
            "platform_name": "平台标识",
        }
        return descriptions.get(rule_name, "垃圾内容")

    def clean_paragraphs(
        self, paragraphs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """清洗段落列表

        Args:
            paragraphs: 段落列表，每个包含text字段

        Returns:
            清洗后的段落列表
        """
        cleaned_paragraphs = []

        for para in paragraphs:
            text = para.get("text", "")
            results = self.clean_text(text)

            # 过滤掉需要删除的内容
            should_delete = False
            for result in results:
                if result.action == CleanAction.DELETE and result.confidence >= 0.8:
                    should_delete = True
                    break

            if not should_delete:
                cleaned_paragraphs.append(para)

        return cleaned_paragraphs


# 全局内容清洗器实例
content_cleaner = ContentCleaner()

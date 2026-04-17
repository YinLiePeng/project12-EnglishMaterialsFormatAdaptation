import re
from typing import List, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass


class ContentType(Enum):
    """内容类型枚举"""

    TITLE = "title"  # 主标题
    HEADING = "heading"  # 子标题
    QUESTION_NUMBER = "question_number"  # 题号
    OPTION = "option"  # 选项
    BODY = "body"  # 正文
    ANSWER = "answer"  # 答案
    ANALYSIS = "analysis"  # 解析


@dataclass
class ContentStructure:
    """内容结构识别结果"""

    index: int
    text: str
    content_type: ContentType
    confidence: float
    style_hint: str  # 建议使用的样式key


class RuleEngine:
    """规则引擎 - 识别内容结构"""

    # 题号模式
    QUESTION_PATTERNS = [
        r"^\s*\d+[\.\)、]",  # 1. 2) 3、
        r"^\s*[\(（]\d+[）\)]",  # (1) （1）
        r"^\s*第[一二三四五六七八九十\d]+[题节部分]",  # 第一题
    ]

    # 选项模式
    OPTION_PATTERNS = [
        r"^\s*[A-D][\.\)、]",  # A. B) C、
        r"^\s*[\(（][A-D][）\)]",  # (A) （B）
        r"^\s*[①②③④⑤⑥⑦⑧⑨⑩]",  # ①②③
    ]

    # 答案模式
    ANSWER_PATTERNS = [
        r"^\s*答案\s*[：:]\s*",
        r"^\s*正确答案\s*[：:]\s*",
        r"^\s*Answer\s*[：:]\s*",
    ]

    # 解析模式
    ANALYSIS_PATTERNS = [
        r"^\s*解析\s*[：:]\s*",
        r"^\s*分析\s*[：:]\s*",
        r"^\s*Explanation\s*[：:]\s*",
    ]

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """预编译正则表达式"""
        self.question_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.QUESTION_PATTERNS
        ]
        self.option_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.OPTION_PATTERNS
        ]
        self.answer_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.ANSWER_PATTERNS
        ]
        self.analysis_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.ANALYSIS_PATTERNS
        ]

    def identify_content_type(
        self,
        text: str,
        font_size: float = 12.0,
        font_bold: bool = False,
        alignment: str = "left",
    ) -> Tuple[ContentType, float]:
        """识别内容类型

        Returns:
            (内容类型, 置信度)
        """
        text_stripped = text.strip()

        if not text_stripped:
            return ContentType.BODY, 1.0

        # 1. 检查是否是题号
        for pattern in self.question_patterns:
            if pattern.match(text_stripped):
                return ContentType.QUESTION_NUMBER, 0.95

        # 2. 检查是否是选项
        for pattern in self.option_patterns:
            if pattern.match(text_stripped):
                return ContentType.OPTION, 0.9

        # 3. 检查是否是答案
        for pattern in self.answer_patterns:
            if pattern.match(text_stripped):
                return ContentType.ANSWER, 0.9

        # 4. 检查是否是解析
        for pattern in self.analysis_patterns:
            if pattern.match(text_stripped):
                return ContentType.ANALYSIS, 0.9

        # 5. 根据格式特征判断标题
        if font_size >= 18 and alignment == "center":
            return ContentType.TITLE, 0.85
        elif font_size >= 14 and font_bold:
            return ContentType.HEADING, 0.8
        elif font_size >= 16 and alignment == "center":
            return ContentType.HEADING, 0.75

        # 6. 默认为正文
        return ContentType.BODY, 0.7

    def analyze_structure(
        self, paragraphs: List[Dict[str, Any]]
    ) -> List[ContentStructure]:
        """分析文档内容结构

        Args:
            paragraphs: 段落信息列表，每个包含 text, font_size, font_bold, alignment

        Returns:
            内容结构识别结果列表
        """
        results = []

        for i, para in enumerate(paragraphs):
            text = para.get("text", "")
            font_size = para.get("font_size", 12.0)
            font_bold = para.get("font_bold", False)
            alignment = para.get("alignment", "left")

            content_type, confidence = self.identify_content_type(
                text, font_size, font_bold, alignment
            )

            # 确定建议的样式
            style_hint = self._get_style_hint(content_type)

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

    def _get_style_hint(self, content_type: ContentType) -> str:
        """根据内容类型获取样式建议"""
        mapping = {
            ContentType.TITLE: "heading1",
            ContentType.HEADING: "heading2",
            ContentType.QUESTION_NUMBER: "question_number",
            ContentType.OPTION: "option",
            ContentType.BODY: "body",
            ContentType.ANSWER: "body",
            ContentType.ANALYSIS: "body",
        }
        return mapping.get(content_type, "body")

    def get_content_type_name(self, content_type: ContentType) -> str:
        """获取内容类型的中文名称"""
        names = {
            ContentType.TITLE: "主标题",
            ContentType.HEADING: "子标题",
            ContentType.QUESTION_NUMBER: "题号",
            ContentType.OPTION: "选项",
            ContentType.BODY: "正文",
            ContentType.ANSWER: "答案",
            ContentType.ANALYSIS: "解析",
        }
        return names.get(content_type, "正文")


# 全局规则引擎实例
rule_engine = RuleEngine()

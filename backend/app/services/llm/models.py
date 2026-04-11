"""LLM服务数据模型"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional


class ContentType(str, Enum):
    """内容类型"""

    TITLE = "title"  # 主标题
    HEADING = "heading"  # 子标题
    QUESTION_NUMBER = "question_number"  # 题号
    OPTION = "option"  # 选项
    BODY = "body"  # 正文
    ANSWER = "answer"  # 答案
    ANALYSIS = "analysis"  # 解析


class ParagraphStructure(BaseModel):
    """单个段落的结构识别结果"""

    index: int = Field(..., description="段落索引")
    content_type: ContentType = Field(..., description="内容类型")


class LLMStructureOutput(BaseModel):
    """大模型结构识别的完整输出"""

    results: List[ParagraphStructure] = Field(
        default_factory=list, description="所有段落的识别结果"
    )
    overall_confidence: float = Field(default=0.8, description="整体置信度", ge=0, le=1)
    summary: Optional[str] = Field(default=None, description="总结说明")

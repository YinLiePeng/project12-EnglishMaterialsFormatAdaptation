"""OCR服务模块 - 双方案兼容

默认使用LLM Vision（复用现有DeepSeek/Qwen客户端）
预留百度OCR接口（后续可配置切换）

配置: .env 中 OCR_BACKEND=llm_vision|baidu
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class OCRPageResult:
    """单页OCR识别结果"""
    page_num: int
    text: str
    confidence: float
    blocks: List[Dict[str, Any]]
    processing_time: float = 0.0


@dataclass
class OCRResult:
    """完整PDF的OCR识别结果"""
    pages: List[OCRPageResult]
    total_text: str
    total_pages: int
    avg_confidence: float
    pdf_type_detected: str = "scanned"


class BaseOCRService(ABC):
    """OCR服务抽象基类"""

    @abstractmethod
    async def recognize_page(self, image_bytes: bytes, page_num: int = 0) -> OCRPageResult:
        """识别单页图片"""
        ...

    @abstractmethod
    async def recognize_pdf(self, pdf_path: str, page_range: Optional[List[int]] = None) -> OCRResult:
        """识别PDF文件"""
        ...

    @abstractmethod
    def get_name(self) -> str:
        """获取OCR引擎名称"""
        ...


def get_ocr_service() -> BaseOCRService:
    """根据配置获取OCR服务实例"""
    from app.core.config import settings

    backend = getattr(settings, "OCR_BACKEND", "llm_vision")

    if backend == "baidu":
        from .baidu import BaiduOCRService
        return BaiduOCRService()
    else:
        from .llm_vision import LLMVisionOCRService
        return LLMVisionOCRService()


__all__ = [
    "BaseOCRService",
    "OCRPageResult",
    "OCRResult",
    "get_ocr_service",
]

"""百度OCR服务 - 预留实现

需要配置 BAIDU_OCR_API_KEY 和 BAIDU_OCR_SECRET_KEY
支持教育场景专项识别（试卷、手写作文等）
"""

import time
from typing import List, Optional

from . import BaseOCRService, OCRPageResult, OCRResult


class BaiduOCRService(BaseOCRService):
    """百度智能云OCR服务"""

    def __init__(self):
        from app.core.config import settings

        self.api_key = settings.BAIDU_OCR_API_KEY
        self.secret_key = settings.BAIDU_OCR_SECRET_KEY
        self.access_token = None

    def get_name(self) -> str:
        return "baidu"

    async def _ensure_token(self):
        """确保access_token有效"""
        if self.access_token:
            return

        import httpx

        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            self.access_token = data["access_token"]

    async def recognize_page(self, image_bytes: bytes, page_num: int = 0) -> OCRPageResult:
        """使用百度OCR识别单页"""
        start_time = time.time()

        try:
            await self._ensure_token()

            import httpx
            import base64

            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic?access_token={self.access_token}"

            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = {"image": b64_image}

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, headers=headers, data=data)
                response.raise_for_status()
                result = response.json()

            words = result.get("words_result", [])
            text = "\n".join(w.get("words", "") for w in words)
            confidence = result.get("log_id", 0) and len(words) > 0

            blocks = []
            for w in words:
                blocks.append({
                    "type": "text",
                    "text": w.get("words", ""),
                    "confidence": 0.9,
                })

            return OCRPageResult(
                page_num=page_num,
                text=text,
                confidence=0.85 if words else 0.0,
                blocks=blocks,
                processing_time=round(time.time() - start_time, 2),
            )
        except Exception:
            return OCRPageResult(
                page_num=page_num,
                text="",
                confidence=0.0,
                blocks=[],
                processing_time=round(time.time() - start_time, 2),
            )

    async def recognize_pdf(
        self, pdf_path: str, page_range: Optional[List[int]] = None
    ) -> OCRResult:
        """识别整个PDF文件"""
        import fitz

        doc = fitz.open(pdf_path)
        total_pages = len(doc)

        if page_range is None:
            page_range = list(range(total_pages))

        page_results = []
        for page_num in page_range:
            if page_num >= total_pages:
                continue

            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_bytes = pix.tobytes("png")

            result = await self.recognize_page(img_bytes, page_num)
            page_results.append(result)

        doc.close()

        total_text = "\n\n".join(p.text for p in page_results if p.text)
        avg_conf = (
            sum(p.confidence for p in page_results) / len(page_results)
            if page_results
            else 0.0
        )

        return OCRResult(
            pages=page_results,
            total_text=total_text,
            total_pages=len(page_results),
            avg_confidence=round(avg_conf, 2),
            pdf_type_detected="scanned",
        )

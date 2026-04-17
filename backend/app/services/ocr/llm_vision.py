"""LLM Vision OCR - 使用大模型视觉能力识别扫描版PDF"""

import base64
import json
import time
from typing import List, Optional

from . import BaseOCRService, OCRPageResult, OCRResult


class LLMVisionOCRService(BaseOCRService):
    """使用LLM视觉模型进行OCR识别

    复用现有DeepSeek/Qwen客户端，将PDF页面渲染为图片后发送给大模型。
    优势：无需额外账号，大模型能同时做OCR+结构识别。
    """

    OCR_SYSTEM_PROMPT = """你是一个专业的OCR识别助手，专门处理英语教学资料的文字识别。

【任务说明】
请仔细识别图片中的所有文字内容，特别注意以下几点：
1. 英语单词的拼写准确性（包括大小写）
2. 音标符号的准确识别（如 /æ/, /ɪ/, /ˈ/ 等）
3. 标点符号（区分中英文标点）
4. 题号和选项的完整识别
5. 表格内容的结构化提取

【输出要求】
严格按照以下JSON格式输出识别结果：

{
  "text": "完整识别的文本内容（保持原始段落结构）",
  "blocks": [
    {
      "type": "paragraph",
      "text": "段落文本",
      "confidence": 0.95
    }
  ],
  "confidence": 0.9,
  "quality_note": "如有识别不确定的地方请说明"
}

注意：
- 保持原始的段落结构和换行
- 如果有识别不确定的字符，在quality_note中说明
- 题目选项保持 A. B. C. D. 格式
- 不要添加任何解释性文字，只输出JSON"""

    def get_name(self) -> str:
        return "llm_vision"

    async def recognize_page(self, image_bytes: bytes, page_num: int = 0) -> OCRPageResult:
        """使用LLM视觉模型识别单页图片"""
        start_time = time.time()

        from app.services.llm.client import deepseek_client

        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        messages = [
            {
                "role": "system",
                "content": self.OCR_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请识别这张图片中的所有文字内容。",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64_image}"
                        },
                    },
                ],
            },
        ]

        try:
            response = await deepseek_client.chat_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=8192,
            )

            result = self._parse_ocr_response(response)
            processing_time = time.time() - start_time

            return OCRPageResult(
                page_num=page_num,
                text=result.get("text", ""),
                confidence=result.get("confidence", 0.8),
                blocks=result.get("blocks", []),
                processing_time=round(processing_time, 2),
            )
        except Exception as e:
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

        start_time = time.time()

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

    def _parse_ocr_response(self, response: str) -> dict:
        """解析LLM OCR响应"""
        try:
            data = json.loads(response)
            return data
        except json.JSONDecodeError:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                try:
                    data = json.loads(response[json_start:json_end])
                    return data
                except json.JSONDecodeError:
                    pass

            return {
                "text": response,
                "blocks": [{"type": "paragraph", "text": response, "confidence": 0.5}],
                "confidence": 0.5,
                "quality_note": "LLM返回非JSON格式，使用原始文本",
            }

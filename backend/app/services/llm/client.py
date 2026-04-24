"""DeepSeek API客户端"""

import httpx
import json
from typing import Optional, List, Dict, Any, AsyncGenerator, Tuple
from app.core.config import settings, get_prompts
from .models import LLMStructureOutput


class DeepSeekClient:
    """DeepSeek API客户端"""

    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL or "https://api.deepseek.com"
        self.model = settings.LLM_MODEL or "deepseek-chat"
        self.timeout = 120

    def _build_structure_messages(
        self,
        paragraphs: List[Dict[str, Any]],
        custom_prompt: str = None,
        style_description: str = None,
    ) -> Tuple[list, str]:
        """构建结构识别的消息列表

        Returns:
            (messages, content_text) 元组
        """
        content_lines = []
        for i, para in enumerate(paragraphs):
            text = para.get("text", "")[:100]
            font_size = para.get("font_size", 12)
            font_bold = para.get("font_bold", False)
            alignment = para.get("alignment", "left")

            content_lines.append(
                f"[{i}] 字号:{font_size}pt 加粗:{font_bold} 对齐:{alignment} | {text}"
            )

        content = "\n".join(content_lines)

        prompts = get_prompts()
        system_prompt = custom_prompt or prompts.get(
            "structure_recognition", "你是一个英语教学资料结构分析专家"
        )

        if style_description and "{style_description}" in system_prompt:
            system_prompt = system_prompt.replace(
                "{style_description}", style_description
            )

        user_prompt = f"请分析以下内容的结构类型，以json格式输出：\n\n{content}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        return messages, content

    @staticmethod
    def _parse_structure_output(raw_content: str) -> Optional[LLMStructureOutput]:
        """从原始文本中解析结构识别结果"""
        try:
            data = json.loads(raw_content)
            return LLMStructureOutput(**data)
        except (json.JSONDecodeError, Exception):
            json_start = raw_content.find("{")
            json_end = raw_content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                try:
                    data = json.loads(raw_content[json_start:json_end])
                    return LLMStructureOutput(**data)
                except Exception:
                    return None
            return None

    async def chat_completion(
        self,
        messages: list,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_format: dict = None,
    ) -> str:
        """调用DeepSeek聊天补全API

        Args:
            messages: 消息列表（支持多模态内容）
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式，如 {"type": "json_object"}

        Returns:
            模型响应内容
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", headers=headers, json=payload
            )
            response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            if not content or content.strip() == "":
                raise ValueError("大模型返回了空内容")

            return content

    async def verify_pdf_structure(
        self, para_dicts: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """校验PDF提取内容的结构正确性

        Args:
            para_dicts: 段落信息列表

        Returns:
            校验结果dict，包含results和confidence
        """
        prompts = get_prompts()
        system_prompt = prompts.get(
            "pdf_structure_verification",
            "你是一个专业的文档结构分析助手",
        )

        content_lines = []
        for i, para in enumerate(para_dicts):
            text = para.get("text", "")[:80]
            content_lines.append(f"[{i}] {text}")

        content = "\n".join(content_lines)
        system_prompt = system_prompt.replace("{content}", content)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请校验以上PDF提取内容的结构正确性。"},
        ]

        try:
            response = await self.chat_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
            return json.loads(response)
        except Exception:
            return None

    async def verify_ocr_result(
        self, para_dicts: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """校验OCR识别结果的准确性

        Args:
            para_dicts: 段落信息列表

        Returns:
            校验结果dict，包含results和overall_confidence
        """
        prompts = get_prompts()
        system_prompt = prompts.get(
            "ocr_verification",
            "你是一个专业的英语教学资料校对助手",
        )

        content_lines = []
        for i, para in enumerate(para_dicts):
            text = para.get("text", "")[:100]
            content_lines.append(f"[{i}] {text}")

        content = "\n".join(content_lines)
        system_prompt = system_prompt.replace("{content}", content)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请校验以上OCR识别结果的准确性。"},
        ]

        try:
            response = await self.chat_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
            return json.loads(response)
        except Exception:
            return None

    async def recognize_structure(
        self,
        paragraphs: List[Dict[str, Any]],
        custom_prompt: str = None,
        style_description: str = None,
    ) -> Optional[LLMStructureOutput]:
        """识别内容结构（非流式）

        Args:
            paragraphs: 段落信息列表
            custom_prompt: 自定义系统提示词
            style_description: 排版样式描述

        Returns:
            LLMStructureOutput 或 None
        """
        messages, _ = self._build_structure_messages(
            paragraphs, custom_prompt, style_description
        )

        try:
            response = await self.chat_completion(
                messages=messages,
                temperature=0.2,
                max_tokens=8192,
                response_format={"type": "json_object"},
            )
            return self._parse_structure_output(response)
        except Exception as e:
            print(f"大模型识别失败: {e}")
            return None

    async def recognize_structure_stream(
        self,
        paragraphs: List[Dict[str, Any]],
        custom_prompt: str = None,
        style_description: str = None,
    ) -> AsyncGenerator[Tuple[str, str], None]:
        """流式识别内容结构

        Yields:
            ("chunk", "文本片段") - LLM 输出的文本片段
            ("result", json_string) - 完整的 JSON 结果字符串
            ("error", "错误信息") - 错误信息
        """
        messages, _ = self._build_structure_messages(
            paragraphs, custom_prompt, style_description
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 8192,
            "response_format": {"type": "json_object"},
            "stream": True,
        }

        full_content = ""

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue

                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_content += content
                                yield ("chunk", content)
                        except json.JSONDecodeError:
                            continue

            parsed = self._parse_structure_output(full_content)
            if parsed:
                yield ("result", json.dumps(parsed.model_dump(), ensure_ascii=False))
            else:
                yield ("error", f"无法解析LLM输出为有效JSON结构")

        except httpx.TimeoutException:
            yield ("error", "LLM请求超时")
        except httpx.HTTPStatusError as e:
            yield ("error", f"LLM服务返回错误: {e.response.status_code}")
        except Exception as e:
            yield ("error", f"LLM流式识别失败: {str(e)}")


# 全局DeepSeek客户端实例
deepseek_client = DeepSeekClient()

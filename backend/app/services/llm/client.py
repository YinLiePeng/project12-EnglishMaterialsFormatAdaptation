"""DeepSeek API客户端"""

import httpx
import json
from typing import Optional, List, Dict, Any
from app.core.config import settings, get_prompts
from .models import LLMStructureOutput


class DeepSeekClient:
    """DeepSeek API客户端"""

    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL or "https://api.deepseek.com"
        self.model = settings.LLM_MODEL or "deepseek-chat"
        self.timeout = 60

    async def chat_completion(
        self,
        messages: list,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_format: dict = None,
    ) -> str:
        """调用DeepSeek聊天补全API

        Args:
            messages: 消息列表
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

            # 处理可能的空content
            if not content or content.strip() == "":
                raise ValueError("DeepSeek返回了空内容")

            return content

    async def recognize_structure(
        self, paragraphs: List[Dict[str, Any]]
    ) -> Optional[LLMStructureOutput]:
        """识别内容结构

        Args:
            paragraphs: 段落信息列表，每个包含 text, font_size, font_bold, alignment

        Returns:
            LLMStructureOutput 或 None（失败时）
        """
        # 构建内容文本
        content_lines = []
        for i, para in enumerate(paragraphs):
            text = para.get("text", "")[:100]  # 限制每段长度
            font_size = para.get("font_size", 12)
            font_bold = para.get("font_bold", False)
            alignment = para.get("alignment", "left")

            content_lines.append(
                f"[{i}] 字号:{font_size}pt 加粗:{font_bold} 对齐:{alignment} | {text}"
            )

        content = "\n".join(content_lines)

        # 构建prompt
        user_prompt = f"请分析以下内容的结构类型，以json格式输出：\n\n{content}"

        # 从配置中获取系统提示词
        prompts = get_prompts()
        system_prompt = prompts.get(
            "structure_recognition", "你是一个英语教学资料结构分析专家"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            # 调用DeepSeek API，使用JSON模式
            response = await self.chat_completion(
                messages=messages,
                temperature=0.2,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )

            # 解析JSON响应
            data = json.loads(response)
            return LLMStructureOutput(**data)

        except Exception as e:
            print(f"大模型识别失败: {e}")
            return None


# 全局DeepSeek客户端实例
deepseek_client = DeepSeekClient()

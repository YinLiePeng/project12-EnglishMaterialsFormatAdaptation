"""结构分析格式化工具

将规则引擎/LLM的识别结果格式化为前端友好的结构，
并附加将要应用的样式详情。
"""

import json
from typing import List, Dict, Any
from ..core.presets.styles import get_style_mapping


class StructureFormatter:
    """结构分析格式化器"""

    # 内容类型中文映射
    CONTENT_TYPE_NAMES = {
        "title": "主标题",
        "heading": "子标题",
        "question_number": "题号",
        "option": "选项",
        "body": "正文",
        "answer": "答案",
        "analysis": "解析",
    }

    # 样式中文名称映射
    STYLE_KEY_NAMES = {
        "heading1": "一级标题",
        "heading2": "二级标题",
        "heading3": "三级标题",
        "body": "正文",
        "question_number": "题号",
        "option": "选项",
    }

    def format_rule_engine_results(
        self,
        structures: List[Any],  # ContentStructure 对象列表
        style_mapping: dict,
        paragraphs: List[Any],  # ParagraphInfo 对象列表
    ) -> dict:
        """格式化规则引擎的识别结果

        Args:
            structures: ContentStructure 对象列表
            style_mapping: 样式映射（从预设样式获取）
            paragraphs: ParagraphInfo 对象列表

        Returns:
            前端友好的结构分析数据
        """
        formatted_paragraphs = []

        for struct in structures:
            # 获取样式详情
            style_key = struct.style_hint
            style_def = style_mapping.get(style_key, {})
            applied_style = self._format_style_details(style_key, style_def)

            # 获取段落文本（完整文本）和原始样式
            para_index = struct.index
            text = ""
            original_style = {
                "font_name": "宋体",
                "font_size": 12.0,
                "font_bold": False,
                "alignment": "left",
            }

            if para_index < len(paragraphs):
                para = paragraphs[para_index]
                text = para.text
                # 提取原始样式信息
                if hasattr(para, "font"):
                    original_style["font_name"] = para.font.name or "宋体"
                    original_style["font_size"] = para.font.size or 12.0
                    original_style["font_bold"] = para.font.bold or False
                if hasattr(para, "format"):
                    original_style["alignment"] = para.format.alignment or "left"
            elif hasattr(struct, "text"):
                text = struct.text

            formatted_paragraphs.append(
                {
                    "index": struct.index,
                    "text": text,  # 完整文本
                    "original_style": original_style,
                    "content_type": struct.content_type.value,
                    "content_type_name": self.CONTENT_TYPE_NAMES.get(
                        struct.content_type.value, "未知"
                    ),
                    "confidence": struct.confidence,
                    "applied_style": applied_style,
                    "reason": getattr(struct, "reason", ""),
                }
            )

        return {
            "method": "rule_engine",
            "overall_confidence": self._calculate_overall_confidence(
                formatted_paragraphs
            ),
            "paragraphs": formatted_paragraphs,
            "summary": f"共识别 {len(formatted_paragraphs)} 个段落",
        }

    def format_llm_results(
        self,
        llm_output: Any,  # LLMStructureOutput 对象
        style_mapping: dict,
        rule_engine: Any,  # 用于获取 style_hint
        paragraphs: List[Any] = None,  # 段落信息列表（用于获取完整文本和原始样式）
    ) -> dict:
        """格式化LLM的识别结果

        Args:
            llm_output: LLMStructureOutput 对象
            style_mapping: 样式映射
            rule_engine: 规则引擎实例（用于获取style_hint）
            paragraphs: ParagraphInfo 对象列表（用于获取完整文本和原始样式）

        Returns:
            前端友好的结构分析数据
        """
        formatted_paragraphs = []

        for result in llm_output.results:
            # 获取内容类型
            content_type = result.content_type.value

            # 使用规则引擎获取样式提示
            from ..docx.rule_engine import ContentType

            style_hint = rule_engine._get_style_hint(ContentType(content_type))

            # 获取样式详情
            style_def = style_mapping.get(style_hint, {})
            applied_style = self._format_style_details(style_hint, style_def)

            # 获取完整文本和原始样式
            text = result.reason or ""
            original_style = {
                "font_name": "宋体",
                "font_size": 12.0,
                "font_bold": False,
                "alignment": "left",
            }

            if paragraphs and result.index < len(paragraphs):
                para = paragraphs[result.index]
                text = para.text
                if hasattr(para, "font"):
                    original_style["font_name"] = para.font.name or "宋体"
                    original_style["font_size"] = para.font.size or 12.0
                    original_style["font_bold"] = para.font.bold or False
                if hasattr(para, "format"):
                    original_style["alignment"] = para.format.alignment or "left"

            formatted_paragraphs.append(
                {
                    "index": result.index,
                    "text": text,  # 完整文本
                    "original_style": original_style,
                    "content_type": content_type,
                    "content_type_name": self.CONTENT_TYPE_NAMES.get(
                        content_type, "未知"
                    ),
                    "confidence": result.confidence,
                    "applied_style": applied_style,
                    "reason": result.reason,
                }
            )

        return {
            "method": "llm",
            "overall_confidence": llm_output.overall_confidence,
            "paragraphs": formatted_paragraphs,
            "summary": llm_output.summary
            or f"共识别 {len(formatted_paragraphs)} 个段落",
        }

    def _format_style_details(self, style_key: str, style_def: dict) -> dict:
        """格式化样式详情

        Args:
            style_key: 样式键（如 heading1）
            style_def: 样式定义

        Returns:
            格式化后的样式信息
        """
        if not style_def:
            return {
                "key": style_key,
                "name": self.STYLE_KEY_NAMES.get(style_key, style_key),
                "font": {"name": "默认", "size": 12, "bold": False},
                "format": {"alignment": "left", "line_spacing": 1.5},
            }

        return {
            "key": style_key,
            "name": self.STYLE_KEY_NAMES.get(style_key, style_key),
            "font": {
                "name": style_def.get("font", {}).get("name", "宋体"),
                "size": style_def.get("font", {}).get("size", 12),
                "bold": style_def.get("font", {}).get("bold", False),
                "color": style_def.get("font", {}).get("color", "000000"),
            },
            "format": {
                "alignment": style_def.get("format", {}).get("alignment", "left"),
                "line_spacing": style_def.get("format", {}).get("line_spacing", 1.5),
                "space_before": style_def.get("format", {}).get("space_before", 0),
                "space_after": style_def.get("format", {}).get("space_after", 0),
                "first_line_indent": style_def.get("format", {}).get(
                    "first_line_indent", 0
                ),
            },
        }

    def _calculate_overall_confidence(self, paragraphs: List[dict]) -> float:
        """计算整体置信度

        Args:
            paragraphs: 段落列表

        Returns:
            平均置信度
        """
        if not paragraphs:
            return 0.0

        total_confidence = sum(p["confidence"] for p in paragraphs)
        return round(total_confidence / len(paragraphs), 2)

    def compare_structures(
        self, old_structure: dict, new_structure: dict
    ) -> List[Dict[str, Any]]:
        """对比两个结构分析，返回变化列表

        Args:
            old_structure: 旧的结构分析数据
            new_structure: 新的结构分析数据

        Returns:
            变化列表，每个变化包含index, old_type, old_type_name, new_type, new_type_name, reason
        """
        changes = []
        old_paras = {p["index"]: p for p in old_structure.get("paragraphs", [])}
        new_paras = {p["index"]: p for p in new_structure.get("paragraphs", [])}

        for index in new_paras:
            new_para = new_paras[index]
            if index in old_paras:
                old_para = old_paras[index]
                # 检查是否有类型变化
                if old_para["content_type"] != new_para["content_type"]:
                    changes.append(
                        {
                            "index": index,
                            "old_type": old_para["content_type"],
                            "old_type_name": old_para["content_type_name"],
                            "new_type": new_para["content_type"],
                            "new_type_name": new_para["content_type_name"],
                            "reason": new_para.get("reason", "AI重新识别"),
                        }
                    )

        return changes


# 全局格式化器实例
structure_formatter = StructureFormatter()

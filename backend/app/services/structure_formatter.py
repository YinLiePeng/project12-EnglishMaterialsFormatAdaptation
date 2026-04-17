"""结构分析格式化工具

将规则引擎/LLM的识别结果格式化为前端友好的结构，
并附加将要应用的样式详情。
"""

import json
from typing import List, Dict, Any
from ..core.presets.styles import get_style_mapping


class StructureFormatter:
    """结构分析格式化器"""

    CONTENT_TYPE_NAMES = {
        "title": "主标题",
        "heading": "子标题",
        "question_number": "题号",
        "option": "选项",
        "body": "正文",
        "answer": "答案",
        "analysis": "解析",
    }

    STYLE_KEY_NAMES = {
        "heading1": "一级标题",
        "heading2": "二级标题",
        "heading3": "三级标题",
        "body": "正文",
        "question_number": "题号",
        "option": "选项",
    }

    def _extract_original_style(self, para: Any) -> dict:
        """从 ParagraphInfo 提取完整原始样式"""
        original_style = {
            "font_name": "宋体",
            "font_size": 12.0,
            "font_bold": False,
            "font_italic": False,
            "font_underline": False,
            "font_color": "000000",
            "alignment": "left",
            "line_spacing": None,
            "line_spacing_rule": None,
            "space_before": None,
            "space_after": None,
            "first_line_indent": None,
            "left_indent": None,
        }

        if hasattr(para, "font"):
            original_style["font_name"] = para.font.name or "宋体"
            original_style["font_size"] = para.font.size or 12.0
            original_style["font_bold"] = para.font.bold or False
            original_style["font_italic"] = para.font.italic or False
            original_style["font_underline"] = para.font.underline or False
            original_style["font_color"] = para.font.color or "000000"

        if hasattr(para, "format"):
            fmt = para.format
            original_style["alignment"] = fmt.alignment or "left"
            if fmt.line_spacing is not None:
                original_style["line_spacing"] = fmt.line_spacing
            if fmt.line_spacing_rule is not None:
                original_style["line_spacing_rule"] = fmt.line_spacing_rule
            if fmt.space_before is not None:
                original_style["space_before"] = fmt.space_before
            if fmt.space_after is not None:
                original_style["space_after"] = fmt.space_after
            if fmt.first_line_indent is not None:
                original_style["first_line_indent"] = fmt.first_line_indent
            if fmt.left_indent is not None:
                original_style["left_indent"] = fmt.left_indent

        return original_style

    def format_rule_engine_results(
        self,
        structures: List[Any],
        style_mapping: dict,
        paragraphs: List[Any],
    ) -> dict:
        """格式化规则引擎的识别结果"""
        formatted_paragraphs = []
        is_preserve = not style_mapping

        for struct in structures:
            style_key = struct.style_hint
            style_def = style_mapping.get(style_key, {}) if style_mapping else {}

            para_index = struct.index
            text = ""
            original_style = self._extract_original_style_default()

            if para_index < len(paragraphs):
                para = paragraphs[para_index]
                text = para.text
                original_style = self._extract_original_style(para)
            elif hasattr(struct, "text"):
                text = struct.text

            if is_preserve:
                applied_style = self._build_preserve_applied_style(
                    style_key, original_style
                )
            else:
                applied_style = self._format_style_details(style_key, style_def)

            formatted_paragraphs.append(
                {
                    "index": struct.index,
                    "text": text,
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
            "style_map": self._build_style_map(style_mapping),
            "overall_confidence": self._calculate_overall_confidence(
                formatted_paragraphs
            ),
            "paragraphs": formatted_paragraphs,
            "summary": f"共识别 {len(formatted_paragraphs)} 个段落",
        }

    def format_llm_results(
        self,
        llm_output: Any,
        style_mapping: dict,
        rule_engine: Any,
        paragraphs: List[Any] = None,
    ) -> dict:
        """格式化LLM的识别结果"""
        formatted_paragraphs = []
        is_preserve = not style_mapping

        for result in llm_output.results:
            content_type = result.content_type.value

            from ..docx.rule_engine import ContentType

            style_hint = rule_engine._get_style_hint(ContentType(content_type))

            style_def = style_mapping.get(style_hint, {}) if style_mapping else {}

            text = result.reason or ""
            original_style = self._extract_original_style_default()

            if paragraphs and result.index < len(paragraphs):
                para = paragraphs[result.index]
                text = para.text
                original_style = self._extract_original_style(para)

            if is_preserve:
                applied_style = self._build_preserve_applied_style(
                    style_hint, original_style
                )
            else:
                applied_style = self._format_style_details(style_hint, style_def)

            formatted_paragraphs.append(
                {
                    "index": result.index,
                    "text": text,
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
            "style_map": self._build_style_map(style_mapping),
            "overall_confidence": llm_output.overall_confidence,
            "paragraphs": formatted_paragraphs,
            "summary": llm_output.summary
            or f"共识别 {len(formatted_paragraphs)} 个段落",
        }

    CONTENT_TYPE_TO_STYLE_KEY = {
        "title": "heading1",
        "heading": "heading2",
        "question_number": "question_number",
        "option": "option",
        "body": "body",
        "answer": "body",
        "analysis": "body",
    }

    def _build_style_map(self, style_mapping: dict) -> dict:
        """构建 content_type → applied_style 的映射，供前端类型选择器使用"""
        result = {}
        for content_type, style_key in self.CONTENT_TYPE_TO_STYLE_KEY.items():
            if not style_mapping:
                result[content_type] = self._format_style_details(style_key, {})
            else:
                style_def = style_mapping.get(style_key, {})
                result[content_type] = self._format_style_details(style_key, style_def)
        return result

    def _extract_original_style_default(self) -> dict:
        """返回默认的原始样式"""
        return {
            "font_name": "宋体",
            "font_size": 12.0,
            "font_bold": False,
            "font_italic": False,
            "font_underline": False,
            "font_color": "000000",
            "alignment": "left",
            "line_spacing": None,
            "line_spacing_rule": None,
            "space_before": None,
            "space_after": None,
            "first_line_indent": None,
            "left_indent": None,
        }

    def _build_preserve_applied_style(
        self, style_key: str, original_style: dict
    ) -> dict:
        """保留原格式模式下，从原始样式构造 applied_style

        保留模式下生成器直接复制原始格式，所以 applied_style 应反映原始样式。
        """
        return {
            "key": style_key,
            "name": self.STYLE_KEY_NAMES.get(style_key, style_key),
            "font": {
                "name": original_style.get("font_name", "宋体"),
                "size": original_style.get("font_size", 12),
                "bold": original_style.get("font_bold", False),
                "color": original_style.get("font_color", "000000"),
                "italic": original_style.get("font_italic", False),
                "underline": original_style.get("font_underline", False),
            },
            "format": {
                "alignment": original_style.get("alignment", "left"),
                "line_spacing": original_style.get("line_spacing", 1.5),
                "line_spacing_rule": original_style.get("line_spacing_rule"),
                "space_before": original_style.get("space_before", 0),
                "space_after": original_style.get("space_after", 0),
                "first_line_indent": original_style.get("first_line_indent", 0),
                "left_indent": original_style.get("left_indent", 0),
            },
        }

    def _format_style_details(self, style_key: str, style_def: dict) -> dict:
        """格式化样式详情（非保留模式）"""
        if not style_def:
            return {
                "key": style_key,
                "name": self.STYLE_KEY_NAMES.get(style_key, style_key),
                "font": {"name": "默认", "size": 12, "bold": False, "color": "000000"},
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
                "italic": style_def.get("font", {}).get("italic", False),
                "underline": style_def.get("font", {}).get("underline", False),
            },
            "format": {
                "alignment": style_def.get("format", {}).get("alignment", "left"),
                "line_spacing": style_def.get("format", {}).get("line_spacing", 1.5),
                "line_spacing_rule": style_def.get("format", {}).get(
                    "line_spacing_rule"
                ),
                "space_before": style_def.get("format", {}).get("space_before", 0),
                "space_after": style_def.get("format", {}).get("space_after", 0),
                "first_line_indent": style_def.get("format", {}).get(
                    "first_line_indent", 0
                ),
                "left_indent": style_def.get("format", {}).get("left_indent", 0),
            },
        }

    def _calculate_overall_confidence(self, paragraphs: List[dict]) -> float:
        if not paragraphs:
            return 0.0

        total_confidence = sum(p["confidence"] for p in paragraphs)
        return round(total_confidence / len(paragraphs), 2)

    def compare_structures(
        self, old_structure: dict, new_structure: dict
    ) -> List[Dict[str, Any]]:
        changes = []
        old_paras = {p["index"]: p for p in old_structure.get("paragraphs", [])}
        new_paras = {p["index"]: p for p in new_structure.get("paragraphs", [])}

        for index in new_paras:
            new_para = new_paras[index]
            if index in old_paras:
                old_para = old_paras[index]
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


structure_formatter = StructureFormatter()

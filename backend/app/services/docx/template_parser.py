from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class StyleInfo:
    """样式详细信息"""

    name: str
    style_id: str
    base_style: Optional[str]
    font: Dict[str, Any]
    format: Dict[str, Any]
    level: int
    is_valid: bool


class TemplateParser:
    """模板解析器 - 提取模板样式体系"""

    def __init__(self, template_path: str):
        self.template_path = Path(template_path)
        self.doc = Document(template_path)
        self._style_cache: Dict[str, StyleInfo] = {}

    def extract_style_system(self) -> Dict[str, Any]:
        """提取完整的样式体系"""
        styles = {}
        style_tree = []

        for style in self.doc.styles:
            if style.type == 1:  # 段落样式
                style_info = self._analyze_style(style)
                styles[style.name] = {
                    "name": style_info.name,
                    "style_id": style_info.style_id,
                    "base_style": style_info.base_style,
                    "font": style_info.font,
                    "format": style_info.format,
                    "level": style_info.level,
                    "is_valid": style_info.is_valid,
                }
                self._style_cache[style.name] = style_info

        # 构建样式层级树
        level_groups = {}
        for name, info in self._style_cache.items():
            level = info.level
            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(
                {
                    "name": name,
                    "style_id": info.style_id,
                    "font_preview": f"{info.font.get('name', '宋体')} {info.font.get('size', 12)}px",
                    "is_valid": info.is_valid,
                }
            )

        for level in sorted(level_groups.keys()):
            style_tree.append({"level": level, "styles": level_groups[level]})

        # 检测样式层级是否混乱
        has_issues = self._detect_style_issues()

        return {
            "styles": styles,
            "style_tree": style_tree,
            "has_level_issues": has_issues,
            "available_styles": list(styles.keys()),
        }

    def _analyze_style(self, style) -> StyleInfo:
        """分析单个样式"""
        # 计算样式层级
        level = self._calculate_level(style)

        # 提取字体信息
        font = self._extract_font(style)

        # 提取段落格式
        fmt = self._extract_format(style)

        # 检查有效性
        is_valid = self._validate_style(style, level)

        return StyleInfo(
            name=style.name,
            style_id=style.style_id if hasattr(style, "style_id") else style.name,
            base_style=style.base_style.name if style.base_style else None,
            font=font,
            format=fmt,
            level=level,
            is_valid=is_valid,
        )

    def _calculate_level(self, style) -> int:
        """计算样式层级（基于继承关系）"""
        level = 0
        current = style
        visited = set()

        while current.base_style:
            if current.name in visited:
                break
            visited.add(current.name)
            level += 1
            current = current.base_style
            if level > 10:  # 防止过深继承
                break

        return level

    def _extract_font(self, style) -> Dict[str, Any]:
        """提取字体信息"""
        font = style.font

        color = "000000"
        if font.color and font.color.rgb:
            color = str(font.color.rgb)

        return {
            "name": font.name or "宋体",
            "size": font.size.pt if font.size else 12.0,
            "bold": font.bold or False,
            "italic": font.italic or False,
            "color": color,
        }

    def _extract_format(self, style) -> Dict[str, Any]:
        """提取段落格式"""
        pf = style.paragraph_format

        # paragraph_format可能没有alignment属性，需要安全获取
        try:
            alignment = pf.alignment
            # 处理 'start' 等特殊值
            alignment_str = str(alignment).lower()
            if "center" in alignment_str:
                alignment_result = "center"
            elif "right" in alignment_str:
                alignment_result = "right"
            elif "justify" in alignment_str:
                alignment_result = "justify"
            else:
                alignment_result = "left"
        except (AttributeError, Exception):
            alignment_result = "left"

        return {
            "alignment": alignment_result,
            "line_spacing": pf.line_spacing if pf.line_spacing else 1.5,
            "space_before": pf.space_before.pt if pf.space_before else 0.0,
            "space_after": pf.space_after.pt if pf.space_after else 0.0,
            "first_line_indent": pf.first_line_indent.cm
            if pf.first_line_indent
            else 0.0,
            "left_indent": pf.left_indent.cm if pf.left_indent else 0.0,
            "right_indent": pf.right_indent.cm if pf.right_indent else 0.0,
        }

    def _validate_style(self, style, level: int) -> bool:
        """验证样式是否有效"""
        # 检查层级是否过深
        if level > 5:
            return False

        # 检查名称是否有效
        if not style.name or len(style.name) > 100:
            return False

        # 检查基础样式是否存在
        if style.base_style and style.base_style.name not in self._style_cache:
            # 初次分析时可能还未缓存，先标记为有效
            pass

        return True

    def _detect_style_issues(self) -> bool:
        """检测样式层级是否有问题"""
        has_issues = False

        for name, info in self._style_cache.items():
            # 检查基础样式是否有效
            if info.base_style and info.base_style not in self._style_cache:
                info.is_valid = False
                has_issues = True

            # 检查层级是否过深
            if info.level > 5:
                info.is_valid = False
                has_issues = True

        return has_issues

    def find_marker(self, marker: str = "{{CONTENT}}") -> Optional[int]:
        """查找标记位位置"""
        for i, para in enumerate(self.doc.paragraphs):
            if marker in para.text:
                return i
        return None

    def get_marker_info(self, marker: str = "{{CONTENT}}") -> Optional[Dict[str, Any]]:
        """获取标记位的详细信息"""
        for i, para in enumerate(self.doc.paragraphs):
            if marker in para.text:
                # 获取标记位所在段落的样式
                style_name = para.style.name if para.style else "Normal"
                style_info = self._style_cache.get(style_name)

                return {
                    "paragraph_index": i,
                    "style_name": style_name,
                    "style_info": {
                        "font": style_info.font if style_info else {},
                        "format": style_info.format if style_info else {},
                    }
                    if style_info
                    else None,
                }
        return None

    def get_style_for_content_type(self, content_type: str) -> Optional[Dict[str, Any]]:
        """为特定内容类型找到最匹配的样式"""
        # 智能匹配策略
        type_keywords = {
            "title": ["title", "heading 1", "标题", "heading1", "Heading 1"],
            "heading": ["heading", "标题", "Heading 2", "Heading 3"],
            "question_number": ["list number", "题号", "question"],
            "option": ["list bullet", "选项", "option"],
            "body": ["normal", "正文", "body", "Normal"],
        }

        keywords = type_keywords.get(content_type, ["normal"])

        # 先尝试精确匹配
        for style_name, style_info in self._style_cache.items():
            if style_name.lower() in [k.lower() for k in keywords]:
                return {
                    "name": style_name,
                    "font": style_info.font,
                    "format": style_info.format,
                }

        # 再尝试模糊匹配
        for keyword in keywords:
            for style_name, style_info in self._style_cache.items():
                if keyword.lower() in style_name.lower():
                    return {
                        "name": style_name,
                        "font": style_info.font,
                        "format": style_info.format,
                    }

        # 返回Normal样式或第一个可用样式
        if "Normal" in self._style_cache:
            normal = self._style_cache["Normal"]
            return {"name": "Normal", "font": normal.font, "format": normal.format}

        return None

    def get_available_styles(self) -> List[Dict[str, Any]]:
        """获取所有可用样式列表"""
        styles = []
        for name, info in self._style_cache.items():
            styles.append(
                {
                    "name": name,
                    "style_id": info.style_id,
                    "font_preview": f"{info.font.get('name', '宋体')} {info.font.get('size', 12)}px"
                    + (" 加粗" if info.font.get("bold") else ""),
                    "level": info.level,
                    "is_valid": info.is_valid,
                }
            )
        return styles

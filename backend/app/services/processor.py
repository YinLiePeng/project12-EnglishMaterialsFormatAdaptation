"""文档处理服务 - 核心处理逻辑"""

import asyncio
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from docx import Document
from sqlalchemy import select

from .docx import (
    DocxParser,
    DocxGenerator,
    RuleEngine,
    rule_engine,
    TemplateParser,
    ParagraphInfo,
)
from .docx.parser import ContentElement, ElementType
from .docx.format_auditor import format_auditor
from .docx.template_filler import fill_template_zip
from .exception_handler import exception_handler, AppException, ExceptionType
from ..core.presets.styles import get_preset_style, get_style_mapping, is_preserve_style
from .structure_formatter import structure_formatter
from ..models.task import Task
from ..core.database import AsyncSessionLocal


class DocumentProcessor:
    """文档处理器 - 实现三种排版模式"""

    def __init__(self):
        self.rule_engine = rule_engine

    async def process_document(
        self,
        input_file_path: str = None,
        layout_mode: str = "none",
        preset_style: Optional[str] = None,
        template_file_path: Optional[str] = None,
        marker_position_str: Optional[str] = None,
        use_llm: bool = False,
        task_id: Optional[str] = None,
        original_filename: Optional[str] = None,
        elements: Optional[List[ContentElement]] = None,
    ) -> Dict[str, Any]:
        start_time = datetime.now()

        try:
            if elements is None:
                parser = DocxParser(input_file_path)
                elements = parser.extract_content()

            para_elements = [
                e for e in elements if e.element_type == ElementType.PARAGRAPH
            ]

            if not para_elements and not elements:
                raise AppException(
                    ExceptionType.FILE_CORRUPTED, "文档内容为空或无法解析"
                )

            marker_position = None
            if marker_position_str:
                try:
                    marker_position = json.loads(marker_position_str)
                except (json.JSONDecodeError, TypeError):
                    pass

            if layout_mode == "none":
                output_path = await self._process_no_template(
                    elements,
                    preset_style,
                    input_file_path,
                    use_llm,
                    task_id,
                    original_filename,
                )
            elif layout_mode == "empty":
                if not template_file_path:
                    raise AppException(
                        ExceptionType.TEMPLATE_PARSE_FAILED,
                        "空模板模式需要提供模板文件",
                    )
                output_path = await self._process_empty_template(
                    elements,
                    template_file_path,
                    marker_position,
                    preset_style,
                    use_llm,
                    task_id,
                    original_filename,
                )
            elif layout_mode == "complete":
                if not template_file_path:
                    raise AppException(
                        ExceptionType.TEMPLATE_PARSE_FAILED,
                        "完整模板模式需要提供模板文件",
                    )
                output_path = await self._process_complete_template(
                    elements,
                    template_file_path,
                    preset_style,
                    use_llm,
                    task_id,
                    original_filename,
                )
            else:
                raise AppException(
                    ExceptionType.UNKNOWN_ERROR, f"不支持的排版模式: {layout_mode}"
                )

            processing_time = (datetime.now() - start_time).total_seconds()
            return {
                "success": True,
                "output_path": output_path,
                "processing_time": processing_time,
                "paragraph_count": len(para_elements),
                "layout_mode": layout_mode,
            }

        except AppException as e:
            return exception_handler.handle(e)
        except Exception as e:
            return exception_handler.handle(e)

    async def _process_no_template(
        self,
        elements: List[ContentElement],
        preset_style: Optional[str],
        input_file_path: str,
        use_llm: bool,
        task_id: Optional[str],
        original_filename: Optional[str] = None,
    ) -> str:
        """无模板模式：使用预设样式从头生成文档"""

        para_dicts = self._extract_para_dicts(elements)
        structures = await self._run_structure_recognition(
            para_dicts, use_llm, preset_style
        )

        preserve = is_preserve_style(preset_style or "")
        if preserve:
            style_mapping = {}
            style_keys = self._build_style_keys(structures)
        else:
            style_mapping = get_style_mapping(
                get_preset_style(preset_style or "universal")
            )
            style_keys = self._build_style_keys(structures)

        output_path = self._get_output_path(input_file_path, original_filename)
        generator = DocxGenerator()
        generator.generate_from_elements(
            elements, style_mapping, style_keys, preserve_format=preserve
        )
        generator.save(output_path)

        if preserve:
            format_auditor.audit_and_correct(output_path, elements)

        method = "llm" if use_llm else "rule_engine"
        await self._save_structure_analysis(
            structures, para_dicts, style_mapping, task_id, method
        )

        return output_path

    async def _process_empty_template(
        self,
        elements: List[ContentElement],
        template_file_path: str,
        marker_position: Optional[Dict[str, Any]],
        preset_style: Optional[str],
        use_llm: bool,
        task_id: Optional[str],
        original_filename: Optional[str] = None,
    ) -> str:
        """空模板模式：ZIP级保真填充，模板框架字节级不变"""

        para_dicts = self._extract_para_dicts(elements)
        structures = await self._run_structure_recognition(
            para_dicts, use_llm, preset_style
        )

        preserve = is_preserve_style(preset_style or "")
        if preserve:
            style_mapping = {}
            style_keys = self._build_style_keys(structures)
        else:
            style_mapping = get_style_mapping(
                get_preset_style(preset_style or "universal")
            )
            style_keys = self._build_style_keys(structures)

        output_path = self._get_output_path(template_file_path, original_filename)

        fill_template_zip(
            template_path=template_file_path,
            output_path=output_path,
            elements=elements,
            style_mapping=style_mapping,
            style_keys=style_keys,
            preserve_format=preserve,
            marker_position=marker_position,
        )

        await self._save_structure_analysis(
            structures,
            para_dicts,
            style_mapping,
            task_id,
            "llm" if use_llm else "rule_engine",
        )

        return output_path

    async def _process_complete_template(
        self,
        elements: List[ContentElement],
        template_file_path: str,
        preset_style: Optional[str],
        use_llm: bool,
        task_id: Optional[str],
        original_filename: Optional[str] = None,
    ) -> str:
        """完整模板模式：使用模板样式体系排版"""

        template_parser = TemplateParser(template_file_path)
        template_styles = template_parser.extract_style_system()

        content_type_keys = [
            "title",
            "heading",
            "question_number",
            "option",
            "body",
        ]
        style_mapping = {}
        for ct in content_type_keys:
            matched = template_parser.get_style_for_content_type(ct)
            if matched:
                style_key = self._content_type_to_style_key(ct)
                style_mapping[style_key] = {
                    "font": matched.get("font", {}),
                    "format": matched.get("format", {}),
                }

        if "body" not in style_mapping:
            preset = get_preset_style(preset_style or "universal")
            style_mapping["body"] = preset.get("body", {})

        para_dicts = self._extract_para_dicts(elements)
        structures = await self._run_structure_recognition(
            para_dicts, use_llm, preset_style
        )
        style_keys = self._build_style_keys(structures)

        marker_info = template_parser.get_marker_info()
        marker = "{{CONTENT}}"

        output_path = self._get_output_path(template_file_path, original_filename)
        generator = DocxGenerator(template_file_path)
        generator.fill_template_from_elements(
            elements, marker, style_mapping, style_keys
        )
        generator.save(output_path)

        await self._save_structure_analysis(
            structures,
            para_dicts,
            style_mapping,
            task_id,
            "llm" if use_llm else "rule_engine",
        )

        return output_path

    @staticmethod
    def _extract_para_dicts(elements: List[ContentElement]) -> List[Dict[str, Any]]:
        """从内容元素列表中提取段落信息字典列表（供结构识别和预览用）

        包含段落、表格（占位文本）和图片（占位文本），保持原始元素顺序
        """
        result = []
        for e in elements:
            if e.element_type == ElementType.PARAGRAPH and e.paragraph:
                p = e.paragraph
                result.append(
                    {
                        "text": p.text,
                        "font_name": p.font.name,
                        "font_size": p.font.size,
                        "font_bold": p.font.bold,
                        "font_italic": p.font.italic,
                        "font_underline": p.font.underline,
                        "font_color": p.font.color,
                        "alignment": p.format.alignment,
                        "line_spacing": p.format.line_spacing,
                        "line_spacing_rule": p.format.line_spacing_rule,
                        "space_before": p.format.space_before,
                        "space_after": p.format.space_after,
                        "first_line_indent": p.format.first_line_indent,
                        "left_indent": p.format.left_indent,
                        "_element_type": "paragraph",
                    }
                )
            elif e.element_type == ElementType.TABLE and e.table_cells:
                rows = len(e.table_cells)
                cols = max((len(r) for r in e.table_cells), default=0)
                preview_text = f"[表格: {rows}行{cols}列]"
                cell_texts = []
                for row in e.table_cells:
                    for cell in row:
                        if cell.text.strip():
                            cell_texts.append(cell.text.strip())
                if cell_texts:
                    preview_text += " " + " | ".join(cell_texts[:8])
                    if len(cell_texts) > 8:
                        preview_text += " ..."
                result.append(
                    {
                        "text": preview_text,
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
                        "_element_type": "table",
                    }
                )
            elif e.element_type == ElementType.IMAGE and e.image_data:
                result.append(
                    {
                        "text": "[图片]",
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
                        "_element_type": "image",
                    }
                )
        return result

    @staticmethod
    def _build_style_keys(structures: list) -> Dict[int, str]:
        """从结构识别结果构建段落索引→样式key映射"""
        return {s.index: s.style_hint for s in structures}

    async def _run_structure_recognition(
        self, para_dicts: List[Dict[str, Any]], use_llm: bool, preset_style: str = None
    ) -> list:
        """执行结构识别

        use_llm=True 时纯用 LLM，否则用规则引擎
        """
        if use_llm:
            from .llm.client import deepseek_client

            style_desc = None
            if preset_style:
                from app.core.presets.styles import (
                    get_preset_style,
                    get_style_mapping,
                    get_preset_list,
                )
                from app.api.v1.endpoints.tasks import _build_style_description

                style_desc = _build_style_description(preset_style)

            llm_output = await deepseek_client.recognize_structure(
                para_dicts, style_description=style_desc
            )
            if llm_output:
                return self._convert_llm_to_structures(llm_output)

            return self.rule_engine.analyze_structure(para_dicts)
        return self.rule_engine.analyze_structure(para_dicts)

    @staticmethod
    def _convert_llm_to_structures(llm_output) -> list:
        """将 LLMStructureOutput 转换为 ContentStructure 列表"""
        from .docx.rule_engine import ContentStructure, ContentType
        from .llm.models import ContentType as LLMContentType

        type_mapping = {
            LLMContentType.TITLE: ContentType.TITLE,
            LLMContentType.HEADING: ContentType.HEADING,
            LLMContentType.QUESTION_NUMBER: ContentType.QUESTION_NUMBER,
            LLMContentType.OPTION: ContentType.OPTION,
            LLMContentType.BODY: ContentType.BODY,
            LLMContentType.ANSWER: ContentType.ANSWER,
            LLMContentType.ANALYSIS: ContentType.ANALYSIS,
        }

        results = []
        for r in llm_output.results:
            content_type = type_mapping.get(r.content_type, ContentType.BODY)
            style_hint = rule_engine._get_style_hint(content_type)
            results.append(
                ContentStructure(
                    index=r.index,
                    text="",
                    content_type=content_type,
                    confidence=0.8,
                    style_hint=style_hint,
                )
            )
        return results

    async def _save_structure_analysis(
        self,
        structures: list,
        para_dicts: List[Dict[str, Any]],
        style_mapping: Dict[str, Any],
        task_id: Optional[str],
        method: str,
    ):
        """将结构分析结果保存到任务记录"""
        if not task_id:
            return

        paragraphs = []
        for i, pd in enumerate(para_dicts):
            from .docx.parser import ParagraphInfo, FontInfo, ParagraphFormat

            paragraphs.append(
                ParagraphInfo(
                    index=i,
                    text=pd.get("text", ""),
                    style_name="Normal",
                    font=FontInfo(
                        name=pd.get("font_name", "宋体"),
                        size=pd.get("font_size", 12.0),
                        bold=pd.get("font_bold", False),
                        italic=pd.get("font_italic", False),
                        underline=pd.get("font_underline", False),
                        color=pd.get("font_color", "000000"),
                    ),
                    format=ParagraphFormat(
                        alignment=pd.get("alignment", "left"),
                        line_spacing=pd.get("line_spacing"),
                        line_spacing_rule=pd.get("line_spacing_rule"),
                        space_before=pd.get("space_before"),
                        space_after=pd.get("space_after"),
                        first_line_indent=pd.get("first_line_indent"),
                        left_indent=pd.get("left_indent"),
                    ),
                )
            )

        formatted = structure_formatter.format_rule_engine_results(
            structures, style_mapping, paragraphs
        )

        import json

        formatted_json = json.dumps(formatted, ensure_ascii=False)

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Task).where(Task.task_id == task_id))
            task = result.scalar_one_or_none()
            if task:
                task.structure_analysis = formatted_json
                await db.commit()
            else:
                print(f"WARNING: Task {task_id} not found in database")

    def _get_output_path(
        self, input_file_path: str, original_filename: Optional[str] = None
    ) -> str:
        """生成输出文件路径

        Args:
            input_file_path: 输入文件路径
            original_filename: 原始上传文件名（用于输出命名）

        Returns:
            输出文件完整路径
        """
        input_path = Path(input_file_path)
        output_dir = input_path.parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        if original_filename:
            # 使用原始文件名
            name_without_ext = Path(original_filename).stem
            safe_name = self._sanitize_filename(name_without_ext)
            # 精确到时分秒的时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"{safe_name}_formatted_{timestamp}.docx"
        else:
            # 向后兼容：使用输入文件路径
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"{input_path.stem}_formatted_{timestamp}.docx"

        return str(output_dir / output_name)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """清理文件名中的非法字符

        Windows/Linux 不允许的字符: \\ / : * ? " < > |
        替换为下划线
        """
        illegal_chars = r'[\\/:*?"<>|]'
        return re.sub(illegal_chars, "_", filename)

    @staticmethod
    def _content_type_to_style_key(content_type: str) -> str:
        """将内容类型转换为样式key"""
        mapping = {
            "title": "heading1",
            "heading": "heading2",
            "question_number": "question_number",
            "option": "option",
            "body": "body",
        }
        return mapping.get(content_type, "body")


document_processor = DocumentProcessor()

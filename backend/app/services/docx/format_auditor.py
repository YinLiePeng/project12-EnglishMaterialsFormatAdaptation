"""格式审查模块 - 检测并纠正复制到模板后产生的格式漂移"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from docx import Document
from docx.shared import Pt, Cm, Length
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING

from .parser import (
    ContentElement,
    ElementType,
    ParagraphFormat,
    RunInfo,
)


@dataclass
class AuditCorrection:
    element_index: int
    element_type: str
    category: str
    property_name: str
    original_value: Any
    output_value: Any
    corrected: bool


@dataclass
class AuditResult:
    total_elements: int
    corrections: List[AuditCorrection] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)


class FormatAuditor:
    """格式审查器：比对输出文档与原始元素的格式差异并纠正"""

    def __init__(self):
        self.tolerance = 0.01

    def audit_and_correct(
        self, output_path: str, original_elements: List[ContentElement]
    ) -> AuditResult:
        """审查输出文档格式并自动纠正漂移"""
        corrections: List[AuditCorrection] = []

        doc = Document(output_path)
        doc_paragraphs = [p for p in doc.paragraphs if p.text.strip()]

        original_paras = [
            e
            for e in original_elements
            if e.element_type == ElementType.PARAGRAPH and e.paragraph
        ]

        for i, orig_el in enumerate(original_paras):
            if i >= len(doc_paragraphs):
                break

            orig_p = orig_el.paragraph
            doc_para = doc_paragraphs[i]

            fmt_corrections = self._compare_and_fix_format(i, orig_p.format, doc_para)
            corrections.extend(fmt_corrections)

            run_corrections = self._compare_and_fix_runs(i, orig_p.runs, doc_para)
            corrections.extend(run_corrections)

        if corrections:
            doc.save(output_path)

        summary: Dict[str, int] = {}
        for c in corrections:
            summary[c.category] = summary.get(c.category, 0) + 1

        return AuditResult(
            total_elements=len(original_elements),
            corrections=corrections,
            summary=summary,
        )

    def _compare_and_fix_format(
        self, idx: int, orig: ParagraphFormat, doc_para
    ) -> List[AuditCorrection]:
        """比较并修正段落格式属性"""
        corrections: List[AuditCorrection] = []
        pf = doc_para.paragraph_format

        alignment_map = {
            WD_ALIGN_PARAGRAPH.LEFT: "left",
            WD_ALIGN_PARAGRAPH.CENTER: "center",
            WD_ALIGN_PARAGRAPH.RIGHT: "right",
            WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
            None: "left",
        }

        if orig.alignment is not None:
            out_alignment = alignment_map.get(doc_para.alignment, "left")
            if out_alignment != orig.alignment:
                corrections.append(
                    AuditCorrection(
                        element_index=idx,
                        element_type="paragraph",
                        category="alignment",
                        property_name="alignment",
                        original_value=orig.alignment,
                        output_value=out_alignment,
                        corrected=True,
                    )
                )
                rev_map = {
                    "left": WD_ALIGN_PARAGRAPH.LEFT,
                    "center": WD_ALIGN_PARAGRAPH.CENTER,
                    "right": WD_ALIGN_PARAGRAPH.RIGHT,
                    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
                }
                doc_para.alignment = rev_map.get(
                    orig.alignment, WD_ALIGN_PARAGRAPH.LEFT
                )

        if orig.line_spacing is not None:
            out_ls, out_rule = self._read_doc_line_spacing(pf)
            orig_rule = orig.line_spacing_rule or "auto"

            if (
                not self._values_close(out_ls, orig.line_spacing)
                or out_rule != orig_rule
            ):
                corrections.append(
                    AuditCorrection(
                        element_index=idx,
                        element_type="paragraph",
                        category="spacing",
                        property_name="line_spacing",
                        original_value=f"{orig.line_spacing}({orig_rule})",
                        output_value=f"{out_ls}({out_rule})",
                        corrected=True,
                    )
                )
                self._fix_line_spacing(pf, orig.line_spacing, orig_rule)

        if orig.space_before is not None:
            out_val = pf.space_before.pt if pf.space_before is not None else 0.0
            if not self._values_close(out_val, orig.space_before):
                corrections.append(
                    AuditCorrection(
                        element_index=idx,
                        element_type="paragraph",
                        category="spacing",
                        property_name="space_before",
                        original_value=orig.space_before,
                        output_value=out_val,
                        corrected=True,
                    )
                )
                pf.space_before = Pt(orig.space_before)

        if orig.space_after is not None:
            out_val = pf.space_after.pt if pf.space_after is not None else 0.0
            if not self._values_close(out_val, orig.space_after):
                corrections.append(
                    AuditCorrection(
                        element_index=idx,
                        element_type="paragraph",
                        category="spacing",
                        property_name="space_after",
                        original_value=orig.space_after,
                        output_value=out_val,
                        corrected=True,
                    )
                )
                pf.space_after = Pt(orig.space_after)

        if orig.first_line_indent is not None:
            out_val = (
                pf.first_line_indent.cm if pf.first_line_indent is not None else 0.0
            )
            if not self._values_close(out_val, orig.first_line_indent):
                corrections.append(
                    AuditCorrection(
                        element_index=idx,
                        element_type="paragraph",
                        category="indent",
                        property_name="first_line_indent",
                        original_value=orig.first_line_indent,
                        output_value=out_val,
                        corrected=True,
                    )
                )
                pf.first_line_indent = Cm(orig.first_line_indent)

        if orig.left_indent is not None:
            out_val = pf.left_indent.cm if pf.left_indent is not None else 0.0
            if not self._values_close(out_val, orig.left_indent):
                corrections.append(
                    AuditCorrection(
                        element_index=idx,
                        element_type="paragraph",
                        category="indent",
                        property_name="left_indent",
                        original_value=orig.left_indent,
                        output_value=out_val,
                        corrected=True,
                    )
                )
                pf.left_indent = Cm(orig.left_indent)

        if orig.right_indent is not None:
            out_val = pf.right_indent.cm if pf.right_indent is not None else 0.0
            if not self._values_close(out_val, orig.right_indent):
                corrections.append(
                    AuditCorrection(
                        element_index=idx,
                        element_type="paragraph",
                        category="indent",
                        property_name="right_indent",
                        original_value=orig.right_indent,
                        output_value=out_val,
                        corrected=True,
                    )
                )
                pf.right_indent = Cm(orig.right_indent)

        return corrections

    @staticmethod
    def _read_doc_line_spacing(pf):
        """读取文档段落的行距值和规则，返回 (float_value, rule_str)"""
        ls = pf.line_spacing
        lsr = pf.line_spacing_rule

        if ls is None:
            return 1.0, "auto"

        if isinstance(ls, Length):
            pt_val = ls.pt
            if lsr == WD_LINE_SPACING.AT_LEAST:
                return pt_val, "atLeast"
            return pt_val, "exact"

        if lsr == WD_LINE_SPACING.MULTIPLE or lsr is None:
            return float(ls), "auto"
        if lsr == WD_LINE_SPACING.EXACTLY:
            return float(ls), "exact"
        if lsr == WD_LINE_SPACING.AT_LEAST:
            return float(ls), "atLeast"
        return float(ls), "auto"

    @staticmethod
    def _fix_line_spacing(pf, value: float, rule: str):
        """修正行距（同时设置值和规则）"""
        if rule == "auto":
            pf.line_spacing = value
        elif rule == "exact":
            pf.line_spacing = Pt(value)
            pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        elif rule == "atLeast":
            pf.line_spacing = Pt(value)
            pf.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
        else:
            pf.line_spacing = value

    def _compare_and_fix_runs(
        self, idx: int, orig_runs: List[RunInfo], doc_para
    ) -> List[AuditCorrection]:
        """比较并修正 run 级格式"""
        corrections: List[AuditCorrection] = []
        doc_runs = doc_para.runs

        for j, orig_run in enumerate(orig_runs):
            if j >= len(doc_runs):
                break
            if not orig_run.text or not orig_run.text.strip():
                continue

            doc_run = doc_runs[j]
            font = doc_run.font

            if orig_run.font_name != (font.name or "宋体"):
                corrections.append(
                    AuditCorrection(
                        element_index=idx,
                        element_type="paragraph",
                        category="font",
                        property_name="font_name",
                        original_value=orig_run.font_name,
                        output_value=font.name,
                        corrected=True,
                    )
                )
                font.name = orig_run.font_name

            out_size = font.size.pt if font.size else 12.0
            if not self._values_close(orig_run.font_size, out_size):
                corrections.append(
                    AuditCorrection(
                        element_index=idx,
                        element_type="paragraph",
                        category="font",
                        property_name="font_size",
                        original_value=orig_run.font_size,
                        output_value=out_size,
                        corrected=True,
                    )
                )
                font.size = Pt(orig_run.font_size)

            if orig_run.bold != (font.bold or False):
                font.bold = orig_run.bold

            if orig_run.italic != (font.italic or False):
                font.italic = orig_run.italic

        return corrections

    def _values_close(self, a: float, b: float) -> bool:
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False
        return abs(float(a) - float(b)) < self.tolerance


format_auditor = FormatAuditor()

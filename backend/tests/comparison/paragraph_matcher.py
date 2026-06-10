"""段落匹配器 - 三级匹配策略

第一级：精确文本匹配
第二级：模糊文本匹配（相似度 > 0.6）
第三级：位置+结构匹配
"""

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import List, Tuple, Optional, Dict, Any

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.docx.parser import ContentElement, ElementType, ParagraphInfo


@dataclass
class MatchResult:
    """单个匹配结果"""
    gen_para: Optional[ParagraphInfo]
    ref_para: Optional[ParagraphInfo]
    gen_index: int  # 在原始列表中的索引
    ref_index: int
    match_type: str  # "exact", "fuzzy", "positional", "unmatched_gen", "unmatched_ref"
    similarity: float  # 文本相似度


@dataclass
class MatcherOutput:
    """匹配器输出"""
    pairs: List[MatchResult] = field(default_factory=list)
    unmatched_gen: List[int] = field(default_factory=list)
    unmatched_ref: List[int] = field(default_factory=list)
    match_rate: float = 0.0


class ParagraphMatcher:
    """段落三级匹配器"""

    def __init__(
        self,
        gen_elements: List[ContentElement],
        ref_elements: List[ContentElement],
        fuzzy_threshold: float = 0.6,
    ):
        self.gen_paras = [
            (i, e.paragraph)
            for i, e in enumerate(gen_elements)
            if e.element_type == ElementType.PARAGRAPH and e.paragraph
        ]
        self.ref_paras = [
            (i, e.paragraph)
            for i, e in enumerate(ref_elements)
            if e.element_type == ElementType.PARAGRAPH and e.paragraph
        ]
        self.fuzzy_threshold = fuzzy_threshold

    def match(self) -> MatcherOutput:
        """执行三级匹配"""
        result = MatcherOutput()

        # 第一级：精确匹配
        exact_result = self._exact_match()
        result.pairs.extend(exact_result.pairs)
        remaining_gen = exact_result.unmatched_gen
        remaining_ref = exact_result.unmatched_ref

        # 第二级：模糊匹配
        fuzzy_result = self._fuzzy_match(remaining_gen, remaining_ref)
        result.pairs.extend(fuzzy_result.pairs)
        remaining_gen = fuzzy_result.unmatched_gen
        remaining_ref = fuzzy_result.unmatched_ref

        # 第三级：位置匹配
        positional_result = self._positional_match(remaining_gen, remaining_ref)
        result.pairs.extend(positional_result.pairs)
        result.unmatched_gen = positional_result.unmatched_gen
        result.unmatched_ref = positional_result.unmatched_ref

        # 计算匹配率
        total = max(len(self.gen_paras), len(self.ref_paras), 1)
        matched = len([p for p in result.pairs if p.match_type != "unmatched"])
        result.match_rate = matched / total

        return result

    def _exact_match(self) -> MatcherOutput:
        """第一级：精确文本匹配"""
        result = MatcherOutput()
        gen_texts: Dict[str, List[int]] = {}

        for idx, (orig_idx, para) in enumerate(self.gen_paras):
            text = para.text.strip()
            if text:
                if text not in gen_texts:
                    gen_texts[text] = []
                gen_texts[text].append(idx)

        used_gen = set()
        used_ref = set()

        for ref_idx, (orig_ref_idx, ref_para) in enumerate(self.ref_paras):
            text = ref_para.text.strip()
            if not text:
                continue

            if text in gen_texts:
                # 找到精确匹配，取第一个未使用的
                for gen_list_idx in gen_texts[text]:
                    if gen_list_idx not in used_gen:
                        used_gen.add(gen_list_idx)
                        used_ref.add(ref_idx)
                        gen_orig_idx, gen_para = self.gen_paras[gen_list_idx]
                        result.pairs.append(
                            MatchResult(
                                gen_para=gen_para,
                                ref_para=ref_para,
                                gen_index=gen_orig_idx,
                                ref_index=orig_ref_idx,
                                match_type="exact",
                                similarity=1.0,
                            )
                        )
                        break

        # 收集未匹配的
        for idx in range(len(self.gen_paras)):
            if idx not in used_gen:
                result.unmatched_gen.append(idx)
        for idx in range(len(self.ref_paras)):
            if idx not in used_ref:
                result.unmatched_ref.append(idx)

        return result

    def _fuzzy_match(self, gen_indices: List[int], ref_indices: List[int]) -> MatcherOutput:
        """第二级：模糊文本匹配"""
        result = MatcherOutput()
        used_gen = set()
        used_ref = set()

        if not gen_indices or not ref_indices:
            result.unmatched_gen = gen_indices[:]
            result.unmatched_ref = ref_indices[:]
            return result

        # 计算所有未匹配段落对的相似度
        candidates = []
        for gi in gen_indices:
            gen_orig_idx, gen_para = self.gen_paras[gi]
            gen_text = gen_para.text.strip()
            for ri in ref_indices:
                ref_orig_idx, ref_para = self.ref_paras[ri]
                ref_text = ref_para.text.strip()
                sim = SequenceMatcher(None, gen_text, ref_text).ratio()
                if sim >= self.fuzzy_threshold:
                    candidates.append((sim, gi, ri))

        # 按相似度降序排列，贪心匹配
        candidates.sort(reverse=True)
        for sim, gi, ri in candidates:
            if gi in used_gen or ri in used_ref:
                continue
            used_gen.add(gi)
            used_ref.add(ri)
            gen_orig_idx, gen_para = self.gen_paras[gi]
            ref_orig_idx, ref_para = self.ref_paras[ri]
            result.pairs.append(
                MatchResult(
                    gen_para=gen_para,
                    ref_para=ref_para,
                    gen_index=gen_orig_idx,
                    ref_index=ref_orig_idx,
                    match_type="fuzzy",
                    similarity=sim,
                )
            )

        # 收集仍未匹配的
        for gi in gen_indices:
            if gi not in used_gen:
                result.unmatched_gen.append(gi)
        for ri in ref_indices:
            if ri not in used_ref:
                result.unmatched_ref.append(ri)

        return result

    def _positional_match(self, gen_indices: List[int], ref_indices: List[int]) -> MatcherOutput:
        """第三级：位置匹配（按顺序配对）"""
        result = MatcherOutput()

        if not gen_indices and not ref_indices:
            return result

        if not gen_indices:
            for ri in ref_indices:
                ref_orig_idx, ref_para = self.ref_paras[ri]
                result.pairs.append(
                    MatchResult(
                        gen_para=None,
                        ref_para=ref_para,
                        gen_index=-1,
                        ref_index=ref_orig_idx,
                        match_type="unmatched_ref",
                        similarity=0.0,
                    )
                )
                result.unmatched_ref.append(ri)
            return result

        if not ref_indices:
            for gi in gen_indices:
                gen_orig_idx, gen_para = self.gen_paras[gi]
                result.pairs.append(
                    MatchResult(
                        gen_para=gen_para,
                        ref_para=None,
                        gen_index=gen_orig_idx,
                        ref_index=-1,
                        match_type="unmatched_gen",
                        similarity=0.0,
                    )
                )
                result.unmatched_gen.append(gi)
            return result

        # 按位置顺序配对
        min_len = min(len(gen_indices), len(ref_indices))
        for i in range(min_len):
            gi = gen_indices[i]
            ri = ref_indices[i]
            gen_orig_idx, gen_para = self.gen_paras[gi]
            ref_orig_idx, ref_para = self.ref_paras[ri]
            gen_text = gen_para.text.strip()
            ref_text = ref_para.text.strip()
            sim = SequenceMatcher(None, gen_text, ref_text).ratio()

            result.pairs.append(
                MatchResult(
                    gen_para=gen_para,
                    ref_para=ref_para,
                    gen_index=gen_orig_idx,
                    ref_index=ref_orig_idx,
                    match_type="positional",
                    similarity=sim,
                )
            )

        # 多余的
        for i in range(min_len, len(gen_indices)):
            gi = gen_indices[i]
            gen_orig_idx, gen_para = self.gen_paras[gi]
            result.pairs.append(
                MatchResult(
                    gen_para=gen_para,
                    ref_para=None,
                    gen_index=gen_orig_idx,
                    ref_index=-1,
                    match_type="unmatched_gen",
                    similarity=0.0,
                )
            )
            result.unmatched_gen.append(gi)

        for i in range(min_len, len(ref_indices)):
            ri = ref_indices[i]
            ref_orig_idx, ref_para = self.ref_paras[ri]
            result.pairs.append(
                MatchResult(
                    gen_para=None,
                    ref_para=ref_para,
                    gen_index=-1,
                    ref_index=ref_orig_idx,
                    match_type="unmatched_ref",
                    similarity=0.0,
                )
            )
            result.unmatched_ref.append(ri)

        return result

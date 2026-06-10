"""Run级文本匹配器

处理段落内run的对齐问题：
PDF可能把一个run拆成多个run，或合并多个run为一个。
按文本内容而非位置对齐run。
"""

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import List, Tuple, Optional

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.docx.parser import RunInfo


@dataclass
class RunMatchPair:
    """单个run匹配对"""
    gen_run: Optional[RunInfo]
    ref_run: Optional[RunInfo]
    match_type: str  # "exact", "fuzzy", "merged", "split", "unmatched"
    text_similarity: float


@dataclass
class RunMatcherOutput:
    """匹配器输出"""
    pairs: List[RunMatchPair] = field(default_factory=list)
    match_rate: float = 0.0


class RunMatcher:
    """Run级文本匹配器"""

    def __init__(self, gen_runs: List[RunInfo], ref_runs: List[RunInfo]):
        self.gen_runs = gen_runs
        self.ref_runs = ref_runs

    def match(self) -> RunMatcherOutput:
        """执行run匹配"""
        result = RunMatcherOutput()

        # 构建连续文本序列
        gen_text = "".join(r.text for r in self.gen_runs)
        ref_text = "".join(r.text for r in self.ref_runs)

        # 如果文本差异太大，直接按位置配对
        overall_sim = SequenceMatcher(None, gen_text, ref_text).ratio()
        if overall_sim < 0.3:
            result.pairs = self._positional_fallback()
        else:
            result.pairs = self._greedy_match()

        matched = len([p for p in result.pairs if p.match_type not in ("unmatched_gen", "unmatched_ref")])
        total = max(len(self.gen_runs), len(self.ref_runs), 1)
        result.match_rate = matched / total

        return result

    def _greedy_match(self) -> List[RunMatchPair]:
        """贪心匹配：按文本相似度配对"""
        pairs = []
        used_gen = set()
        used_ref = set()

        # 构建候选对
        candidates = []
        for gi, gen_run in enumerate(self.gen_runs):
            for ri, ref_run in enumerate(self.ref_runs):
                if not gen_run.text.strip() and not ref_run.text.strip():
                    sim = 1.0
                elif not gen_run.text.strip() or not ref_run.text.strip():
                    sim = 0.0
                else:
                    sim = SequenceMatcher(None, gen_run.text, ref_run.text).ratio()
                if sim > 0.3:
                    candidates.append((sim, gi, ri))

        # 按相似度降序排列
        candidates.sort(reverse=True)

        for sim, gi, ri in candidates:
            if gi in used_gen or ri in used_ref:
                continue
            used_gen.add(gi)
            used_ref.add(ri)

            gen_run = self.gen_runs[gi]
            ref_run = self.ref_runs[ri]

            if sim > 0.95:
                match_type = "exact"
            else:
                match_type = "fuzzy"

            pairs.append(
                RunMatchPair(
                    gen_run=gen_run,
                    ref_run=ref_run,
                    match_type=match_type,
                    text_similarity=sim,
                )
            )

        # 未匹配的
        for gi in range(len(self.gen_runs)):
            if gi not in used_gen:
                pairs.append(
                    RunMatchPair(
                        gen_run=self.gen_runs[gi],
                        ref_run=None,
                        match_type="unmatched_gen",
                        text_similarity=0.0,
                    )
                )

        for ri in range(len(self.ref_runs)):
            if ri not in used_ref:
                pairs.append(
                    RunMatchPair(
                        gen_run=None,
                        ref_run=self.ref_runs[ri],
                        match_type="unmatched_ref",
                        text_similarity=0.0,
                    )
                )

        return pairs

    def _positional_fallback(self) -> List[RunMatchPair]:
        """位置配对回退"""
        pairs = []
        min_len = min(len(self.gen_runs), len(self.ref_runs))

        for i in range(min_len):
            gen_run = self.gen_runs[i]
            ref_run = self.ref_runs[i]
            sim = SequenceMatcher(None, gen_run.text, ref_run.text).ratio()
            pairs.append(
                RunMatchPair(
                    gen_run=gen_run,
                    ref_run=ref_run,
                    match_type="positional",
                    text_similarity=sim,
                )
            )

        for i in range(min_len, len(self.gen_runs)):
            pairs.append(
                RunMatchPair(
                    gen_run=self.gen_runs[i],
                    ref_run=None,
                    match_type="unmatched_gen",
                    text_similarity=0.0,
                )
            )

        for i in range(min_len, len(self.ref_runs)):
            pairs.append(
                RunMatchPair(
                    gen_run=None,
                    ref_run=self.ref_runs[i],
                    match_type="unmatched_ref",
                    text_similarity=0.0,
                )
            )

        return pairs

from __future__ import annotations

from typing import Dict, FrozenSet, List, Set, Tuple
import re

from .base import RuleContext
from .helpers import make_issue


class PunctuationRule:
    code = "PUNCTUATION"
    _pairs = {"（": "）", "(": ")", "【": "】", "[": "]", "「": "」", "『": "』", "《": "》"}
    _closers = set(_pairs.values())

    def check(self, context: RuleContext):
        if context.block.role not in {"body", "heading"}:
            return []
        text = context.sentence.text
        issues = []
        for match in re.finditer(r"([。！？!?，,；;：:、])\1+", text):
            issues.append(
                make_issue(context, type_code="PUNCTUATION_DUPLICATE", start=match.start(), end=match.end(), message="标点符号重复")
            )
        stack: List[Tuple[str, int]] = []
        for index, char in enumerate(text):
            if char in self._pairs:
                stack.append((char, index))
            elif char in self._closers:
                expected = self._pairs[stack[-1][0]] if stack else None
                if not stack or char != expected:
                    issues.append(make_issue(context, type_code="PUNCTUATION_UNPAIRED", start=index, end=index + 1, message="括号或引号未配对"))
                else:
                    stack.pop()
        issues.extend(
            make_issue(context, type_code="PUNCTUATION_UNPAIRED", start=index, end=index + 1, message="括号或引号未配对")
            for _, index in stack
        )
        for match in re.finditer(r"[\u4e00-\u9fff],[\u4e00-\u9fff]", text):
            issues.append(make_issue(context, type_code="PUNCTUATION_WIDTH_MISMATCH", start=match.start() + 1, end=match.start() + 2, message="中文语境建议使用全角逗号"))
        for match in re.finditer(r"\.{3,}|-{2,}", text):
            issues.append(make_issue(context, type_code="ELLIPSIS_OR_DASH_INVALID", start=match.start(), end=match.end(), message="省略号或破折号形式可能不规范"))
        return issues

import re

from .base import Rule, RuleContext
from .helpers import make_issue


class RepeatedWordRule:
    code = "REPEATED_WORD"

    def check(self, context: RuleContext):
        if context.block.role != "body":
            return []
        issues = []
        for match in re.finditer(r"([\u4e00-\u9fff]{2,4})\1", context.sentence.text):
            issues.append(
                make_issue(
                    context,
                    type_code=self.code,
                    start=match.start(1) + len(match.group(1)),
                    end=match.end(),
                    message="疑似重复字词",
                )
            )
        return issues


class WhitespaceRule:
    code = "WHITESPACE_REDUNDANT"

    def check(self, context: RuleContext):
        if context.block.role != "body":
            return []
        issues = []
        for match in re.finditer(r"[ \t]{2,}", context.sentence.text):
            issues.append(make_issue(context, type_code=self.code, start=match.start(), end=match.end(), message="存在连续空格"))
        for match in re.finditer("\u3000", context.sentence.text):
            issues.append(make_issue(context, type_code="FULLWIDTH_SPACE_INVALID", start=match.start(), end=match.end(), message="正文中存在全角空格"))
        return issues

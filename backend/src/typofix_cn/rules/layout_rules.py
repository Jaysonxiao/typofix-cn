from typofix_cn.domain.catalog import ERROR_TYPES

from .base import RuleContext
from .helpers import make_issue


class FirstLineIndentRule:
    code = "FIRST_LINE_INDENT"

    def __init__(self, expected_indent_pt: float | None = None) -> None:
        self.expected_indent_pt = expected_indent_pt

    def check(self, context: RuleContext):
        if context.block.role != "body" or not context.block.text.strip() or context.sentence.index != 0:
            return []
        text = context.sentence.text
        if text[:1] in {" ", "\t", "\u3000"}:
            index = len(text) - len(text.lstrip(" \t\u3000"))
            return [make_issue(context, type_code="MANUAL_INDENT_SPACES", start=0, end=index, message="不建议使用行首空格模拟首行缩进")]
        indent = context.block.first_line_indent_pt or 0
        if indent <= 0:
            return [make_issue(context, type_code="FIRST_LINE_INDENT_MISSING", start=0, end=0, message="正文段落缺少首行缩进", original="")]
        if self.expected_indent_pt is not None and abs(indent - self.expected_indent_pt) > self.expected_indent_pt * 0.25:
            return [make_issue(context, type_code="FIRST_LINE_INDENT_INVALID", start=0, end=0, message="正文首行缩进量与基准不一致", original="")]
        return []

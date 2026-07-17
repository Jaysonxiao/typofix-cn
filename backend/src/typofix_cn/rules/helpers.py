from typofix_cn.domain.catalog import ERROR_TYPES
from typofix_cn.domain.enums import IssueSource
from typofix_cn.domain.issues import Issue
from typofix_cn.domain.locations import TextLocation

from .base import RuleContext


def make_issue(context: RuleContext, *, type_code: str, start: int, end: int, message: str, original: str | None = None) -> Issue:
    definition = ERROR_TYPES[type_code]
    value = context.sentence.text[start:end] if original is None else original
    return Issue.create(
        source=IssueSource.RULE,
        category=definition.category,
        type_code=type_code,
        severity=definition.default_severity,
        location=TextLocation(
            document_path=context.block.document_path,
            region=context.block.region,
            paragraph_index=context.block.paragraph_index,
            sentence_index=context.sentence.index,
            start_offset=context.sentence.start + start,
            end_offset=context.sentence.start + end,
        ),
        original=value,
        suggestion=None,
        message=message,
        context=context.sentence.text,
        rule_code=type_code,
    )

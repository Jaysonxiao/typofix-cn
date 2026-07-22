import pytest

from typofix_cn.documents.chunking import TextChunk
from typofix_cn.documents.models import ExtractedBlock
from typofix_cn.documents.sentences import SentenceSpan
from typofix_cn.rules.base import RuleContext
from typofix_cn.rules.registry import build_default_rule_registry


def context(text: str, role: str = "body") -> RuleContext:
    return RuleContext(
        block=ExtractedBlock(
            document_path="论文.docx",
            region="body",
            paragraph_index=0,
            text=text,
            role=role,
            style_name="Normal",
            first_line_indent_pt=24,
        ),
        sentence=SentenceSpan(index=0, text=text, start=0, end=len(text)),
    )


@pytest.mark.parametrize(
    ("text", "type_code"),
    [
        ("研究研究表明", "REPEATED_WORD"),
        ("结果。。如下", "PUNCTUATION_DUPLICATE"),
        ("采用（测试方法。", "PUNCTUATION_UNPAIRED"),
        ("中文句子,使用半角逗号。", "PUNCTUATION_WIDTH_MISMATCH"),
        ("这里使用" + "." * 6 + "表示省略", "ELLIPSIS_OR_DASH_INVALID"),
        ("中文  之间有空格。", "WHITESPACE_REDUNDANT"),
        ("正文中有　全角空格。", "FULLWIDTH_SPACE_INVALID"),
    ],
)
def test_rule_reports_expected_subtype(text: str, type_code: str) -> None:
    issues = build_default_rule_registry().check(context(text))
    assert type_code in {issue.type_code for issue in issues}
    assert all(issue.category.value in {"TEXT_CORRECTION", "PUNCTUATION_CHARACTER"} for issue in issues)


@pytest.mark.parametrize("text", ["？！", "English, text.", "访问 https://example.com/a,b。", "人人都要努力。"])
def test_rule_does_not_report_legitimate_text(text: str) -> None:
    assert build_default_rule_registry().check(context(text)) == []

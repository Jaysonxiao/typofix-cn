from typofix_cn.documents.models import ExtractedBlock
from typofix_cn.rules.base import RuleContext
from typofix_cn.rules.layout_rules import FirstLineIndentRule
from typofix_cn.rules.style_profile import build_style_profile


def block(*, role: str = "body", indent: float | None = None, text: str = "这是正文。", font_size: float = 12) -> ExtractedBlock:
    return ExtractedBlock(
        document_path="论文.docx",
        region="body" if role != "table_cell" else "table_cell",
        paragraph_index=0,
        text=text,
        role=role,
        style_name="Normal",
        first_line_indent_pt=indent,
        font_size_pt=font_size,
    )


def context(item: ExtractedBlock, sentence_index: int = 0) -> RuleContext:
    from typofix_cn.documents.sentences import SentenceSpan

    return RuleContext(block=item, sentence=SentenceSpan(index=sentence_index, text=item.text, start=0, end=len(item.text)))


def test_body_without_indent_is_reported() -> None:
    issues = FirstLineIndentRule().check(context(block(indent=0)))
    assert [issue.type_code for issue in issues] == ["FIRST_LINE_INDENT_MISSING"]


def test_manual_spaces_are_reported_without_duplicate_missing_indent() -> None:
    issues = FirstLineIndentRule().check(context(block(indent=0, text="  这是正文。")))
    assert [issue.type_code for issue in issues] == ["MANUAL_INDENT_SPACES"]


def test_heading_list_and_table_do_not_require_indent() -> None:
    rule = FirstLineIndentRule()
    assert rule.check(context(block(role="heading", indent=0))) == []
    assert rule.check(context(block(role="list_item", indent=0))) == []
    assert rule.check(context(block(role="table_cell", indent=0))) == []


def test_indent_outlier_is_reported_against_expected_value() -> None:
    issues = FirstLineIndentRule(expected_indent_pt=24).check(context(block(indent=12)))
    assert [issue.type_code for issue in issues] == ["FIRST_LINE_INDENT_INVALID"]


def test_indent_is_checked_once_per_paragraph() -> None:
    assert FirstLineIndentRule().check(context(block(indent=0), sentence_index=1)) == []


def test_style_profile_finds_one_outlier_after_dominant_body_style() -> None:
    profile = build_style_profile([block(font_size=12) for _ in range(9)] + [block(font_size=18)])
    assert profile.outlier_indexes == {9}

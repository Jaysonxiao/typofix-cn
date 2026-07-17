from typofix_cn.domain.enums import IssueCategory, IssueSource, Severity
from typofix_cn.domain.issues import Issue
from typofix_cn.domain.locations import TextLocation
from typofix_cn.terms.matcher import TermMatcher


def _issue(source: IssueSource, type_code: str, start: int, end: int) -> Issue:
    return Issue.create(
        source=source,
        category=IssueCategory.TEXT_CORRECTION,
        type_code=type_code,
        severity=Severity.ERROR,
        location=TextLocation(
            document_path="论文.docx",
            region="body",
            paragraph_index=0,
            sentence_index=0,
            start_offset=start,
            end_offset=end,
        ),
        original="做" if type_code == "SPELLING_TYPO" else "。",
        suggestion="作" if type_code == "SPELLING_TYPO" else None,
        message="测试问题",
        context="支持麒麟操做系统。",
    )


def test_only_model_typo_fully_inside_term_is_suppressed() -> None:
    matcher = TermMatcher({"default": ["麒麟操做系统"]})
    issues = matcher.apply(
        [_issue(IssueSource.MODEL, "SPELLING_TYPO", 5, 6), _issue(IssueSource.RULE, "PUNCTUATION_DUPLICATE", 9, 10)]
    )
    assert issues[0].status == "term_suppressed"
    assert issues[0].term_hits[0].term == "麒麟操做系统"
    assert issues[1].status == "actionable"


def test_partial_term_overlap_does_not_suppress() -> None:
    matcher = TermMatcher({"default": ["麒麟操做系统"]})
    issue = _issue(IssueSource.MODEL, "SPELLING_TYPO", 1, 3)
    assert matcher.apply([issue])[0].status == "actionable"


def test_sentence_relative_context_still_suppresses_with_paragraph_offset() -> None:
    issue = _issue(IssueSource.MODEL, "SPELLING_TYPO", 6, 7).model_copy(update={
        "location": TextLocation(document_path="论文.docx", region="body", paragraph_index=0, sentence_index=1, start_offset=6, end_offset=7),
        "original": "做",
        "context": "第一句。麒麟操做系统。",
    })
    assert TermMatcher({"default": ["麒麟操做系统"]}).apply([issue])[0].status == "term_suppressed"

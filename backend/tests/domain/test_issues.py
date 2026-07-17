from typofix_cn.domain.enums import IssueCategory, IssueSource, IssueStatus, Severity
from typofix_cn.domain.issues import Issue
from typofix_cn.domain.locations import TextLocation


def test_issue_id_does_not_change_when_term_status_changes() -> None:
    location = TextLocation(
        document_path="论文.docx",
        region="body",
        paragraph_index=2,
        sentence_index=1,
        start_offset=3,
        end_offset=4,
    )
    issue = Issue.create(
        source=IssueSource.MODEL,
        category=IssueCategory.TEXT_CORRECTION,
        type_code="SPELLING_TYPO",
        severity=Severity.ERROR,
        location=location,
        original="新",
        suggestion="心",
        message="疑似错别字",
        context="今天新情很好",
    )
    suppressed = issue.model_copy(update={"status": IssueStatus.TERM_SUPPRESSED})
    assert issue.issue_id == suppressed.issue_id


def test_every_subtype_maps_to_one_user_visible_parent() -> None:
    from typofix_cn.domain.catalog import ERROR_TYPES

    assert len(ERROR_TYPES) == len(set(ERROR_TYPES))
    assert all(item.category in set(IssueCategory) for item in ERROR_TYPES.values())
    assert ERROR_TYPES["FIRST_LINE_INDENT_MISSING"].category == IssueCategory.PARAGRAPH_LAYOUT

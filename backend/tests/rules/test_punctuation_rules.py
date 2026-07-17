from typofix_cn.rules.punctuation_rules import PunctuationRule
from typofix_cn.rules.base import RuleContext
from typofix_cn.documents.models import ExtractedBlock
from typofix_cn.documents.sentences import SentenceSpan


def test_paired_quotes_and_brackets_are_checked_with_stack() -> None:
    context = RuleContext(
        block=ExtractedBlock(document_path="论文.docx", region="body", paragraph_index=0, text="采用（测试方法。", role="body"),
        sentence=SentenceSpan(index=0, text="采用（测试方法。", start=0, end=8),
    )
    issues = PunctuationRule().check(context)
    assert [issue.type_code for issue in issues] == ["PUNCTUATION_UNPAIRED"]

from typofix_cn.documents.models import ExtractedBlock
from typofix_cn.rules.reference_rules import AcademicReferenceRuleSet


def body(text: str) -> ExtractedBlock:
    return ExtractedBlock(document_path="论文.docx", region="body", paragraph_index=0, text=text, role="body", style_name="Normal", first_line_indent_pt=24)


def test_missing_figure_and_reference_targets_are_reported() -> None:
    blocks = [body("如图2.3所示，相关结论见文献[4]。"), body("参考文献"), body("[1] 作者. 题名.")]
    codes = {issue.type_code for issue in AcademicReferenceRuleSet().check_document(blocks)}
    assert "CROSS_REFERENCE_TARGET_MISSING" in codes
    assert "CITATION_TARGET_MISSING" in codes
    assert "REFERENCE_NOT_CITED" in codes


def test_valid_numeric_citations_are_not_reported() -> None:
    blocks = [body("已有研究表明[1]。"), body("参考文献"), body("[1] 作者. 题名.")]
    assert AcademicReferenceRuleSet().check_document(blocks) == []

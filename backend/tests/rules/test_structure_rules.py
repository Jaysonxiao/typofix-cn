from typofix_cn.documents.models import ExtractedBlock
from typofix_cn.rules.structure_rules import StructureRuleSet


def heading(text: str, level: int) -> ExtractedBlock:
    return ExtractedBlock(document_path="论文.docx", region="body", paragraph_index=0, text=text, role="heading", style_name=f"Heading {level}")


def body(text: str) -> ExtractedBlock:
    return ExtractedBlock(document_path="论文.docx", region="body", paragraph_index=0, text=text, role="body", style_name="Normal", first_line_indent_pt=24)


def test_heading_level_jump_and_terminal_punctuation_are_reported() -> None:
    blocks = [heading("第一章 绪论", 1), heading("1.1.1 方法。", 3)]
    codes = {issue.type_code for issue in StructureRuleSet().check_document(blocks)}
    assert codes == {"HEADING_LEVEL_JUMP", "HEADING_END_PUNCTUATION"}


def test_duplicate_figure_number_and_missing_table_reference_are_reported() -> None:
    blocks = [body("如图2.1所示，详见表2.2。"), body("图2.1 实验结果"), body("图2.1 重复标题")]
    codes = {issue.type_code for issue in StructureRuleSet().check_document(blocks)}
    assert "FIGURE_NUMBER_DUPLICATE_OR_GAP" in codes
    assert "CROSS_REFERENCE_TARGET_MISSING" in codes

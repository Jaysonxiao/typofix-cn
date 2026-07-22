from docx.text.paragraph import Paragraph


def classify_paragraph(paragraph: Paragraph, *, region: str) -> str:
    if not paragraph.text:
        return "blank"
    if region == "table_cell":
        return "table_cell"
    style_name = (paragraph.style.name or "").lower()
    if style_name.startswith("heading") or style_name.startswith("标题"):
        return "heading"
    if style_name.startswith("list") or paragraph._p.pPr is not None and paragraph._p.pPr.numPr is not None:
        return "list_item"
    return "body"

from pydantic import BaseModel

from typofix_cn.domain.locations import TableLocation


class ExtractedBlock(BaseModel):
    document_path: str
    region: str
    paragraph_index: int
    text: str
    role: str
    style_name: str | None = None
    font_name: str | None = None
    font_size_pt: float | None = None
    first_line_indent_pt: float | None = None
    left_indent_pt: float | None = None
    alignment: str | None = None
    line_spacing: float | None = None
    space_before_pt: float | None = None
    space_after_pt: float | None = None
    table: TableLocation | None = None

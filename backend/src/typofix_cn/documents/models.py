from typing import Optional
from pydantic import BaseModel

from typofix_cn.domain.locations import TableLocation


class ExtractedBlock(BaseModel):
    document_path: str
    region: str
    paragraph_index: int
    text: str
    role: str
    style_name: Optional[str] = None
    font_name: Optional[str] = None
    font_size_pt: Optional[float] = None
    first_line_indent_pt: Optional[float] = None
    left_indent_pt: Optional[float] = None
    alignment: Optional[str] = None
    line_spacing: Optional[float] = None
    space_before_pt: Optional[float] = None
    space_after_pt: Optional[float] = None
    table: Optional[TableLocation] = None

from typing import Optional
from pydantic import BaseModel, Field


class TableLocation(BaseModel):
    table_index: int = Field(ge=0)
    row_index: int = Field(ge=0)
    column_index: int = Field(ge=0)
    cell_paragraph_index: int = Field(ge=0)


class TextLocation(BaseModel):
    document_path: str
    region: str
    paragraph_index: int = Field(ge=0)
    sentence_index: int = Field(ge=0)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    table: Optional[TableLocation] = None

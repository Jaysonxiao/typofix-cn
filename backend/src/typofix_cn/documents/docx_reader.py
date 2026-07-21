from pathlib import Path
from typing import Iterator, Optional, Union

from docx import Document
from docx.document import Document as DocumentObject
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P

from typofix_cn.domain.locations import TableLocation

from .errors import InvalidDocxError, UnsupportedDocxError
from .models import ExtractedBlock
from .roles import classify_paragraph


def _iter_block_items(parent: Union[DocumentObject, _Cell]) -> Iterator[Union[Paragraph, Table]]:
    parent_element = parent.element.body if isinstance(parent, DocumentObject) else parent._tc
    parent_part = parent.part
    for child in parent_element.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent_part)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent_part)


def _format_value(value: object) -> Optional[float]:
    if value is None:
        return None
    if hasattr(value, "pt"):
        return float(value.pt)
    if isinstance(value, (float, int)):
        return float(value)
    return None


class DocxReader:
    def read(self, path: Path, *, relative_path: str) -> list[ExtractedBlock]:
        if path.suffix.lower() != ".docx":
            raise UnsupportedDocxError(f"仅支持 DOCX 文件：{relative_path}")
        try:
            document = Document(path)
        except Exception as exc:  # python-docx raises several parser-specific exceptions
            raise InvalidDocxError(f"无法读取 DOCX 文件：{relative_path}") from exc

        blocks: list[ExtractedBlock] = []
        paragraph_index = 0
        table_index = 0
        for item in _iter_block_items(document):
            if isinstance(item, Paragraph):
                blocks.append(self._block(item, relative_path, paragraph_index, "body"))
                paragraph_index += 1
                continue
            for row_index, row in enumerate(item.rows):
                for column_index, cell in enumerate(row.cells):
                    for cell_paragraph_index, paragraph in enumerate(cell.paragraphs):
                        blocks.append(
                            self._block(
                                paragraph,
                                relative_path,
                                paragraph_index,
                                "table_cell",
                                TableLocation(
                                    table_index=table_index,
                                    row_index=row_index,
                                    column_index=column_index,
                                    cell_paragraph_index=cell_paragraph_index,
                                ),
                            )
                        )
                        paragraph_index += 1
            table_index += 1
        return blocks

    @staticmethod
    def _block(
        paragraph: Paragraph,
        relative_path: str,
        paragraph_index: int,
        region: str,
        table: Optional[TableLocation] = None,
    ) -> ExtractedBlock:
        fmt = paragraph.paragraph_format
        alignment = getattr(paragraph.alignment, "value", None)
        first_run = paragraph.runs[0] if paragraph.runs else None
        style_font = paragraph.style.font if paragraph.style is not None else None
        font_name = (first_run.font.name if first_run is not None else None) or (style_font.name if style_font else None)
        font_size = (first_run.font.size if first_run is not None else None) or (style_font.size if style_font else None)
        return ExtractedBlock(
            document_path=relative_path,
            region=region,
            paragraph_index=paragraph_index,
            text=paragraph.text,
            role=classify_paragraph(paragraph, region=region),
            style_name=paragraph.style.name if paragraph.style is not None else None,
            font_name=font_name,
            font_size_pt=_format_value(font_size),
            first_line_indent_pt=_format_value(fmt.first_line_indent),
            left_indent_pt=_format_value(fmt.left_indent),
            alignment=str(alignment) if alignment is not None else None,
            line_spacing=_format_value(fmt.line_spacing),
            space_before_pt=_format_value(fmt.space_before),
            space_after_pt=_format_value(fmt.space_after),
            table=table,
        )

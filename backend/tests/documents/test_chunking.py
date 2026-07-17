import pytest

from typofix_cn.documents.chunking import chunk_sentence


def test_long_sentence_chunks_overlap_without_losing_offsets() -> None:
    chunks = chunk_sentence("甲" * 20, max_chars=8, overlap=2)
    assert [(chunk.start, chunk.end) for chunk in chunks] == [(0, 8), (6, 14), (12, 20)]
    assert all(chunk.text == "甲" * (chunk.end - chunk.start) for chunk in chunks)


def test_chunking_rejects_invalid_overlap() -> None:
    with pytest.raises(ValueError, match="overlap"):
        chunk_sentence("文本", max_chars=4, overlap=4)

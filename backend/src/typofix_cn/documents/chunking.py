from __future__ import annotations

from typing import Dict, FrozenSet, List, Set, Tuple
from pydantic import BaseModel


class TextChunk(BaseModel):
    text: str
    start: int
    end: int


def chunk_sentence(text: str, *, max_chars: int, overlap: int) -> List[TextChunk]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap must be non-negative and smaller than max_chars")
    if not text:
        return []
    chunks: List[TextChunk] = []
    start = 0
    step = max_chars - overlap
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(TextChunk(text=text[start:end], start=start, end=end))
        if end == len(text):
            break
        start += step
    return chunks

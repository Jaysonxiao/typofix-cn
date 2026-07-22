from __future__ import annotations

from typing import Dict, FrozenSet, List, Set, Tuple
from pydantic import BaseModel


class SentenceSpan(BaseModel):
    index: int
    text: str
    start: int
    end: int


_TERMINATORS = set("。！？!?；;")
_CLOSERS = set("”’\"'》」』）)】〕〉】")


def split_sentences(text: str) -> List[SentenceSpan]:
    spans: List[SentenceSpan] = []
    start = 0
    index = 0
    cursor = 0
    while cursor < len(text):
        if text[cursor] not in _TERMINATORS:
            cursor += 1
            continue
        end = cursor + 1
        while end < len(text) and text[end] in _CLOSERS:
            end += 1
        if text[start:end].strip():
            spans.append(SentenceSpan(index=index, text=text[start:end], start=start, end=end))
            index += 1
        start = end
        cursor = end
    if text[start:].strip():
        spans.append(SentenceSpan(index=index, text=text[start:], start=start, end=len(text)))
    return spans

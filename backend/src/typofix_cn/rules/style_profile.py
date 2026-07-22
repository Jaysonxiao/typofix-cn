from __future__ import annotations

from typing import Dict, FrozenSet, List, Set, Tuple
from typing import Optional
from collections import Counter
from dataclasses import dataclass

from typofix_cn.documents.models import ExtractedBlock


@dataclass(frozen=True)
class StyleProfile:
    dominant_signature: Optional[Tuple[object, ...]]
    outlier_indexes: Set[int]


def _signature(block: ExtractedBlock) -> Tuple[object, ...]:
    return (
        block.font_name,
        block.font_size_pt,
        block.alignment,
        block.line_spacing,
        block.space_before_pt,
        block.space_after_pt,
    )


def build_style_profile(blocks: List[ExtractedBlock]) -> StyleProfile:
    comparable = [(index, block) for index, block in enumerate(blocks) if block.role == "body" and block.text.strip()]
    if len(comparable) < 5:
        return StyleProfile(dominant_signature=None, outlier_indexes=set())
    signatures = [_signature(block) for _, block in comparable]
    dominant, count = Counter(signatures).most_common(1)[0]
    if count / len(signatures) < 0.7:
        return StyleProfile(dominant_signature=None, outlier_indexes=set())
    return StyleProfile(
        dominant_signature=dominant,
        outlier_indexes={index for (index, _), signature in zip(comparable, signatures) if signature != dominant},
    )

from __future__ import annotations

from typing import Dict, FrozenSet, List, Set, Tuple
from typing import Sequence

from .base import CorrectionFinding, CorrectionInput, CorrectionResult


class FakeCorrector:
    def __init__(self, corrections: Dict[str, List[Tuple[str, str, int]]]) -> None:
        self.corrections = corrections
        self.calls = 0

    def correct(self, inputs: Sequence[CorrectionInput], *, detection_threshold: float = 0.50, correction_threshold: float = 0.30) -> List[CorrectionResult]:
        self.calls += 1
        results: List[CorrectionResult] = []
        for item in inputs:
            findings = [
                CorrectionFinding(start=start, end=start + len(original), original=original, suggestion=suggestion)
                for original, suggestion, start in self.corrections.get(item.text, [])
            ]
            results.append(CorrectionResult(key=item.key, source=item.text, findings=findings))
        return results

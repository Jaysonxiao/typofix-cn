from collections.abc import Sequence

from .base import CorrectionFinding, CorrectionInput, CorrectionResult


class FakeCorrector:
    def __init__(self, corrections: dict[str, list[tuple[str, str, int]]]) -> None:
        self.corrections = corrections
        self.calls = 0

    def correct(self, inputs: Sequence[CorrectionInput], *, detection_threshold: float = 0.50, correction_threshold: float = 0.30) -> list[CorrectionResult]:
        self.calls += 1
        results: list[CorrectionResult] = []
        for item in inputs:
            findings = [
                CorrectionFinding(start=start, end=start + len(original), original=original, suggestion=suggestion)
                for original, suggestion, start in self.corrections.get(item.text, [])
            ]
            results.append(CorrectionResult(key=item.key, source=item.text, findings=findings))
        return results

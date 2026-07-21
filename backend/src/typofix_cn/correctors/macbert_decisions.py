from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from .confusions import ConfusionMatch
from .macbert_candidates import Candidate, MacBertCandidate


@dataclass(frozen=True)
class CorrectionDecision:
    start: int
    end: int
    source: str
    suggestion: Optional[str]
    provider: str
    original_score: Optional[float]
    suggestion_score: Optional[float]
    detection_score: Optional[float]
    accepted: bool
    reason: str
    candidates: tuple[Candidate, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "source": self.source,
            "suggestion": self.suggestion,
            "provider": self.provider,
            "original_score": self.original_score,
            "suggestion_score": self.suggestion_score,
            "detection_score": self.detection_score,
            "accepted": self.accepted,
            "reason": self.reason,
            "candidates": [{"text": item.text, "score": item.score} for item in self.candidates],
        }


def build_decisions(
    text: str,
    confusion_matches: Iterable[ConfusionMatch],
    model_candidates: Iterable[MacBertCandidate],
    *,
    detection_threshold: float = 0.50,
    correction_threshold: float = 0.30,
) -> list[CorrectionDecision]:
    confusion_decisions = [
        CorrectionDecision(
            start=item.start,
            end=item.end,
            source=item.source,
            suggestion=item.target,
            provider="confusion",
            original_score=None,
            suggestion_score=None,
            detection_score=None,
            accepted=True,
            reason="confusion_exact_match",
        )
        for item in confusion_matches
    ]
    accepted_ranges = [(item.start, item.end) for item in confusion_decisions]
    model_decisions: list[CorrectionDecision] = []
    for item in model_candidates:
        if any(item.start < end and item.end > start for start, end in accepted_ranges):
            continue
        if not item.candidates:
            continue
        best = max(item.candidates, key=lambda candidate: candidate.score)
        if best.score < 0.05:
            continue
        detection_score = 1.0 - item.original_score
        if detection_score < detection_threshold:
            accepted = False
            reason = "detection_below_threshold"
        elif best.score < correction_threshold:
            accepted = False
            reason = "correction_below_threshold"
        else:
            accepted = True
            reason = "accepted"
        model_decisions.append(
            CorrectionDecision(
                start=item.start,
                end=item.end,
                source=item.source,
                suggestion=best.text,
                provider="model",
                original_score=item.original_score,
                suggestion_score=best.score,
                detection_score=detection_score,
                accepted=accepted,
                reason=reason,
                candidates=item.candidates,
            )
        )
    return sorted(confusion_decisions + model_decisions, key=lambda item: (item.start, item.end, item.provider != "confusion"))

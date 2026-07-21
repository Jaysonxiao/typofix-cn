from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    text: str
    score: float


@dataclass(frozen=True)
class MacBertCandidate:
    start: int
    end: int
    source: str
    original_score: float
    candidates: tuple[Candidate, ...]

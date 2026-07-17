from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel


class CorrectionInput(BaseModel):
    key: str
    text: str


class CorrectionFinding(BaseModel):
    start: int
    end: int
    original: str
    suggestion: str
    confidence: float | None = None


class CorrectionResult(BaseModel):
    key: str
    source: str
    findings: list[CorrectionFinding]


class Corrector(Protocol):
    def correct(self, inputs: Sequence[CorrectionInput]) -> list[CorrectionResult]:
        raise RuntimeError("Corrector protocol method must be implemented")

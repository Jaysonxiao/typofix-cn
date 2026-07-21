from collections.abc import Sequence
from typing import Protocol, Optional

from pydantic import BaseModel


class CorrectionInput(BaseModel):
    key: str
    text: str


class CorrectionFinding(BaseModel):
    start: int
    end: int
    original: str
    suggestion: str
    confidence: Optional[float] = None


class CorrectionResult(BaseModel):
    key: str
    source: str
    findings: list[CorrectionFinding]


class Corrector(Protocol):
    def correct(
        self,
        inputs: Sequence[CorrectionInput],
        *,
        detection_threshold: float = 0.50,
        correction_threshold: float = 0.30,
    ) -> list[CorrectionResult]:
        raise RuntimeError("Corrector protocol method must be implemented")

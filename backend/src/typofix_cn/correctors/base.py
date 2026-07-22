from __future__ import annotations

from typing import Dict, FrozenSet, List, Set, Tuple
from typing import Optional, Protocol, Sequence

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
    findings: List[CorrectionFinding]


class Corrector(Protocol):
    def correct(
        self,
        inputs: Sequence[CorrectionInput],
        *,
        detection_threshold: float = 0.50,
        correction_threshold: float = 0.30,
    ) -> List[CorrectionResult]:
        raise RuntimeError("Corrector protocol method must be implemented")

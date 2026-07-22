from __future__ import annotations

from typing import Dict, FrozenSet, List, Set, Tuple
from typing import Optional
from datetime import datetime, timezone
from enum import Enum

try:
    from enum import StrEnum
except ImportError:  # Python 3.8/3.9 compatibility
    class StrEnum(str, Enum):
        def __str__(self) -> str:
            return self.value

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_DOCUMENT_FAILURES = "completed_with_document_failures"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class JobManifest(BaseModel):
    schema_version: int = 1
    job_id: str
    status: JobStatus
    mode: str
    input_paths: List[str]
    selected_libraries: List[str]
    detection_threshold: float = Field(default=0.50, ge=0.0, le=1.0)
    correction_threshold: float = Field(default=0.30, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_documents: int = 0
    processed_documents: int = 0
    phase: str = "queued"
    error: Optional[str] = None

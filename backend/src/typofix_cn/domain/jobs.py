from datetime import datetime, timezone
from enum import StrEnum

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
    input_paths: list[str]
    selected_libraries: list[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_documents: int = 0
    processed_documents: int = 0
    phase: str = "queued"
    error: str | None = None

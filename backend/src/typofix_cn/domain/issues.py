from typing import Optional
import hashlib
import json

from pydantic import BaseModel, Field

from .enums import IssueCategory, IssueSource, IssueStatus, Severity
from .locations import TextLocation


class TermHit(BaseModel):
    library: str
    term: str
    start_offset: int
    end_offset: int


class Issue(BaseModel):
    issue_id: str
    source: IssueSource
    category: IssueCategory
    type_code: str
    severity: Severity
    status: IssueStatus = IssueStatus.ACTIONABLE
    location: TextLocation
    original: str
    suggestion: Optional[str] = None
    message: str
    context: str
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    rule_code: Optional[str] = None
    term_hits: list[TermHit] = Field(default_factory=list)

    @classmethod
    def create(cls, **values: object) -> "Issue":
        identity = {
            key: values[key]
            for key in ("source", "type_code", "location", "original", "suggestion")
        }
        payload = json.dumps(identity, ensure_ascii=False, sort_keys=True, default=str)
        return cls(issue_id=hashlib.sha256(payload.encode()).hexdigest()[:20], **values)

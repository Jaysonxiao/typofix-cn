from __future__ import annotations

from typing import Dict, FrozenSet, List, Set, Tuple
from collections import Counter
from typing import Literal, Optional

from pydantic import BaseModel, Field

from .enums import IssueCategory, IssueSource
from .issues import Issue


class DocumentResult(BaseModel):
    document_path: str
    status: Literal["completed", "failed"]
    issue_ids: List[str] = Field(default_factory=list)
    failure: Optional[str] = None


class ReportSummary(BaseModel):
    total: int
    actionable: int
    term_suppressed: int
    by_category: Dict[str, int]
    by_source: Dict[str, int]


class AnalysisReport(BaseModel):
    schema_version: Literal[1] = 1
    job_id: str
    mode: Literal["full", "rules_only"]
    model_name: Optional[str] = None
    documents: List[DocumentResult]
    issues: List[Issue]
    summary: ReportSummary


def summarize(issues: List[Issue]) -> ReportSummary:
    return ReportSummary(
        total=len(issues),
        actionable=sum(issue.status.value == "actionable" for issue in issues),
        term_suppressed=sum(issue.status.value == "term_suppressed" for issue in issues),
        by_category=dict(Counter(issue.category.value for issue in issues)),
        by_source=dict(Counter(issue.source.value for issue in issues)),
    )

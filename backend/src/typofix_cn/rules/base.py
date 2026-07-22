from __future__ import annotations

from typing import Dict, FrozenSet, List, Set, Tuple
from typing import Protocol

from pydantic import BaseModel

from typofix_cn.documents.models import ExtractedBlock
from typofix_cn.documents.sentences import SentenceSpan
from typofix_cn.domain.issues import Issue


class RuleContext(BaseModel):
    block: ExtractedBlock
    sentence: SentenceSpan


class Rule(Protocol):
    code: str

    def check(self, context: RuleContext) -> List[Issue]:
        raise RuntimeError("Rule protocol method must be implemented")

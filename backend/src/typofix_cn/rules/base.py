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

    def check(self, context: RuleContext) -> list[Issue]:
        raise RuntimeError("Rule protocol method must be implemented")

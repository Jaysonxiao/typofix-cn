from __future__ import annotations

from typing import Dict, FrozenSet, List, Set, Tuple
import unicodedata

from typofix_cn.domain.enums import IssueSource, IssueStatus
from typofix_cn.domain.issues import Issue, TermHit


class TermMatcher:
    def __init__(self, libraries: Dict[str, List[str]]) -> None:
        self.libraries = libraries

    def apply(self, issues: List[Issue]) -> List[Issue]:
        result: List[Issue] = []
        for issue in issues:
            hits = self._find_hits(issue.context)
            can_suppress = issue.source == IssueSource.MODEL and issue.type_code == "SPELLING_TYPO"
            original_start = issue.context.find(issue.original) if issue.original else -1
            original_end = original_start + len(issue.original) if original_start >= 0 else -1
            if original_start >= 0 and 0 <= issue.location.start_offset <= len(issue.context) and issue.location.start_offset != original_start:
                original_start = issue.location.start_offset
                original_end = original_start + len(issue.original)
            suppressed = can_suppress and original_start >= 0 and any(hit.start_offset <= original_start and original_end <= hit.end_offset for hit in hits)
            result.append(
                issue.model_copy(
                    update={
                        "status": IssueStatus.TERM_SUPPRESSED if suppressed else IssueStatus.ACTIONABLE,
                        "term_hits": hits,
                    }
                )
            )
        return result

    def _find_hits(self, context: str) -> List[TermHit]:
        normalized_context = unicodedata.normalize("NFC", context)
        hits: List[TermHit] = []
        for library, terms in self.libraries.items():
            for raw_term in terms:
                term = unicodedata.normalize("NFC", raw_term)
                if not term:
                    continue
                start = normalized_context.find(term)
                while start >= 0:
                    hits.append(TermHit(library=library, term=raw_term, start_offset=start, end_offset=start + len(term)))
                    start = normalized_context.find(term, start + 1)
        return hits

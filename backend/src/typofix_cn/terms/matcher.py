import unicodedata

from typofix_cn.domain.enums import IssueSource, IssueStatus
from typofix_cn.domain.issues import Issue, TermHit


class TermMatcher:
    def __init__(self, libraries: dict[str, list[str]]) -> None:
        self.libraries = libraries

    def apply(self, issues: list[Issue]) -> list[Issue]:
        result: list[Issue] = []
        for issue in issues:
            hits = self._find_hits(issue.context)
            can_suppress = issue.source == IssueSource.MODEL and issue.type_code == "SPELLING_TYPO"
            start = issue.location.start_offset
            end = issue.location.end_offset
            suppressed = can_suppress and any(hit.start_offset <= start and end <= hit.end_offset for hit in hits)
            result.append(
                issue.model_copy(
                    update={
                        "status": IssueStatus.TERM_SUPPRESSED if suppressed else IssueStatus.ACTIONABLE,
                        "term_hits": hits,
                    }
                )
            )
        return result

    def _find_hits(self, context: str) -> list[TermHit]:
        normalized_context = unicodedata.normalize("NFC", context)
        hits: list[TermHit] = []
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

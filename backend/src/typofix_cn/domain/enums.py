from enum import StrEnum


class IssueSource(StrEnum):
    MODEL = "model"
    RULE = "rule"


class IssueStatus(StrEnum):
    ACTIONABLE = "actionable"
    TERM_SUPPRESSED = "term_suppressed"


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueCategory(StrEnum):
    TEXT_CORRECTION = "TEXT_CORRECTION"
    PUNCTUATION_CHARACTER = "PUNCTUATION_CHARACTER"
    PARAGRAPH_LAYOUT = "PARAGRAPH_LAYOUT"
    STRUCTURE_NUMBERING = "STRUCTURE_NUMBERING"
    CITATION_REFERENCE = "CITATION_REFERENCE"

from enum import Enum

try:
    from enum import StrEnum
except ImportError:  # Python 3.8/3.9 compatibility
    class StrEnum(str, Enum):
        def __str__(self) -> str:
            return self.value


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

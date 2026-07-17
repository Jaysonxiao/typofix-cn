from dataclasses import dataclass

from .enums import IssueCategory, Severity


@dataclass(frozen=True)
class ErrorTypeDefinition:
    category: IssueCategory
    default_severity: Severity
    default_enabled: bool = True


def _definition(category: IssueCategory, severity: Severity, enabled: bool = True) -> ErrorTypeDefinition:
    return ErrorTypeDefinition(category, severity, enabled)


ERROR_TYPES = {
    "SPELLING_TYPO": _definition(IssueCategory.TEXT_CORRECTION, Severity.ERROR),
    "REPEATED_WORD": _definition(IssueCategory.TEXT_CORRECTION, Severity.WARNING),
    "TERM_INCONSISTENT": _definition(IssueCategory.TEXT_CORRECTION, Severity.INFO, False),
    "ABBREVIATION_UNEXPLAINED": _definition(IssueCategory.TEXT_CORRECTION, Severity.INFO, False),
    "PUNCTUATION_DUPLICATE": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.WARNING),
    "PUNCTUATION_UNPAIRED": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.ERROR),
    "PUNCTUATION_WIDTH_MISMATCH": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.WARNING),
    "PUNCTUATION_COMBINATION_INVALID": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.WARNING),
    "ELLIPSIS_OR_DASH_INVALID": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.WARNING),
    "PARAGRAPH_END_PUNCTUATION_MISSING": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.INFO),
    "WHITESPACE_REDUNDANT": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.WARNING),
    "FULLWIDTH_SPACE_INVALID": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.WARNING),
    "NUMBER_STYLE_INCONSISTENT": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.INFO),
    "DATE_FORMAT_SUSPECT": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.INFO),
    "NUMBER_UNIT_SPACING": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.INFO),
    "UNIT_STYLE_INCONSISTENT": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.INFO),
    "FIRST_LINE_INDENT_MISSING": _definition(IssueCategory.PARAGRAPH_LAYOUT, Severity.WARNING),
    "FIRST_LINE_INDENT_INVALID": _definition(IssueCategory.PARAGRAPH_LAYOUT, Severity.WARNING),
    "MANUAL_INDENT_SPACES": _definition(IssueCategory.PARAGRAPH_LAYOUT, Severity.WARNING),
    "BODY_STYLE_OUTLIER": _definition(IssueCategory.PARAGRAPH_LAYOUT, Severity.INFO),
    "EXCESSIVE_EMPTY_PARAGRAPH": _definition(IssueCategory.PARAGRAPH_LAYOUT, Severity.INFO),
    "HEADING_END_PUNCTUATION": _definition(IssueCategory.STRUCTURE_NUMBERING, Severity.WARNING),
    "HEADING_NUMBER_INVALID": _definition(IssueCategory.STRUCTURE_NUMBERING, Severity.WARNING),
    "HEADING_LEVEL_JUMP": _definition(IssueCategory.STRUCTURE_NUMBERING, Severity.WARNING),
    "HEADING_STYLE_INCONSISTENT": _definition(IssueCategory.STRUCTURE_NUMBERING, Severity.INFO),
    "FIGURE_NUMBER_DUPLICATE_OR_GAP": _definition(IssueCategory.STRUCTURE_NUMBERING, Severity.WARNING),
    "TABLE_NUMBER_DUPLICATE_OR_GAP": _definition(IssueCategory.STRUCTURE_NUMBERING, Severity.WARNING),
    "CAPTION_STYLE_INCONSISTENT": _definition(IssueCategory.STRUCTURE_NUMBERING, Severity.INFO),
    "CROSS_REFERENCE_TARGET_MISSING": _definition(IssueCategory.STRUCTURE_NUMBERING, Severity.ERROR),
    "CITATION_TARGET_MISSING": _definition(IssueCategory.CITATION_REFERENCE, Severity.ERROR),
    "REFERENCE_NOT_CITED": _definition(IssueCategory.CITATION_REFERENCE, Severity.WARNING),
    "REFERENCE_NUMBER_DUPLICATE_OR_GAP": _definition(IssueCategory.CITATION_REFERENCE, Severity.WARNING),
    "REFERENCE_STYLE_INCONSISTENT": _definition(IssueCategory.CITATION_REFERENCE, Severity.INFO),
}

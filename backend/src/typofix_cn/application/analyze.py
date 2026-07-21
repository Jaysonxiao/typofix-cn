from typing import Optional
from collections.abc import Callable, Sequence
from pathlib import Path

from typofix_cn.correctors.base import CorrectionInput, Corrector
from typofix_cn.documents.docx_reader import DocxReader
from typofix_cn.documents.sentences import split_sentences
from typofix_cn.domain.enums import IssueCategory, IssueSource
from typofix_cn.domain.issues import Issue
from typofix_cn.domain.reports import AnalysisReport, DocumentResult, summarize
from typofix_cn.rules.base import RuleContext
from typofix_cn.rules.reference_rules import AcademicReferenceRuleSet
from typofix_cn.rules.registry import RuleRegistry, build_default_rule_registry
from typofix_cn.rules.structure_rules import StructureRuleSet
from typofix_cn.terms.matcher import TermMatcher


class AnalysisService:
    def __init__(
        self,
        *,
        corrector: Corrector,
        term_libraries: Optional[dict[str, list[str]]] = None,
        reader: Optional[DocxReader] = None,
        rules: Optional[RuleRegistry] = None,
        model_name: Optional[str] = None,
        detection_threshold: float = 0.50,
        correction_threshold: float = 0.30,
    ) -> None:
        self.corrector = corrector
        self.term_libraries = term_libraries or {}
        self.reader = reader or DocxReader()
        self.rules = rules or build_default_rule_registry()
        self.model_name = model_name
        self.detection_threshold = detection_threshold
        self.correction_threshold = correction_threshold

    def analyze(
        self,
        paths: Sequence[Path],
        *,
        relative_paths: Optional[Sequence[str]] = None,
        selected_libraries: Sequence[str] = (),
        mode: str = "full",
        job_id: str = "local",
        progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> AnalysisReport:
        all_issues: list[Issue] = []
        documents: list[DocumentResult] = []
        total = len(paths)
        display_paths = list(relative_paths) if relative_paths is not None else [path.name for path in paths]
        if len(display_paths) != len(paths):
            raise ValueError("relative_paths must match paths")
        for index, (path, display_path) in enumerate(zip(paths, display_paths), start=1):
            try:
                blocks = self.reader.read(path, relative_path=display_path)
                issues = self._analyze_blocks(blocks, mode=mode)
                issues = self._deduplicate(issues)
                all_issues.extend(issues)
                documents.append(DocumentResult(document_path=display_path, status="completed", issue_ids=[item.issue_id for item in issues]))
            except Exception as exc:
                documents.append(DocumentResult(document_path=display_path, status="failed", failure=str(exc)))
            if progress:
                progress(index, total, "analysis")
        selected = {name: self.term_libraries[name] for name in selected_libraries if name in self.term_libraries}
        issues = TermMatcher(selected).apply(all_issues)
        return AnalysisReport(
            job_id=job_id,
            mode=mode,
            model_name=self.model_name if mode == "full" else None,
            documents=documents,
            issues=issues,
            summary=summarize(issues),
        )

    def _analyze_blocks(self, blocks, *, mode: str) -> list[Issue]:
        issues: list[Issue] = []
        for block in blocks:
            sentences = split_sentences(block.text)
            for sentence in sentences:
                context = RuleContext(block=block, sentence=sentence)
                issues.extend(self.rules.check(context))
        issues.extend(StructureRuleSet().check_document(blocks))
        issues.extend(AcademicReferenceRuleSet().check_document(blocks))
        if mode == "full":
            sentence_map = {
                f"{block.paragraph_index}:{sentence.index}": (block, sentence)
                for block in blocks
                for sentence in split_sentences(block.text)
                if sentence.text.strip()
            }
            inputs = [
                CorrectionInput(key=f"{block.paragraph_index}:{sentence.index}", text=sentence.text)
                for block in blocks
                for sentence in split_sentences(block.text)
                if sentence.text.strip()
            ]
            for result in self.corrector.correct(
                inputs,
                detection_threshold=self.detection_threshold,
                correction_threshold=self.correction_threshold,
            ):
                paragraph_index, sentence_index = (int(value) for value in result.key.split(":", 1))
                block, sentence = sentence_map[result.key]
                for finding in result.findings:
                    issues.append(
                        Issue.create(
                            source=IssueSource.MODEL,
                            category=IssueCategory.TEXT_CORRECTION,
                            type_code="SPELLING_TYPO",
                            severity="error",
                            location={
                                "document_path": block.document_path,
                                "region": block.region,
                                "paragraph_index": paragraph_index,
                                "sentence_index": sentence_index,
                                "start_offset": sentence.start + finding.start,
                                "end_offset": sentence.start + finding.end,
                                "table": block.table,
                            },
                            original=finding.original,
                            suggestion=finding.suggestion,
                            message=f"建议将“{finding.original}”修改为“{finding.suggestion}”",
                            context=result.source,
                            confidence=finding.confidence,
                        )
                    )
        return issues

    @staticmethod
    def _deduplicate(issues: list[Issue]) -> list[Issue]:
        seen: set[str] = set()
        result = []
        for issue in issues:
            if issue.issue_id not in seen:
                result.append(issue)
                seen.add(issue.issue_id)
        return result

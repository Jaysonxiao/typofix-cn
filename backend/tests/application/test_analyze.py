from docx import Document
from docx.shared import Pt

from typofix_cn.application.analyze import AnalysisService
from typofix_cn.correctors.fake import FakeCorrector


def sample_docx(tmp_path):
    path = tmp_path / "论文.docx"
    document = Document()
    paragraph = document.add_paragraph("支持麒麟操做系统。")
    paragraph.paragraph_format.first_line_indent = Pt(24)
    document.save(path)
    return path


def test_analysis_combines_model_rules_and_term_status(tmp_path) -> None:
    service = AnalysisService(
        corrector=FakeCorrector({"支持麒麟操做系统。": [("做", "作", 5)]}),
        term_libraries={"default": ["麒麟操做系统"]},
    )
    report = service.analyze([sample_docx(tmp_path)], selected_libraries=["default"], job_id="job-1")
    typo = next(issue for issue in report.issues if issue.type_code == "SPELLING_TYPO")
    assert typo.status == "term_suppressed"
    assert typo.location.paragraph_index == 0
    assert report.summary.term_suppressed == 1
    assert report.summary.actionable >= 0


def test_rules_only_mode_never_calls_corrector(tmp_path) -> None:
    corrector = FakeCorrector({})
    service = AnalysisService(corrector=corrector)
    report = service.analyze([sample_docx(tmp_path)], selected_libraries=[], mode="rules_only", job_id="job-2")
    assert report.mode == "rules_only"
    assert corrector.calls == 0


def test_document_failure_does_not_abort_other_documents(tmp_path) -> None:
    good = sample_docx(tmp_path)
    bad = tmp_path / "损坏.docx"
    bad.write_bytes(b"not a docx")
    report = AnalysisService(corrector=FakeCorrector({})).analyze([good, bad], mode="rules_only", job_id="job-3")
    assert len(report.documents) == 2
    assert report.documents[1].status == "failed"
    assert report.documents[0].status == "completed"

from pathlib import Path
from types import SimpleNamespace

from typofix_cn.correctors.base import CorrectionInput
import pytest

from typofix_cn.correctors.macbert import MacBertCorrector, ModelInferenceError
from typofix_cn.correctors.macbert_candidates import Candidate, MacBertCandidate


class PipelineBackend:
    tokenizer = object()
    model = object()


class ProviderBackend:
    def candidate_provider(self):
        return FakeProvider(self)


class FakeProvider:
    available = True

    def __init__(self, backend) -> None:
        self.backend = backend

    def predict(self, texts):
        return [
            [
                MacBertCandidate(
                    start=2,
                    end=3,
                    source="新",
                    original_score=0.46,
                    candidates=(Candidate("薪", 0.41), Candidate("心", 0.39)),
                )
            ]
            for _ in texts
        ]


def test_macbert_pipeline_returns_decisions_and_accepts_top_two_candidate(monkeypatch, tmp_path: Path) -> None:
    confusion_path = tmp_path / "confusions.txt"
    confusion_path.write_text("", encoding="utf-8")
    monkeypatch.setattr("typofix_cn.correctors.macbert.MacBertCandidateProvider", FakeProvider)
    corrector = MacBertCorrector(tmp_path / "model", loader=lambda _: PipelineBackend(), confusion_path=confusion_path)

    result = corrector.correct_raw(["今天新情"])[0]

    assert result["target"] == "今天薪情"
    assert result["errors"] == [("新", "薪", 2)]
    assert result["decisions"][0]["accepted"] is True


def test_macbert_pipeline_confusion_is_reported_before_model(monkeypatch, tmp_path: Path) -> None:
    confusion_path = tmp_path / "confusions.txt"
    confusion_path.write_text("新资 => 薪资\n", encoding="utf-8")
    monkeypatch.setattr("typofix_cn.correctors.macbert.MacBertCandidateProvider", FakeProvider)
    corrector = MacBertCorrector(tmp_path / "model", loader=lambda _: PipelineBackend(), confusion_path=confusion_path)

    result = corrector.correct_raw(["今天新资"])[0]

    assert result["target"] == "今天薪资"
    assert result["errors"] == [("新资", "薪资", 2)]
    assert result["decisions"][0]["provider"] == "confusion"


def test_macbert_pipeline_falls_back_when_backend_has_no_fast_logits(tmp_path: Path) -> None:
    class FallbackBackend:
        def correct_batch(self, texts, *, threshold=0.7):
            return [{"target": text.replace("新", "薪"), "errors": [("新", "薪", text.index("新"))]} for text in texts]

    corrector = MacBertCorrector(tmp_path / "model", loader=lambda _: FallbackBackend(), confusion_path=tmp_path / "missing.txt")

    result = corrector.correct_raw(["今天新情"])[0]

    assert result["target"] == "今天薪情"
    assert result["errors"] == [("新", "薪", 2)]
    assert result["decisions"][0]["reason"] == "backend_fallback"


def test_macbert_correct_keeps_docx_finding_contract(monkeypatch, tmp_path: Path) -> None:
    confusion_path = tmp_path / "confusions.txt"
    confusion_path.write_text("", encoding="utf-8")
    monkeypatch.setattr("typofix_cn.correctors.macbert.MacBertCandidateProvider", FakeProvider)
    corrector = MacBertCorrector(tmp_path / "model", loader=lambda _: PipelineBackend(), confusion_path=confusion_path)

    result = corrector.correct([CorrectionInput(key="s1", text="今天新情")])[0]

    assert result.source == "今天新情"
    assert [finding.model_dump() for finding in result.findings] == [
        {"start": 2, "end": 3, "original": "新", "suggestion": "薪", "confidence": None}
    ]


def test_macbert_correct_does_not_promote_confusion_rules_into_docx_findings(monkeypatch, tmp_path: Path) -> None:
    confusion_path = tmp_path / "confusions.txt"
    confusion_path.write_text("新资 => 薪资\n", encoding="utf-8")
    monkeypatch.setattr("typofix_cn.correctors.macbert.MacBertCandidateProvider", FakeProvider)
    corrector = MacBertCorrector(tmp_path / "model", loader=lambda _: PipelineBackend(), confusion_path=confusion_path)

    result = corrector.correct([CorrectionInput(key="s1", text="今天新资")])[0]

    assert result.findings == []


def test_macbert_inference_error_does_not_silently_fallback(monkeypatch, tmp_path: Path) -> None:
    class BrokenProvider:
        available = True

        def __init__(self, backend) -> None:
            pass

        def predict(self, texts):
            raise RuntimeError("forward failed")

    confusion_path = tmp_path / "confusions.txt"
    confusion_path.write_text("", encoding="utf-8")
    monkeypatch.setattr("typofix_cn.correctors.macbert.MacBertCandidateProvider", BrokenProvider)
    corrector = MacBertCorrector(tmp_path / "model", loader=lambda _: PipelineBackend(), confusion_path=confusion_path)

    with pytest.raises(ModelInferenceError, match="MacBERT 推理失败"):
        corrector.correct_raw(["今天新情"])


def test_macbert_uses_backend_candidate_provider_when_available(tmp_path: Path) -> None:
    corrector = MacBertCorrector(tmp_path / "model", loader=lambda _: ProviderBackend(), confusion_path=tmp_path / "missing.txt")

    result = corrector.correct_raw(["今天新情"])[0]

    assert result["target"] == "今天薪情"

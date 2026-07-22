from unittest.mock import Mock

from typofix_cn.correctors.base import CorrectionInput
from typofix_cn.correctors.macbert import MacBertCorrector


class StubBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], float]] = []

    def correct_batch(self, texts, *, threshold=0.7):
        self.calls.append((list(texts), threshold))
        results = []
        for text in texts:
            if "新资" in text:
                results.append({"source": text, "target": text.replace("新资", "薪资"), "errors": [("新", "薪", text.index("新"))]})
            elif "新" in text:
                results.append({"source": text, "target": text.replace("新", "心"), "errors": [("新", "心", text.index("新"))]})
            else:
                results.append({"source": text, "target": text, "errors": []})
        return results


def test_macbert_loads_backend_once(monkeypatch, tmp_path) -> None:
    loader = Mock(return_value=StubBackend())
    corrector = MacBertCorrector(tmp_path, loader=loader)
    corrector.correct([CorrectionInput(key="a", text="今天新情很好")])
    corrector.correct([CorrectionInput(key="b", text="今天新情很好")])
    loader.assert_called_once_with(tmp_path)


def test_macbert_returns_backend_output_without_conversion(tmp_path) -> None:
    corrector = MacBertCorrector(tmp_path, loader=lambda _: StubBackend())

    result = corrector.correct_raw(["今天新情很好"])

    assert result == [
        {
            "source": "今天新情很好",
            "target": "今天心情很好",
            "errors": [("新", "心", 2)],
            "decisions": [
                {
                    "start": 2,
                    "end": 3,
                    "source": "新",
                    "suggestion": "心",
                    "provider": "model",
                    "original_score": None,
                    "suggestion_score": None,
                    "detection_score": None,
                    "accepted": True,
                    "reason": "backend_fallback",
                    "candidates": [],
                }
            ],
        }
    ]


def test_macbert_corrects_chinese_spans_in_mixed_text(tmp_path) -> None:
    backend = StubBackend()
    corrector = MacBertCorrector(tmp_path, loader=lambda _: backend)
    source = "2023年学员平均就业新资18K/月（高于行业均值32%）"

    result = corrector.correct_raw([source], threshold=0.35)

    assert backend.calls == [(["年学员平均就业新资", "月", "高于行业均值"], 0.35)]
    assert result == [
        {
            "source": source,
            "target": "2023年学员平均就业薪资18K/月（高于行业均值32%）",
            "errors": [("新", "薪", 11)],
            "decisions": [
                {
                    "start": 11,
                    "end": 12,
                    "source": "新",
                    "suggestion": "薪",
                    "provider": "model",
                    "original_score": None,
                    "suggestion_score": None,
                    "detection_score": None,
                    "accepted": True,
                    "reason": "backend_fallback",
                    "candidates": [],
                }
            ],
        }
    ]


def test_macbert_does_not_load_backend_for_non_chinese_text(tmp_path) -> None:
    loader = Mock()
    corrector = MacBertCorrector(tmp_path, loader=loader)

    result = corrector.correct_raw(["2023 / MacBERT 18K"])

    assert result == [{"source": "2023 / MacBERT 18K", "target": "2023 / MacBERT 18K", "errors": [], "decisions": []}]
    loader.assert_not_called()


def test_macbert_adapter_keeps_mixed_text_finding_at_global_offset(tmp_path) -> None:
    corrector = MacBertCorrector(tmp_path, loader=lambda _: StubBackend())
    source = "2023年学员平均就业新资18K/月"

    result = corrector.correct([CorrectionInput(key="paragraph-1", text=source)])

    assert [finding.model_dump() for finding in result[0].findings] == [
        {
            "start": 11,
            "end": 12,
            "original": "新",
            "suggestion": "薪",
            "confidence": None,
        }
    ]

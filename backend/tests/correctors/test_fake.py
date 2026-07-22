from typofix_cn.correctors.base import CorrectionInput
from typofix_cn.correctors.fake import FakeCorrector


def test_fake_corrector_returns_source_relative_findings() -> None:
    corrector = FakeCorrector({"今天新情很好": [("新", "心", 2)]})
    result = corrector.correct([CorrectionInput(key="s1", text="今天新情很好")])
    assert result[0].findings[0].model_dump() == {
        "start": 2,
        "end": 3,
        "original": "新",
        "suggestion": "心",
        "confidence": None,
    }

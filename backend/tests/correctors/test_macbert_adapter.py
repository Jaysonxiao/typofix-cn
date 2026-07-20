from pathlib import Path

from typofix_cn.correctors.base import CorrectionInput
from typofix_cn.correctors.macbert import MacBertCorrector


class StubBackend:
    def correct_batch(self, texts):
        return [
            {
                "errors": [
                    ["", "简", 3],
                    ["错", "措", 1],
                ]
            }
        ]


def test_macbert_adapter_ignores_zero_length_findings() -> None:
    corrector = MacBertCorrector(Path("unused"), loader=lambda _: StubBackend())

    result = corrector.correct([CorrectionInput(key="s1", text="一错三四")])

    assert [finding.model_dump() for finding in result[0].findings] == [
        {"start": 1, "end": 2, "original": "错", "suggestion": "措", "confidence": None}
    ]

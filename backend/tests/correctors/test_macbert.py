from unittest.mock import Mock

from typofix_cn.correctors.base import CorrectionInput
from typofix_cn.correctors.macbert import MacBertCorrector


class StubBackend:
    def correct_batch(self, texts):
        return [{"source": text, "target": text.replace("新", "心"), "errors": [("新", "心", 2)]} for text in texts]


def test_macbert_loads_backend_once(monkeypatch, tmp_path) -> None:
    loader = Mock(return_value=StubBackend())
    corrector = MacBertCorrector(tmp_path, loader=loader)
    corrector.correct([CorrectionInput(key="a", text="今天新情很好")])
    corrector.correct([CorrectionInput(key="b", text="今天新情很好")])
    loader.assert_called_once_with(tmp_path)

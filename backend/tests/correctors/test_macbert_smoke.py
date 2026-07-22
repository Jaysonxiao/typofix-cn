import os

import pytest

from typofix_cn.correctors.base import CorrectionInput
from typofix_cn.correctors.macbert import MacBertCorrector


@pytest.mark.model
def test_real_macbert_corrects_known_typo(tmp_path) -> None:
    if os.getenv("TYPOFIX_RUN_MODEL_TESTS") != "1":
        pytest.skip("set TYPOFIX_RUN_MODEL_TESTS=1 to run the downloaded model")
    result = MacBertCorrector(tmp_path).correct([CorrectionInput(key="s1", text="今天新情很好")])
    assert any(finding.original == "新" and finding.suggestion == "心" for finding in result[0].findings)

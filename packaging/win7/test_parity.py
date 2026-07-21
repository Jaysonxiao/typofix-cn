from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("verify_model_parity.py")
SPEC = importlib.util.spec_from_file_location("verify_model_parity", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_canonical_result_ignores_non_contract_fields() -> None:
    legacy = {
        "source": "今天新情很好",
        "target": "今天心情很好",
        "errors": [("新", "心", 2)],
        "decisions": [{"provider": "model", "accepted": True, "reason": "legacy"}],
    }
    onnx = {
        "source": "今天新情很好",
        "target": "今天心情很好",
        "errors": [["新", "心", 2]],
        "decisions": [{"provider": "model", "accepted": True, "reason": "onnx"}],
    }
    assert MODULE.canonical_result(legacy) == MODULE.canonical_result(onnx)


def test_compare_results_reports_source_and_error_mismatch() -> None:
    mismatch = MODULE.compare_results(
        {"source": "新资", "target": "薪资", "errors": [("新", "薪", 0)]},
        {"source": "新资", "target": "新资", "errors": []},
    )
    assert mismatch is not None
    assert "target" in mismatch
    assert "errors" in mismatch

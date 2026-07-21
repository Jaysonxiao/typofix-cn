from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional


def load_cases(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("parity case file must contain a JSON list")
    cases: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict) or not isinstance(item.get("text"), str):
            raise ValueError("each parity case requires a text field")
        cases.append({"name": str(item.get("name", f"case-{len(cases) + 1}")), "text": item["text"]})
    return cases


def canonical_result(result: dict[str, Any]) -> tuple[str, str, tuple[tuple[str, str, int], ...]]:
    errors: list[tuple[str, str, int]] = []
    for error in result.get("errors", []):
        if isinstance(error, (list, tuple)) and len(error) == 3:
            errors.append((str(error[0]), str(error[1]), int(error[2])))
    return (
        str(result.get("source", "")),
        str(result.get("target", "")),
        tuple(sorted(errors, key=lambda item: (item[2], item[0], item[1]))),
    )


def compare_results(legacy: dict[str, Any], onnx: dict[str, Any]) -> Optional[str]:
    left = canonical_result(legacy)
    right = canonical_result(onnx)
    if left == right:
        return None
    return f"target/errors mismatch: legacy={left!r}; onnx={right!r}"


def _default_path(relative: str) -> Path:
    return Path(__file__).resolve().parents[2] / relative


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Compare legacy and FP32 ONNX MacBERT results offline")
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("sample_inputs") / "parity_cases.json")
    parser.add_argument("--model-root", type=Path, default=None)
    parser.add_argument("--confusion-path", type=Path, default=None)
    args = parser.parse_args(argv)

    model_root = args.model_root or (Path(os.environ["TYPOFIX_MODEL_ROOT"]) if os.environ.get("TYPOFIX_MODEL_ROOT") else _default_path("data/models/macbert4csc-base-chinese"))
    confusion_path = args.confusion_path or (Path(os.environ["TYPOFIX_CONFUSION_PATH"]) if os.environ.get("TYPOFIX_CONFUSION_PATH") else _default_path("data/confusions/default.txt"))
    if not (model_root / "onnx" / "model.onnx").is_file():
        raise FileNotFoundError(f"missing ONNX model: {model_root / 'onnx' / 'model.onnx'}")
    if not (model_root / "config.json").is_file():
        raise FileNotFoundError(f"missing legacy model config: {model_root / 'config.json'}")

    backend_src = _default_path("backend/src")
    if str(backend_src) not in sys.path:
        sys.path.insert(0, str(backend_src))
    from typofix_cn.correctors.macbert import MacBertCorrector

    cases = load_cases(args.cases)
    texts = [item["text"] for item in cases]
    legacy = MacBertCorrector(model_root, confusion_path=confusion_path, backend_kind="legacy").correct_raw(texts)
    onnx = MacBertCorrector(model_root, confusion_path=confusion_path, backend_kind="onnx").correct_raw(texts)
    mismatches: list[str] = []
    for case, left, right in zip(cases, legacy, onnx):
        mismatch = compare_results(left, right)
        if mismatch:
            mismatches.append(f"{case['name']}: {mismatch}")
    if mismatches:
        print("Parity check failed:")
        print("\n".join(mismatches))
        return 1
    print(f"Parity check passed for {len(cases)} cases (legacy == FP32 ONNX).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

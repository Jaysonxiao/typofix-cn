from __future__ import annotations

from pathlib import Path
from typing import Any

from .onnx_candidates import OnnxMacBertCandidateProvider


class OnnxMacBertBackend:
    def __init__(self, model_path: Path, *, threads: int = 2) -> None:
        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer
        except ImportError as exc:
            raise RuntimeError("ONNX Runtime or tokenizers is not installed") from exc

        model_dir = Path(model_path) / "onnx"
        model_file = model_dir / "model.onnx"
        tokenizer_file = model_dir / "tokenizer.json"
        if not model_file.is_file() or not tokenizer_file.is_file():
            raise FileNotFoundError(f"ONNX model assets are missing under {model_dir}")

        options = ort.SessionOptions()
        options.intra_op_num_threads = max(1, int(threads))
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        self.tokenizer = Tokenizer.from_file(str(tokenizer_file))
        self.session = ort.InferenceSession(
            str(model_file),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )

    def candidate_provider(self, **kwargs: Any) -> OnnxMacBertCandidateProvider:
        return OnnxMacBertCandidateProvider(self, **kwargs)

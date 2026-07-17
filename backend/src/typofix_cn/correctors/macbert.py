from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .base import CorrectionFinding, CorrectionInput, CorrectionResult


class ModelDependencyMissing(RuntimeError):
    pass


class ModelNotReady(RuntimeError):
    pass


class ModelInferenceError(RuntimeError):
    pass


def _load_backend(model_path: Path) -> Any:
    try:
        from pycorrector import MacBertCorrector as Backend
    except ImportError as exc:
        raise ModelDependencyMissing("未安装模型依赖，请安装 typofix-cn[model]") from exc
    return Backend(str(model_path))


class MacBertCorrector:
    def __init__(self, model_path: Path, *, loader: Callable[[Path], Any] | None = None) -> None:
        self.model_path = Path(model_path)
        self._loader = loader or _load_backend
        self._backend: Any | None = None

    def _ensure_backend(self) -> Any:
        if self._backend is None:
            try:
                self._backend = self._loader(self.model_path)
            except ModelDependencyMissing:
                raise
            except Exception as exc:
                raise ModelNotReady("MacBERT 模型未就绪，请先下载模型") from exc
        return self._backend

    def correct(self, inputs: Sequence[CorrectionInput]) -> list[CorrectionResult]:
        if not inputs:
            return []
        backend = self._ensure_backend()
        try:
            batches = backend.correct_batch([item.text for item in inputs])
        except Exception as exc:
            raise ModelInferenceError("MacBERT 推理失败，请查看服务端日志") from exc
        return [self._convert(item, raw) for item, raw in zip(inputs, batches, strict=True)]

    @staticmethod
    def _convert(item: CorrectionInput, raw: dict[str, Any]) -> CorrectionResult:
        findings: list[CorrectionFinding] = []
        for error in raw.get("errors", []):
            if len(error) != 3:
                continue
            original, suggestion, start = error
            if not isinstance(start, int) or item.text[start : start + len(original)] != original:
                continue
            findings.append(CorrectionFinding(start=start, end=start + len(original), original=original, suggestion=suggestion))
        return CorrectionResult(key=item.key, source=item.text, findings=findings)

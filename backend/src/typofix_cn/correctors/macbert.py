import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .base import CorrectionFinding, CorrectionInput, CorrectionResult


_CHINESE_SPAN_PATTERN = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF]+")


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
        batches = self.correct_raw([item.text for item in inputs])
        return [self._convert(item, raw) for item, raw in zip(inputs, batches, strict=True)]

    def correct_raw(self, texts: Sequence[str], *, threshold: float = 0.7) -> list[dict[str, Any]]:
        if not texts:
            return []

        results: list[dict[str, Any]] = [{"source": text, "target": text, "errors": []} for text in texts]
        spans: list[tuple[int, int, str]] = []
        for text_index, source in enumerate(texts):
            spans.extend(
                (text_index, match.start(), match.group())
                for match in _CHINESE_SPAN_PATTERN.finditer(source)
            )
        if not spans:
            return results

        backend = self._ensure_backend()
        try:
            corrected_spans = list(
                backend.correct_batch(
                    [span_text for _, _, span_text in spans],
                    threshold=threshold,
                )
            )
            if len(corrected_spans) != len(spans):
                raise ValueError("MacBERT 返回数量与输入片段数量不一致")
        except Exception as exc:
            raise ModelInferenceError("MacBERT 推理失败，请查看服务端日志") from exc

        targets = [list(text) for text in texts]
        merged_errors: list[list[tuple[str, str, int]]] = [[] for _ in texts]
        for (text_index, span_start, source_span), raw in zip(spans, corrected_spans, strict=True):
            target_span = raw.get("target", source_span)
            if not isinstance(target_span, str) or len(target_span) != len(source_span):
                continue
            targets[text_index][span_start : span_start + len(source_span)] = target_span
            for error in raw.get("errors", []):
                if not isinstance(error, (list, tuple)) or len(error) != 3:
                    continue
                original, suggestion, local_start = error
                if not isinstance(original, str) or not isinstance(suggestion, str):
                    continue
                if not original or len(original) != len(suggestion):
                    continue
                if not isinstance(local_start, int) or local_start < 0:
                    continue
                if source_span[local_start : local_start + len(original)] != original:
                    continue
                merged_errors[text_index].append((original, suggestion, span_start + local_start))

        for index, result in enumerate(results):
            result["target"] = "".join(targets[index])
            result["errors"] = merged_errors[index]
        return results

    @staticmethod
    def _convert(item: CorrectionInput, raw: dict[str, Any]) -> CorrectionResult:
        findings: list[CorrectionFinding] = []
        for error in raw.get("errors", []):
            if len(error) != 3:
                continue
            original, suggestion, start = error
            if not original or not suggestion or len(original) != len(suggestion):
                continue
            if not isinstance(start, int) or item.text[start : start + len(original)] != original:
                continue
            findings.append(CorrectionFinding(start=start, end=start + len(original), original=original, suggestion=suggestion))
        return CorrectionResult(key=item.key, source=item.text, findings=findings)

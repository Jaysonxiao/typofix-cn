from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .base import CorrectionFinding, CorrectionInput, CorrectionResult
from .confusions import ConfusionConfigError, ConfusionMatch, TextConfusionRepository
from .macbert_candidates import MacBertCandidateProvider
from .macbert_decisions import CorrectionDecision, build_decisions


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
    def __init__(
        self,
        model_path: Path,
        *,
        loader: Callable[[Path], Any] | None = None,
        confusion_path: Path | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self._loader = loader or _load_backend
        self._backend: Any | None = None
        if confusion_path is not None:
            self.confusion_path = Path(confusion_path)
        elif self.model_path.parent.name == "models":
            self.confusion_path = self.model_path.parent.parent / "confusions" / "default.txt"
        else:
            self.confusion_path = self.model_path.parent / "confusions" / "default.txt"

    def _ensure_backend(self) -> Any:
        if self._backend is None:
            try:
                self._backend = self._loader(self.model_path)
            except ModelDependencyMissing:
                raise
            except Exception as exc:
                raise ModelNotReady("MacBERT 模型未就绪，请先下载模型") from exc
        return self._backend

    def correct(
        self,
        inputs: Sequence[CorrectionInput],
        *,
        detection_threshold: float = 0.50,
        correction_threshold: float = 0.30,
    ) -> list[CorrectionResult]:
        batches = self.correct_raw(
            [item.text for item in inputs],
            detection_threshold=detection_threshold,
            correction_threshold=correction_threshold,
        )
        converted: list[CorrectionResult] = []
        for item, raw in zip(inputs, batches, strict=True):
            confusion_ranges = {
                (int(decision["start"]), int(decision["end"]))
                for decision in raw.get("decisions", [])
                if decision.get("provider") == "confusion"
            }
            filtered = dict(raw)
            filtered["errors"] = [error for error in raw.get("errors", []) if (error[2], error[2] + len(error[0])) not in confusion_ranges]
            converted.append(self._convert(item, filtered))
        return converted

    def correct_raw(
        self,
        texts: Sequence[str],
        *,
        detection_threshold: float = 0.50,
        correction_threshold: float = 0.30,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        if not texts:
            return []
        results: list[dict[str, Any]] = [
            {"source": text, "target": text, "errors": [], "decisions": []} for text in texts
        ]
        eligible_indices = [index for index, text in enumerate(texts) if _CHINESE_SPAN_PATTERN.search(text)]
        if not eligible_indices:
            return results
        backend = self._ensure_backend()
        confusion_repository = TextConfusionRepository(self.confusion_path)
        try:
            confusion_matches = {index: confusion_repository.match(texts[index]) for index in eligible_indices}
        except ConfusionConfigError:
            raise

        provider = MacBertCandidateProvider(backend)
        if provider.available:
            try:
                candidate_batches = provider.predict([texts[index] for index in eligible_indices])
            except Exception as exc:
                raise ModelInferenceError("MacBERT 推理失败，请查看服务端日志") from exc
            for index, candidates in zip(eligible_indices, candidate_batches, strict=True):
                decisions = build_decisions(
                    texts[index],
                    confusion_matches[index],
                    candidates,
                    detection_threshold=detection_threshold,
                    correction_threshold=correction_threshold,
                )
                self._set_result(results[index], texts[index], decisions)
            return results

        fallback_threshold = correction_threshold if threshold is None else threshold
        self._fallback_batch(results, texts, backend, eligible_indices, confusion_matches, fallback_threshold)
        return results

    def _fallback_batch(
        self,
        results: list[dict[str, Any]],
        texts: Sequence[str],
        backend: Any,
        eligible_indices: list[int],
        confusion_matches: dict[int, list[ConfusionMatch]],
        threshold: float,
    ) -> None:
        spans: list[tuple[int, int, str]] = []
        for text_index in eligible_indices:
            spans.extend((text_index, match.start(), match.group()) for match in _CHINESE_SPAN_PATTERN.finditer(texts[text_index]))
        try:
            corrected_spans = list(backend.correct_batch([span for _, _, span in spans], threshold=threshold))
            if len(corrected_spans) != len(spans):
                raise ValueError("MacBERT 返回数量与输入片段数量不一致")
        except Exception as exc:
            raise ModelInferenceError("MacBERT 推理失败，请查看服务端日志") from exc
        decisions_by_index: dict[int, list[CorrectionDecision]] = {index: list(_confusion_decisions(confusion_matches[index])) for index in eligible_indices}
        for (text_index, span_start, source_span), raw in zip(spans, corrected_spans, strict=True):
            for error in raw.get("errors", []):
                if not isinstance(error, (list, tuple)) or len(error) != 3:
                    continue
                original, suggestion, local_start = error
                if not isinstance(original, str) or not isinstance(suggestion, str) or not isinstance(local_start, int):
                    continue
                start = span_start + local_start
                end = start + len(original)
                if not original or len(original) != len(suggestion) or texts[text_index][start:end] != original:
                    continue
                if any(start < item.end and end > item.start for item in decisions_by_index[text_index] if item.accepted):
                    continue
                decisions_by_index[text_index].append(
                    CorrectionDecision(
                        start=start,
                        end=end,
                        source=original,
                        suggestion=suggestion,
                        provider="model",
                        original_score=None,
                        suggestion_score=None,
                        detection_score=None,
                        accepted=True,
                        reason="backend_fallback",
                    )
                )
        for text_index in eligible_indices:
            self._set_result(results[text_index], texts[text_index], sorted(decisions_by_index[text_index], key=lambda item: item.start))

    @staticmethod
    def _set_result(result: dict[str, Any], source: str, decisions: Sequence[CorrectionDecision]) -> None:
        target = list(source)
        errors: list[tuple[str, str, int]] = []
        for decision in sorted((item for item in decisions if item.accepted), key=lambda item: item.start):
            if not decision.suggestion or source[decision.start : decision.end] != decision.source:
                continue
            target[decision.start : decision.end] = decision.suggestion
            errors.append((decision.source, decision.suggestion, decision.start))
        result["target"] = "".join(target)
        result["errors"] = errors
        result["decisions"] = [decision.as_dict() for decision in decisions]

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


def _confusion_decisions(matches: Sequence[ConfusionMatch]) -> list[CorrectionDecision]:
    return [
        CorrectionDecision(
            start=item.start,
            end=item.end,
            source=item.source,
            suggestion=item.target,
            provider="confusion",
            original_score=None,
            suggestion_score=None,
            detection_score=None,
            accepted=True,
            reason="confusion_exact_match",
        )
        for item in matches
    ]

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence

try:
    import torch
except ImportError:  # pragma: no cover - exercised in the rules-only installation
    torch = None  # type: ignore[assignment]

from typofix_cn.documents.chunking import TextChunk, chunk_sentence


_HAN_ONLY = re.compile(r"^[\u3400-\u4DBF\u4E00-\u9FFF]$")
_MODEL_INPUTS = {"input_ids", "attention_mask", "token_type_ids"}


@dataclass(frozen=True)
class Candidate:
    text: str
    score: float


@dataclass(frozen=True)
class MacBertCandidate:
    start: int
    end: int
    source: str
    original_score: float
    candidates: tuple[Candidate, ...]


class MacBertCandidateProvider:
    """Read MacBERT logits and map single-Han candidates to full-text offsets."""

    def __init__(self, backend: Any, *, max_chars: int = 120, overlap: int = 16, top_k: int = 5) -> None:
        self.backend = backend
        self.max_chars = max_chars
        self.overlap = overlap
        self.top_k = top_k
        self.tokenizer = getattr(backend, "tokenizer", None)
        self.model = getattr(backend, "model", None)

    @property
    def available(self) -> bool:
        return bool(torch is not None and self.tokenizer is not None and self.model is not None and getattr(self.tokenizer, "is_fast", False))

    def predict(self, texts: Sequence[str]) -> list[list[MacBertCandidate]]:
        if not self.available:
            raise RuntimeError("fast tokenizer and model logits are unavailable")
        windows: list[tuple[int, TextChunk]] = []
        for text_index, text in enumerate(texts):
            chunks = [TextChunk(text=text, start=0, end=len(text))] if len(text) <= self.max_chars else chunk_sentence(text, max_chars=self.max_chars, overlap=self.overlap)
            windows.extend((text_index, chunk) for chunk in chunks)
        if not windows:
            return [[] for _ in texts]

        batch_texts = [chunk.text for _, chunk in windows]
        encoded = self.tokenizer(
            batch_texts,
            padding=True,
            return_tensors="pt",
            return_offsets_mapping=True,
            return_special_tokens_mask=True,
        )
        model_inputs = {key: value for key, value in encoded.items() if key in _MODEL_INPUTS}
        device = self._device()
        model_inputs = {key: value.to(device) for key, value in model_inputs.items()}
        with torch.no_grad():
            outputs = self.model(**model_inputs)
        logits = getattr(outputs, "logits", outputs[0] if isinstance(outputs, (tuple, list)) else outputs)
        if logits.ndim != 3:
            raise ValueError("MacBERT logits must have shape [batch, sequence, vocabulary]")
        offsets = encoded["offset_mapping"]
        masks = encoded.get("special_tokens_mask")
        attention = encoded.get("attention_mask")
        input_ids = encoded["input_ids"]
        results: list[list[MacBertCandidate]] = [[] for _ in texts]
        for window_index, (text_index, chunk) in enumerate(windows):
            window_candidates = self._decode_window(
                chunk,
                input_ids[window_index],
                logits[window_index],
                offsets[window_index],
                masks[window_index] if masks is not None else None,
                attention[window_index] if attention is not None else None,
            )
            results[text_index].extend(window_candidates)
        for index, candidates in enumerate(results):
            deduped: dict[tuple[int, int], MacBertCandidate] = {}
            for candidate in candidates:
                key = (candidate.start, candidate.end)
                previous = deduped.get(key)
                if previous is None or self._best_score(candidate) > self._best_score(previous):
                    deduped[key] = candidate
            results[index] = sorted(deduped.values(), key=lambda item: (item.start, item.end))
        return results

    def _decode_window(
        self,
        chunk: TextChunk,
        input_ids: torch.Tensor,
        logits: torch.Tensor,
        offsets: torch.Tensor,
        special_tokens_mask: torch.Tensor | None,
        attention_mask: torch.Tensor | None,
    ) -> list[MacBertCandidate]:
        decoded: list[MacBertCandidate] = []
        probabilities = torch.softmax(logits, dim=-1)
        for token_index, pair in enumerate(offsets.tolist()):
            if attention_mask is not None and not int(attention_mask[token_index]):
                continue
            if special_tokens_mask is not None and int(special_tokens_mask[token_index]):
                continue
            token_start, token_end = (int(pair[0]), int(pair[1]))
            if token_end - token_start != 1:
                continue
            absolute_start = chunk.start + token_start
            absolute_end = chunk.start + token_end
            source = chunk.text[token_start:token_end]
            if not _HAN_ONLY.fullmatch(source):
                continue
            row = probabilities[token_index]
            original_id = int(input_ids[token_index])
            original_score = float(row[original_id].item())
            values, ids = torch.topk(row, k=min(self.top_k + 1, row.shape[-1]))
            candidates: list[Candidate] = []
            for value, candidate_id in zip(values.tolist(), ids.tolist(), strict=True):
                candidate_text = self._decode_token(int(candidate_id))
                if candidate_text == source or not _HAN_ONLY.fullmatch(candidate_text):
                    continue
                candidates.append(Candidate(text=candidate_text, score=float(value)))
                if len(candidates) == self.top_k:
                    break
            if candidates:
                decoded.append(
                    MacBertCandidate(
                        start=absolute_start,
                        end=absolute_end,
                        source=source,
                        original_score=original_score,
                        candidates=tuple(candidates),
                    )
                )
        return decoded

    def _decode_token(self, token_id: int) -> str:
        token_strings = getattr(self.tokenizer, "convert_ids_to_tokens", None)
        if token_strings is not None:
            token = token_strings([token_id])[0]
            if not isinstance(token, str) or token.startswith("##"):
                return ""
        try:
            decoded = self.tokenizer.decode([token_id], skip_special_tokens=True, clean_up_tokenization_spaces=False)
        except TypeError:
            decoded = self.tokenizer.decode([token_id], skip_special_tokens=True)
        return decoded.strip() if isinstance(decoded, str) else ""

    def _device(self) -> torch.device:
        try:
            return next(self.model.parameters()).device
        except (AttributeError, StopIteration):
            return torch.device("cpu")

    @staticmethod
    def _best_score(candidate: MacBertCandidate) -> float:
        return candidate.candidates[0].score if candidate.candidates else -1.0

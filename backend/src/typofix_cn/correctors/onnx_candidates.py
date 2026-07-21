from __future__ import annotations

import re
from typing import Any, Sequence

import numpy as np

from typofix_cn.documents.chunking import TextChunk, chunk_sentence

from .macbert_types import Candidate, MacBertCandidate


_HAN_ONLY = re.compile(r"^[\u3400-\u4DBF\u4E00-\u9FFF]$")


class OnnxMacBertCandidateProvider:
    """Decode FP32 ONNX MacBERT logits into the shared candidate contract."""

    def __init__(self, backend: Any, *, max_chars: int = 120, overlap: int = 16, top_k: int = 5) -> None:
        self.backend = backend
        self.max_chars = max_chars
        self.overlap = overlap
        self.top_k = top_k
        self.tokenizer = backend.tokenizer
        self.session = backend.session
        self._input_names = {item.name for item in self.session.get_inputs()}

    @property
    def available(self) -> bool:
        return bool(self.tokenizer is not None and self.session is not None)

    def predict(self, texts: Sequence[str]) -> list[list[MacBertCandidate]]:
        if not texts:
            return []
        windows: list[tuple[int, TextChunk]] = []
        for text_index, text in enumerate(texts):
            chunks = (
                [TextChunk(text=text, start=0, end=len(text))]
                if len(text) <= self.max_chars
                else chunk_sentence(text, max_chars=self.max_chars, overlap=self.overlap)
            )
            windows.extend((text_index, chunk) for chunk in chunks)
        if not windows:
            return [[] for _ in texts]

        encodings = self.tokenizer.encode_batch([chunk.text for _, chunk in windows])
        model_inputs = self._model_inputs(encodings)
        outputs = self.session.run(None, model_inputs)
        logits = self._logits(outputs)
        results: list[list[MacBertCandidate]] = [[] for _ in texts]
        for window_index, (text_index, chunk) in enumerate(windows):
            results[text_index].extend(self._decode_window(chunk, encodings[window_index], logits[window_index]))

        for index, candidates in enumerate(results):
            deduped: dict[tuple[int, int], MacBertCandidate] = {}
            for candidate in candidates:
                key = (candidate.start, candidate.end)
                previous = deduped.get(key)
                if previous is None or self._best_score(candidate) > self._best_score(previous):
                    deduped[key] = candidate
            results[index] = sorted(deduped.values(), key=lambda item: (item.start, item.end))
        return results

    def _model_inputs(self, encodings: Sequence[Any]) -> dict[str, np.ndarray]:
        max_length = max(len(encoding.ids) for encoding in encodings)
        input_ids = np.zeros((len(encodings), max_length), dtype=np.int64)
        attention_mask = np.zeros((len(encodings), max_length), dtype=np.int64)
        token_type_ids = np.zeros((len(encodings), max_length), dtype=np.int64)
        for row, encoding in enumerate(encodings):
            length = len(encoding.ids)
            input_ids[row, :length] = encoding.ids
            attention_mask[row, :length] = encoding.attention_mask
            token_type_ids[row, :length] = encoding.type_ids

        values = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "token_type_ids": token_type_ids,
        }
        return {name: values[name] for name in self._input_names if name in values}

    @staticmethod
    def _logits(outputs: Sequence[Any]) -> np.ndarray:
        for output in outputs:
            array = np.asarray(output)
            if array.ndim == 3:
                return array
        raise ValueError("MacBERT ONNX logits must have shape [batch, sequence, vocabulary]")

    def _decode_window(self, chunk: TextChunk, encoding: Any, logits: np.ndarray) -> list[MacBertCandidate]:
        if logits.shape[0] != len(encoding.ids):
            raise ValueError("MacBERT ONNX sequence length does not match tokenizer output")
        probabilities = self._softmax(logits)
        decoded: list[MacBertCandidate] = []
        for token_index, pair in enumerate(encoding.offsets):
            if not int(encoding.attention_mask[token_index]) or int(encoding.special_tokens_mask[token_index]):
                continue
            token_start, token_end = int(pair[0]), int(pair[1])
            if token_end - token_start != 1:
                continue
            source = chunk.text[token_start:token_end]
            if not _HAN_ONLY.fullmatch(source):
                continue
            absolute_start = chunk.start + token_start
            row = probabilities[token_index]
            original_id = int(encoding.ids[token_index])
            candidates: list[Candidate] = []
            for candidate_id in np.argsort(row)[::-1][: self.top_k + 1].tolist():
                candidate_text = self._decode_token(int(candidate_id))
                if candidate_text == source or not _HAN_ONLY.fullmatch(candidate_text):
                    continue
                candidates.append(Candidate(text=candidate_text, score=float(row[candidate_id])))
                if len(candidates) == self.top_k:
                    break
            if candidates:
                decoded.append(
                    MacBertCandidate(
                        start=absolute_start,
                        end=absolute_start + 1,
                        source=source,
                        original_score=float(row[original_id]),
                        candidates=tuple(candidates),
                    )
                )
        return decoded

    @staticmethod
    def _softmax(logits: np.ndarray) -> np.ndarray:
        shifted = logits - np.max(logits, axis=-1, keepdims=True)
        exponentials = np.exp(shifted)
        return exponentials / np.sum(exponentials, axis=-1, keepdims=True)

    def _decode_token(self, token_id: int) -> str:
        token = self.tokenizer.id_to_token(token_id)
        if not isinstance(token, str) or token.startswith("##"):
            return ""
        try:
            decoded = self.tokenizer.decode([token_id], skip_special_tokens=True, clean_up_tokenization_spaces=False)
        except TypeError:
            decoded = self.tokenizer.decode([token_id], skip_special_tokens=True)
        return decoded.strip() if isinstance(decoded, str) else ""

    @staticmethod
    def _best_score(candidate: MacBertCandidate) -> float:
        return candidate.candidates[0].score if candidate.candidates else -1.0

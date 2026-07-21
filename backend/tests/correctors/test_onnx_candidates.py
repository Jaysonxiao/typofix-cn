from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from typofix_cn.correctors.onnx_candidates import OnnxMacBertCandidateProvider


class FakeEncoding:
    def __init__(self, ids, offsets, special_tokens_mask):
        self.ids = ids
        self.attention_mask = [1] * len(ids)
        self.type_ids = [0] * len(ids)
        self.offsets = offsets
        self.special_tokens_mask = special_tokens_mask


class FakeTokenizer:
    def encode_batch(self, texts):
        assert texts == ["2023新资18K"]
        return [
            FakeEncoding(
                ids=[101, 200, 201, 1, 2, 202, 102],
                offsets=[(0, 0), (0, 3), (3, 4), (4, 5), (5, 6), (6, 9), (0, 0)],
                special_tokens_mask=[1, 0, 0, 0, 0, 0, 1],
            )
        ]

    def id_to_token(self, token_id):
        return {1: "新", 2: "资", 3: "金", 4: "咨"}.get(token_id, "[UNK]")

    def decode(self, ids, **kwargs):
        return self.id_to_token(ids[0])


class FakeSession:
    def get_inputs(self):
        return [SimpleNamespace(name=name) for name in ("input_ids", "attention_mask", "token_type_ids")]

    def run(self, output_names, inputs):
        assert output_names is None
        assert inputs["input_ids"].tolist() == [[101, 200, 201, 1, 2, 202, 102]]
        logits = np.full((1, 7, 205), -10.0, dtype=np.float32)
        logits[0, 3, 1] = 0.0
        logits[0, 3, 3] = 3.0
        logits[0, 3, 4] = 2.0
        logits[0, 4, 2] = 3.0
        logits[0, 4, 4] = 2.0
        return [logits]


def test_onnx_provider_maps_single_han_candidates_to_absolute_offsets() -> None:
    backend = SimpleNamespace(tokenizer=FakeTokenizer(), session=FakeSession())

    records = OnnxMacBertCandidateProvider(backend).predict(["2023新资18K"])

    assert [(item.start, item.end, item.source) for item in records[0]] == [(4, 5, "新"), (5, 6, "资")]
    assert records[0][0].candidates[0].text == "金"
    assert records[0][0].original_score < records[0][0].candidates[0].score


def test_onnx_provider_returns_empty_for_empty_input() -> None:
    backend = SimpleNamespace(tokenizer=FakeTokenizer(), session=FakeSession())

    assert OnnxMacBertCandidateProvider(backend).predict([]) == []

from __future__ import annotations

from types import SimpleNamespace

import torch

from typofix_cn.correctors.macbert_candidates import MacBertCandidateProvider


class FakeTokenizer:
    is_fast = True

    def __init__(self) -> None:
        self.ids = {"新": 1, "资": 2, "薪": 3, "情": 4, "好": 5, "甲": 6, "乙": 7}
        self.tokens = {value: key for key, value in self.ids.items()}

    def __call__(self, texts, **kwargs):
        input_ids = []
        attention = []
        offsets = []
        special = []
        for text in texts:
            row = [101]
            row_offsets = [(0, 0)]
            row_special = [1]
            index = 0
            while index < len(text):
                if text[index : index + 4] == "2023":
                    row.append(200)
                    row_offsets.append((index, index + 4))
                    row_special.append(0)
                    index += 4
                elif text[index : index + 3] == "18K":
                    row.append(201)
                    row_offsets.append((index, index + 3))
                    row_special.append(0)
                    index += 3
                else:
                    row.append(self.ids[text[index]])
                    row_offsets.append((index, index + 1))
                    row_special.append(0)
                    index += 1
            row.append(102)
            row_offsets.append((0, 0))
            row_special.append(1)
            input_ids.append(row)
            attention.append([1] * len(row))
            offsets.append(row_offsets)
            special.append(row_special)
        max_length = max(map(len, input_ids))
        for rows, pad_value in ((input_ids, 0), (attention, 0), (special, 1)):
            for row in rows:
                row.extend([pad_value] * (max_length - len(row)))
        for row in offsets:
            row.extend([(0, 0)] * (max_length - len(row)))
        return {
            "input_ids": torch.tensor(input_ids),
            "attention_mask": torch.tensor(attention),
            "offset_mapping": torch.tensor(offsets),
            "special_tokens_mask": torch.tensor(special),
        }

    def decode(self, ids, **kwargs):
        return self.tokens.get(int(ids[0]), "")

    def convert_ids_to_tokens(self, ids):
        return [self.tokens.get(int(item), "[UNK]") for item in ids]


class FakeModel:
    def parameters(self):
        yield torch.zeros(1)

    def __call__(self, **kwargs):
        input_ids = kwargs["input_ids"]
        logits = torch.full((input_ids.shape[0], input_ids.shape[1], 220), -8.0)
        for batch_index, row in enumerate(input_ids.tolist()):
            for token_index, token_id in enumerate(row):
                if token_id == 1:  # 新 -> 薪 is a strong candidate
                    logits[batch_index, token_index, 1] = 0.0
                    logits[batch_index, token_index, 3] = 2.0
                elif token_id == 2:  # 资 has no editable single-character candidate in this fixture
                    logits[batch_index, token_index, 2] = 3.0
                    logits[batch_index, token_index, 4] = -1.0
        return SimpleNamespace(logits=logits)


def test_provider_keeps_mixed_text_offsets_and_ignores_multi_character_tokens() -> None:
    provider = MacBertCandidateProvider(SimpleNamespace(tokenizer=FakeTokenizer(), model=FakeModel()))

    records = provider.predict(["2023新资18K"])

    assert [(record.start, record.end, record.source) for record in records[0]] == [(4, 5, "新"), (5, 6, "资")]
    assert records[0][0].candidates[0].text == "薪"


def test_provider_reports_capability_fallback_when_fast_offsets_are_unavailable() -> None:
    provider = MacBertCandidateProvider(SimpleNamespace(tokenizer=SimpleNamespace(is_fast=False), model=FakeModel()))

    assert provider.available is False


def test_provider_merges_long_text_overlap_by_absolute_position() -> None:
    text = "甲" * 119 + "新" + "资" + "乙" * 40
    provider = MacBertCandidateProvider(SimpleNamespace(tokenizer=FakeTokenizer(), model=FakeModel()))

    records = provider.predict([text])[0]

    assert all(0 <= record.start < record.end <= len(text) for record in records)
    assert len({(record.start, record.end) for record in records}) == len(records)

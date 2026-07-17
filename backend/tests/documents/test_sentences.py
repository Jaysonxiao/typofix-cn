from typofix_cn.documents.sentences import split_sentences


def test_sentence_offsets_reference_original_paragraph() -> None:
    sentences = split_sentences("第一句。第二句！末句")
    assert [(item.text, item.start, item.end) for item in sentences] == [
        ("第一句。", 0, 4),
        ("第二句！", 4, 8),
        ("末句", 8, 10),
    ]


def test_sentence_keeps_closing_quote_after_terminal_punctuation() -> None:
    sentences = split_sentences("他说：“完成了”。然后继续")
    assert [item.text for item in sentences] == ["他说：“完成了”。", "然后继续"]

import pytest

from typofix_cn.terms.repository import InvalidLibraryName, TextTermRepository


def test_repository_reads_bom_comments_blanks_and_duplicates(tmp_path) -> None:
    root = tmp_path / "term-libraries"
    root.mkdir()
    (root / "default.txt").write_text(
        "\ufeff麒麟操作系统\n# 说明\n\nMacBERT\nMacBERT\n", encoding="utf-8"
    )
    repository = TextTermRepository(root)
    assert repository.load("default").terms == ["麒麟操作系统", "MacBERT"]


def test_add_term_is_idempotent_and_rejects_path_names(tmp_path) -> None:
    repository = TextTermRepository(tmp_path)
    repository.create("default")
    repository.add("default", "自然语言处理")
    repository.add("default", "自然语言处理")
    assert repository.load("default").terms == ["自然语言处理"]
    with pytest.raises(InvalidLibraryName):
        repository.create("../escape")


def test_repository_rejects_empty_newline_and_long_terms(tmp_path) -> None:
    repository = TextTermRepository(tmp_path)
    repository.create("default")
    with pytest.raises(ValueError):
        repository.add("default", "")
    with pytest.raises(ValueError):
        repository.add("default", "包含\n换行")
    with pytest.raises(ValueError):
        repository.add("default", "甲" * 101)

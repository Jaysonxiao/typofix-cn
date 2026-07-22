from pathlib import Path

import pytest

from typofix_cn.correctors.confusions import ConfusionConfigError, TextConfusionRepository


def test_confusion_repository_parses_utf8_rules_and_uses_longest_non_overlapping_match(tmp_path: Path) -> None:
    path = tmp_path / "default.txt"
    path.write_text("# comment\n\n 新 => 薪\n新资 => 薪资\n", encoding="utf-8")

    repository = TextConfusionRepository(path)

    matches = repository.match("今日新资，新的数据")

    assert [(item.start, item.end, item.source, item.target) for item in matches] == [
        (2, 4, "新资", "薪资"),
        (5, 6, "新", "薪"),
    ]


def test_confusion_repository_reloads_when_file_changes(tmp_path: Path) -> None:
    path = tmp_path / "default.txt"
    path.write_text("新资 => 薪资\n", encoding="utf-8")
    repository = TextConfusionRepository(path)
    assert [(item.source, item.target) for item in repository.match("新资")] == [("新资", "薪资")]

    path.write_text("新资 => 薪资\n因该 => 应该\n", encoding="utf-8")

    assert [(item.source, item.target) for item in repository.match("因该")] == [("因该", "应该")]


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("新资 => 薪\n", "same number of Han characters"),
        ("new => 新\n", "Han characters only"),
        ("新资 => 薪资\n新资 => 新钱\n", "conflicting confusion rule"),
        ("新资 薪资\n", "source => target"),
    ],
)
def test_confusion_repository_rejects_invalid_rules(tmp_path: Path, content: str, message: str) -> None:
    path = tmp_path / "default.txt"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ConfusionConfigError, match=message):
        TextConfusionRepository(path).match("新资")


def test_confusion_repository_collapses_identical_duplicates(tmp_path: Path) -> None:
    path = tmp_path / "default.txt"
    path.write_text("新资 => 薪资\n新资 => 薪资\n", encoding="utf-8")

    matches = TextConfusionRepository(path).match("新资")

    assert len(matches) == 1

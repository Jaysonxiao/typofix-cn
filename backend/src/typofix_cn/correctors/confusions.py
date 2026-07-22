from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


_HAN_ONLY = re.compile(r"^[\u3400-\u4DBF\u4E00-\u9FFF]+$")


class ConfusionConfigError(ValueError):
    """Raised when the editable confusion file contains an unsafe rule."""


@dataclass(frozen=True)
class ConfusionRule:
    source: str
    target: str
    line_number: int


@dataclass(frozen=True)
class ConfusionMatch:
    start: int
    end: int
    source: str
    target: str
    line_number: int


class TextConfusionRepository:
    """Reloadable UTF-8 confusion rules used by the plain-text model test."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def rules(self) -> tuple[ConfusionRule, ...]:
        if not self.path.exists():
            return ()
        by_source: dict[str, ConfusionRule] = {}
        for line_number, raw_line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=>" not in line:
                raise ConfusionConfigError(f"line {line_number}: expected source => target")
            source, target = (part.strip() for part in line.split("=>", 1))
            if not source or not target:
                raise ConfusionConfigError(f"line {line_number}: source => target must not be empty")
            if not _HAN_ONLY.fullmatch(source) or not _HAN_ONLY.fullmatch(target):
                raise ConfusionConfigError(f"line {line_number}: source and target must contain Han characters only")
            if len(source) != len(target):
                raise ConfusionConfigError(f"line {line_number}: source and target must have the same number of Han characters")
            previous = by_source.get(source)
            if previous is not None:
                if previous.target != target:
                    raise ConfusionConfigError(
                        f"line {line_number}: conflicting confusion rule for {source!r} (line {previous.line_number})"
                    )
                continue
            by_source[source] = ConfusionRule(source=source, target=target, line_number=line_number)
        return tuple(by_source.values())

    def match(self, text: str) -> list[ConfusionMatch]:
        rules = self.rules()
        matches: list[ConfusionMatch] = []
        index = 0
        while index < len(text):
            candidates = [rule for rule in rules if text.startswith(rule.source, index)]
            if not candidates:
                index += 1
                continue
            rule = max(candidates, key=lambda item: len(item.source))
            matches.append(
                ConfusionMatch(
                    start=index,
                    end=index + len(rule.source),
                    source=rule.source,
                    target=rule.target,
                    line_number=rule.line_number,
                )
            )
            index += len(rule.source)
        return matches

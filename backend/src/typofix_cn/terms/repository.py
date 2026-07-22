from __future__ import annotations

from typing import Dict, FrozenSet, List, Set, Tuple
import hashlib
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .models import TermLibrary


class InvalidLibraryName(ValueError):
    pass


_VALID_NAME = re.compile(r"^[\w\-\u4e00-\u9fff]{1,80}$")


class TextTermRepository:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _validate_name(self, name: str) -> None:
        if not _VALID_NAME.fullmatch(name):
            raise InvalidLibraryName("术语库名称只能包含中文、字母、数字、下划线或短横线")

    def _path(self, name: str) -> Path:
        self._validate_name(name)
        return self.root / f"{name}.txt"

    def list(self) -> List[TermLibrary]:
        return [self.load(path.stem) for path in sorted(self.root.glob("*.txt"))]

    def create(self, name: str) -> TermLibrary:
        path = self._path(name)
        if path.exists():
            raise FileExistsError(f"术语库已存在：{name}")
        self._atomic_write(path, "")
        return self.load(name)

    def load(self, name: str) -> TermLibrary:
        path = self._path(name)
        if not path.exists():
            raise FileNotFoundError(f"术语库不存在：{name}")
        raw = path.read_text(encoding="utf-8-sig")
        terms: List[str] = []
        seen: Set[str] = set()
        for line in raw.splitlines():
            term = line.strip()
            if not term or term.startswith("#") or term in seen:
                continue
            terms.append(term)
            seen.add(term)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        return TermLibrary(name=name, terms=terms, modified_at=modified, content_sha256=digest)

    def add(self, name: str, term: str) -> TermLibrary:
        value = term.strip()
        if not value or "\n" in value or "\r" in value or len(value) > 100:
            raise ValueError("术语不能为空、不能包含换行，且最多 100 个字符")
        library = self.load(name)
        if value not in library.terms:
            content = "\n".join([*library.terms, value]) + "\n"
            self._atomic_write(self._path(name), content)
        return self.load(name)

    def delete(self, name: str, term: str) -> TermLibrary:
        library = self.load(name)
        remaining = [item for item in library.terms if item != term]
        self._atomic_write(self._path(name), "" if not remaining else "\n".join(remaining) + "\n")
        return self.load(name)

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

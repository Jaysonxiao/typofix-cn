from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UNION_PATTERN = re.compile(r"\b[A-Za-z_][\w.\[\], ]*\s+\|\s+[A-Za-z_][\w.\[\], ]*")
STRICT_ZIP_PATTERN = re.compile(r"\bzip\([^\n]*strict\s*=\s*True")


def test_source_has_no_python39_plus_union_or_strict_zip_syntax() -> None:
    offenders: list[str] = []
    for source_root in (ROOT / "backend" / "src", ROOT / "cli" / "src"):
        for path in source_root.rglob("*.py"):
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if UNION_PATTERN.search(line) or STRICT_ZIP_PATTERN.search(line):
                    offenders.append(f"{path}:{line_number}: {line.strip()}")
    assert offenders == [], "Python 3.8-incompatible syntax:\n" + "\n".join(offenders)

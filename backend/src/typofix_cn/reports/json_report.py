import json
import os
import tempfile
from pathlib import Path

from typofix_cn.domain.reports import AnalysisReport


class JsonReportWriter:
    def write(self, report: AnalysisReport, path: Path) -> None:
        content = json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2)
        self._atomic_write(path, content)

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

from __future__ import annotations

import logging
import sys
import threading
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from typofix_cn.api.app import create_app
from typofix_cn.config import Settings


@dataclass(frozen=True)
class RuntimePaths:
    root: Path
    data_dir: Path
    frontend_dir: Path
    model_dir: Path
    logs_dir: Path


def runtime_paths(executable: Optional[Path] = None) -> RuntimePaths:
    executable_path = Path(executable or sys.executable).resolve()
    root = executable_path.parent
    internal_root = root / "_internal"
    resource_root = internal_root if (internal_root / "frontend" / "dist" / "index.html").is_file() else root
    return RuntimePaths(
        root=root,
        data_dir=root / "data",
        frontend_dir=resource_root / "frontend" / "dist",
        model_dir=resource_root / "data" / "models" / "macbert4csc-base-chinese",
        logs_dir=root / "logs",
    )


def _configure_logging(paths: RuntimePaths) -> None:
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(paths.logs_dir / "typofix.log", encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(message)s")


def _open_browser() -> None:
    try:
        webbrowser.open("http://127.0.0.1:8000/")
    except Exception:
        logging.getLogger(__name__).exception("failed to open the browser")


def main() -> None:
    import uvicorn

    paths = runtime_paths()
    _configure_logging(paths)
    settings = Settings(
        data_dir=paths.data_dir,
        frontend_dir=paths.frontend_dir,
        model_dir=paths.model_dir,
        model_backend="onnx",
        model_threads=2,
    )
    application = create_app(settings)
    threading.Timer(1.0, _open_browser).start()
    uvicorn.run(application, host=settings.host, port=settings.port, log_config=None, access_log=False)


if __name__ == "__main__":
    main()

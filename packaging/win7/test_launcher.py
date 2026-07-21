from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import launcher


def test_runtime_paths_are_relative_to_frozen_executable(tmp_path: Path) -> None:
    executable = tmp_path / "TypofixCN" / "TypofixCN.exe"

    paths = launcher.runtime_paths(executable)

    assert paths.root == executable.parent
    assert paths.data_dir == executable.parent / "data"
    assert paths.frontend_dir == executable.parent / "frontend" / "dist"
    assert paths.model_dir == executable.parent / "data" / "models" / "macbert4csc-base-chinese"
    assert paths.logs_dir == executable.parent / "logs"


def test_runtime_paths_find_pyinstaller_internal_resources(tmp_path: Path) -> None:
    executable = tmp_path / "TypofixCN" / "TypofixCN.exe"
    internal_frontend = executable.parent / "_internal" / "frontend" / "dist"
    internal_model = executable.parent / "_internal" / "data" / "models" / "macbert4csc-base-chinese" / "onnx"
    internal_frontend.mkdir(parents=True)
    internal_model.mkdir(parents=True)
    (internal_frontend / "index.html").write_text("<html />", encoding="utf-8")
    (internal_model / "model.onnx").write_bytes(b"model")

    paths = launcher.runtime_paths(executable)

    assert paths.frontend_dir == internal_frontend
    assert paths.model_dir == internal_model.parent


def test_launcher_source_has_no_model_download_entrypoint() -> None:
    source = Path(launcher.__file__).read_text(encoding="utf-8")

    assert "snapshot_download" not in source
    assert "huggingface" not in source.lower()

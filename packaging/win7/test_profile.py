from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))
sys.path.insert(0, str(ROOT / "cli" / "src"))


def main() -> None:
    package_names = (
        "fastapi",
        "uvicorn",
        "onnxruntime",
        "tokenizers",
        "numpy",
        "python-docx",
        "pydantic",
        "typofix-cn",
    )
    for package_name in package_names:
        try:
            print(f"{package_name} {importlib.metadata.version(package_name)}")
        except importlib.metadata.PackageNotFoundError:
            if package_name == "typofix-cn":
                import typofix_cn  # noqa: F401
                print(f"{package_name} source")
            else:
                raise

    import fastapi  # noqa: F401
    import numpy  # noqa: F401
    import onnxruntime  # noqa: F401
    import pydantic  # noqa: F401
    import tokenizers  # noqa: F401
    import uvicorn  # noqa: F401
    import docx  # noqa: F401
    import typofix_cn  # noqa: F401

    forbidden = {"torch", "transformers", "pycorrector", "huggingface_hub"}
    imported_forbidden = forbidden.intersection(sys.modules)
    if imported_forbidden:
        raise AssertionError(f"Win7 launcher profile imported forbidden modules: {sorted(imported_forbidden)}")


if __name__ == "__main__":
    main()

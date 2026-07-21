import os
from pathlib import Path

from PyInstaller.building.build_main import Analysis, COLLECT, EXE, PYZ


spec_dir = Path(SPECPATH).resolve()
project_root = spec_dir.parents[1]
frontend_dir = Path(os.environ.get("TYPOFIX_FRONTEND_DIR", str(project_root / "frontend" / "dist")))
model_dir = Path(
    os.environ.get(
        "TYPOFIX_ONNX_MODEL_DIR",
        str(project_root / "data" / "models" / "macbert4csc-base-chinese" / "onnx"),
    )
)
if not (frontend_dir / "index.html").is_file():
    raise FileNotFoundError(f"frontend dist is missing: {frontend_dir}")
if not (model_dir / "model.onnx").is_file() or not (model_dir / "tokenizer.json").is_file():
    raise FileNotFoundError(f"FP32 ONNX model assets are missing: {model_dir}")

datas = [
    (str(frontend_dir), "frontend/dist"),
    (str(model_dir), "data/models/macbert4csc-base-chinese/onnx"),
]

analysis = Analysis(
    [str(spec_dir / "launcher.py")],
    pathex=[str(project_root / "backend" / "src"), str(project_root / "cli" / "src"), str(spec_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "onnxruntime",
        "tokenizers",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
    ],
    excludes=["torch", "transformers", "pycorrector", "huggingface_hub", "torchvision", "torchaudio"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name="TypofixCN", debug=False, console=False)
coll = COLLECT(exe, analysis.binaries, analysis.datas, name="TypofixCN")

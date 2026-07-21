# Windows 7 Offline FP32 ONNX Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully offline, directory-based `TypofixCN.exe` release for Windows 7 SP1 x64 that keeps the current MacBERT correction contract while running the FP32 ONNX model without Torch.

**Architecture:** Keep `MacBertCorrector` as the application boundary, add an ONNX Runtime candidate provider that emits the existing `MacBertCandidate` records, and let the existing decision/report pipeline continue unchanged. A frozen launcher will use an exe-sibling `data` directory, share one model instance across API tests and queued jobs, and package only the ONNX model assets.

**Tech Stack:** Python 3.8.10 x64, FastAPI/Uvicorn, ONNX Runtime CPU, tokenizers, NumPy, PyInstaller onedir, Vite static assets, Windows 7 SP1 x64 VM.

---

### Task 1: Add a separate Win7 build profile

**Files:**
- Create: `packaging/win7/requirements.txt`
- Create: `packaging/win7/build.ps1`
- Create: `packaging/win7/README-Windows7.txt`
- Modify: `README.md`

- [ ] **Step 1: Write the build-profile smoke test**

Create `packaging/win7/test_profile.py` that imports `fastapi`, `uvicorn`, `onnxruntime`, `tokenizers`, `numpy`, `docx`, `pydantic`, and `typofix_cn`, then prints their versions. It must also assert that importing `torch`, `transformers`, and `pycorrector` is not required by the launcher.

- [ ] **Step 2: Pin the runtime dependencies**

Write `packaging/win7/requirements.txt` with Python-3.8-compatible pins for FastAPI, Uvicorn, python-docx, Pydantic, pydantic-settings, python-multipart, platformdirs, Typer, NumPy, tokenizers, ONNX Runtime CPU, and PyInstaller. Keep Torch, Transformers, pycorrector, Hugging Face Hub, and dev packages out of this file.

- [ ] **Step 3: Add a reproducible PowerShell build entry point**

`build.ps1` must:

```powershell
$ErrorActionPreference = "Stop"
& "$PSScriptRoot\.venv-win7\Scripts\python.exe" -m pip install -r "$PSScriptRoot\requirements.txt"
Set-Location (Resolve-Path "$PSScriptRoot\..\..")
& "$PSScriptRoot\.venv-win7\Scripts\python.exe" "$PSScriptRoot\test_profile.py"
& "$PSScriptRoot\.venv-win7\Scripts\python.exe" -m PyInstaller "$PSScriptRoot\typofix_win7.spec" --noconfirm --clean
```

The script must fail before producing a release directory when the profile interpreter or any pinned dependency is missing.

- [ ] **Step 4: Document offline installation**

Document that the build machine downloads wheels and the target machine receives only the generated ZIP. Document the target as Windows 7 SP1 x64 and explicitly state that the target does not need Python, Node.js, or internet access.

- [ ] **Step 5: Run the profile smoke test**

Run from a Python 3.8 x64 environment:

```powershell
packaging\win7\.venv-win7\Scripts\python.exe packaging\win7\test_profile.py
```

Expected: all runtime imports succeed and no model download is attempted.

- [ ] **Step 6: Commit**

```powershell
git add packaging/win7/requirements.txt packaging/win7/build.ps1 packaging/win7/test_profile.py packaging/win7/README-Windows7.txt README.md
git commit -m "build: add Windows 7 offline profile"
```

### Task 2: Implement the FP32 ONNX MacBERT candidate provider

**Files:**
- Create: `backend/src/typofix_cn/correctors/onnx_macbert.py`
- Create: `backend/src/typofix_cn/correctors/onnx_candidates.py`
- Create: `backend/tests/correctors/test_onnx_candidates.py`
- Modify: `backend/src/typofix_cn/correctors/macbert.py`

- [ ] **Step 1: Write failing provider tests**

Use a fake tokenizer encoding with `ids`, `attention_mask`, `type_ids`, `offsets`, and `special_tokens_mask`, plus a fake session returning deterministic `[batch, sequence, vocabulary]` NumPy logits. Assert that `predict(["2023新资18K"])` returns only single-Han candidates with absolute offsets, Top-5 ordering, and the expected original score.

- [ ] **Step 2: Implement ONNX backend loading**

Add an `OnnxMacBertBackend` that loads `onnx/tokenizer.json` with `Tokenizer.from_file()` and creates one CPU `onnxruntime.InferenceSession` from `onnx/model.onnx`. Configure `intra_op_num_threads=2`, `inter_op_num_threads=1`, and sequential execution. Expose the tokenizer and session to the candidate provider.

- [ ] **Step 3: Implement tokenizer batching and logits decoding**

The provider must call `encode_batch`, pad the three model inputs to the batch maximum, invoke `session.run`, apply a numerically stable softmax row by row, and decode only vocabulary entries that represent one Han character. Preserve the existing `MacBertCandidate` dataclasses and `chunk_sentence` overlap behavior.

- [ ] **Step 4: Keep the existing PyTorch provider testable**

In `macbert.py`, choose the ONNX provider when the backend exposes `candidate_provider`; otherwise instantiate the existing `MacBertCandidateProvider`. Existing tests that inject a fake backend and monkeypatch `MacBertCandidateProvider` must continue to use the old path.

- [ ] **Step 5: Run focused tests**

```powershell
.venv\Scripts\python.exe -m pytest backend/tests/correctors/test_onnx_candidates.py backend/tests/correctors/test_macbert_pipeline.py -q
```

Expected: new ONNX decoding tests and all existing pipeline tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/src/typofix_cn/correctors/onnx_macbert.py backend/src/typofix_cn/correctors/onnx_candidates.py backend/src/typofix_cn/correctors/macbert.py backend/tests/correctors/test_onnx_candidates.py
git commit -m "feat: add FP32 ONNX MacBERT provider"
```

### Task 3: Make the application use one model instance

**Files:**
- Modify: `backend/src/typofix_cn/config.py`
- Modify: `backend/src/typofix_cn/api/app.py`
- Modify: `backend/tests/api/test_macbert.py`
- Create: `backend/tests/api/test_model_lifetime.py`

- [ ] **Step 1: Write the lifetime regression test**

Patch `MacBertCorrector` with a factory that counts constructions, create the app, submit one model test request and one queued full job, and assert that exactly one corrector/backend is used by both paths.

- [ ] **Step 2: Add explicit backend and thread settings**

Add `model_backend: str = "auto"` and `model_threads: int = 2` to `Settings`. The launcher will pass `model_backend="onnx"`; normal development keeps `auto`, which selects ONNX when the model directory contains `onnx/model.onnx` and otherwise retains the legacy backend.

- [ ] **Step 3: Share the corrector in `create_app`**

Construct one non-rules `MacBertCorrector` beside the queue, close over it in `run_job`, and use it in `/api/v1/macbert/test`. Keep `FakeCorrector` for `rules_only` jobs. Do not create a new MacBERT corrector inside every job.

- [ ] **Step 4: Preserve error mapping**

Map missing ONNX files, missing ONNX Runtime, session creation errors, and inference errors to the existing `ModelDependencyMissing`, `ModelNotReady`, and `ModelInferenceError` paths so API responses and job manifests retain their current shape.

- [ ] **Step 5: Run API and lifetime tests**

```powershell
.venv\Scripts\python.exe -m pytest backend/tests/api/test_macbert.py backend/tests/api/test_model_lifetime.py backend/tests/jobs -q
```

Expected: API error contracts, queue behavior, and single-instance assertions pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/src/typofix_cn/config.py backend/src/typofix_cn/api/app.py backend/tests/api/test_macbert.py backend/tests/api/test_model_lifetime.py
git commit -m "perf: share one MacBERT model instance"
```

### Task 4: Backport source syntax needed by Python 3.8

**Files:**
- Modify: every file reported by `rg -n '\\| None|\\| [A-Za-z_]|zip\\([^\\n]*strict=' backend/src cli/src`
- Create: `backend/tests/test_python38_syntax.py`

- [ ] **Step 1: Add the syntax gate**

The test must enumerate `backend/src` and `cli/src`, call `py_compile.compile()` for every `.py` file with the Win7 interpreter, and fail on Python 3.8 syntax errors.

- [ ] **Step 2: Replace PEP 604 annotations**

Replace `T | None` and other union annotations with `Optional[T]`/`Union[...]` and import the required names from `typing`. Preserve runtime types and Pydantic field constraints.

- [ ] **Step 3: Replace strict zip calls**

For every `zip(..., strict=True)`, add an explicit length assertion where the inputs are sized lists, then use ordinary `zip`. Keep the existing error behavior for mismatched input lengths.

- [ ] **Step 4: Run the syntax gate and current suite**

```powershell
packaging\win7\.venv-win7\Scripts\python.exe -m pytest backend/tests/test_python38_syntax.py -q
.venv\Scripts\python.exe -m pytest backend/tests cli/tests -m "not model" -q
```

Expected: Python 3.8 compilation succeeds and the current development suite remains green.

- [ ] **Step 5: Commit**

```powershell
git add backend/src cli/src backend/tests/test_python38_syntax.py
git commit -m "compat: support Python 3.8 syntax"
```

### Task 5: Add the frozen Win7 launcher and PyInstaller spec

**Files:**
- Create: `packaging/win7/launcher.py`
- Create: `packaging/win7/typofix_win7.spec`
- Modify: `backend/src/typofix_cn/api/app.py`
- Modify: `backend/tests/api/test_frontend.py`

- [ ] **Step 1: Write launcher path tests**

Test that a frozen-style root resolves `data`, `frontend/dist`, and `logs` beside `sys.executable`, not beside the source module. Test that the launcher never calls `snapshot_download`.

- [ ] **Step 2: Implement the launcher**

The launcher must build `Settings(data_dir=exe_root / "data", frontend_dir=exe_root / "frontend" / "dist", model_backend="onnx")`, configure file logging under `logs/typofix.log`, start `uvicorn` on `127.0.0.1:8000`, and open the default browser after the server starts. It must not use reload mode or network download code.

- [ ] **Step 3: Make frontend fallback frozen-safe**

Keep the existing `frontend_dir` override as the authoritative path. Add tests for a packaged frontend directory containing `index.html` and `/assets` so the API and static fallback continue to work.

- [ ] **Step 4: Write the onedir spec**

The spec must set `pathex` to `backend/src` and `cli/src`, collect `frontend/dist`, the ONNX model files (`model.onnx`, `tokenizer.json`, `config.json`, `tokenizer_config.json`, `special_tokens_map.json`, `vocab.txt`), and exclude `torch`, `transformers`, `pycorrector`, `huggingface_hub`, and CUDA DLLs. Use `COLLECT`/onedir output and do not embed mutable `data/jobs`.

- [ ] **Step 5: Run the launcher tests**

```powershell
.venv\Scripts\python.exe -m pytest backend/tests/api/test_frontend.py packaging/win7/test_launcher.py -q
```

Expected: source-mode frontend behavior and frozen-root path tests pass.

- [ ] **Step 6: Commit**

```powershell
git add packaging/win7/launcher.py packaging/win7/typofix_win7.spec backend/src/typofix_cn/api/app.py backend/tests/api/test_frontend.py packaging/win7/test_launcher.py
git commit -m "build: add offline Windows 7 launcher"
```

### Task 6: Add model parity and release verification

**Files:**
- Create: `packaging/win7/verify_model_parity.py`
- Create: `packaging/win7/sample_inputs/parity_cases.json`
- Create: `packaging/win7/test_release.ps1`
- Modify: `README.md`

- [ ] **Step 1: Create representative parity cases**

Include plain Han text, mixed numbers/Latin text, a known confusion rule, a threshold-boundary case, and a long text that crosses a chunk overlap.

- [ ] **Step 2: Implement PyTorch-versus-ONNX comparison**

On the development environment, run both backends against the JSON cases and compare accepted decision spans, source/suggestion pairs, and confusion precedence. Print a non-zero exit code for a systematic mismatch; allow only explicitly recorded floating-point score differences.

- [ ] **Step 3: Implement release smoke test**

`test_release.ps1` must verify the expected files, calculate the release size, launch the EXE, poll `/api/v1/health`, upload a sample DOCX, poll the job until completed, and verify both report files. It must support a `-Offline` switch that blocks download commands and fails if the log contains a Hugging Face URL.

- [ ] **Step 4: Run all regression tests and parity**

```powershell
.venv\Scripts\python.exe -m pytest backend/tests cli/tests -m "not model" -q
.venv\Scripts\python.exe packaging\win7\verify_model_parity.py
```

Expected: all existing tests pass and the parity script reports no systematic correction mismatch.

- [ ] **Step 5: Commit**

```powershell
git add packaging/win7/verify_model_parity.py packaging/win7/sample_inputs/parity_cases.json packaging/win7/test_release.ps1 README.md
git commit -m "test: verify offline ONNX release"
```

### Task 7: Build and validate on Windows 7 SP1

**Files:**
- Generated: `packaging/win7/dist/TypofixCN/`
- Generated: `packaging/win7/dist/TypofixCN-win7-fp32.zip`

- [ ] **Step 1: Build on Windows 7 SP1 x64**

Install Python 3.8.10 x64 and the pinned build dependencies in the VM, build the Vite frontend on the Windows 11 build machine, copy only the selected frontend and ONNX assets, and run `packaging\win7\build.ps1` in the Win7 VM.

- [ ] **Step 2: Verify the clean offline VM**

Disconnect the VM network, extract the ZIP, run `TypofixCN.exe`, open the local page, submit the sample DOCX, and inspect the JSON/HTML reports. Run two consecutive jobs and record peak working-set memory.

- [ ] **Step 3: Record release manifest**

Write the Python, PyInstaller, ONNX Runtime, tokenizer, model SHA-256, release size, and Win7 smoke-test result into `packaging/win7/RELEASE-MANIFEST.txt`.

- [ ] **Step 4: Commit release instructions only**

Do not commit the generated executable, model, ZIP, or mutable `data/jobs`. Commit only the reproducible build instructions and release manifest template:

```powershell
git add packaging/win7/RELEASE-MANIFEST.txt packaging/win7/README-Windows7.txt
git commit -m "docs: record Win7 release procedure"
```

## Plan self-review

- The design's ONNX boundary is covered by Task 2.
- Shared model lifetime and 4 GB memory behavior are covered by Task 3.
- Python 3.8 compatibility is covered by Task 4.
- Frozen paths, offline data, and frontend assets are covered by Task 5.
- Accuracy parity and clean offline acceptance are covered by Tasks 6 and 7.
- No task deletes existing model files or changes the current report contract.
- Every step has a concrete file, command, expected result, and verification boundary.

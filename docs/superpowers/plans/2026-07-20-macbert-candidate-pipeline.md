# MacBERT Candidate Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a project-owned MacBERT candidate/detection/selection pipeline that improves Chinese typo recall with offset-safe mixed-text inference, editable confusion rules, Top-5 logits, and diagnostics, while preserving the existing DOCX workflow and response fields.

**Architecture:** Keep `pycorrector` as the model loader and source of model/tokenizer weights. Add a fast-tokenizer candidate adapter, a reloadable UTF-8 confusion repository, and pure selection logic in the application. `MacBertCorrector.correct_raw()` composes those pieces and returns the existing `source/target/errors` plus test-only `decisions`; `correct()` converts only accepted errors into the existing DOCX `CorrectionResult`. If the loaded backend cannot provide fast offsets/model logits, use the current `correct_batch()` Chinese-span adapter. Inference exceptions are surfaced as model errors.

**Tech Stack:** Python 3.11, Pydantic v2, FastAPI, PyTorch/Transformers through `pycorrector`, pytest, React/TypeScript, Vitest.

---

## 1. Establish isolated baseline

- [x] Verify the new worktree is on `codex/macbert-candidate-pipeline` and that the parent worktree’s `.idea/` and `package-lock.json` remain untouched.
- [x] Install/sync the backend development and model extras in the worktree, and install frontend dependencies if the lockfile is absent.
- [x] Run the current backend non-model suite and frontend tests, recording the baseline before edits.

Commands:

```powershell
uv sync --extra dev --extra model
.venv\Scripts\python.exe -m pytest -m "not model" -q
Set-Location frontend
npm install
npx vitest run
```

## 2. Add confusion-rule repository and configuration (TDD)

Files:

- `backend/src/typofix_cn/correctors/confusions.py` (new)
- `backend/src/typofix_cn/config.py`
- `backend/tests/correctors/test_confusions.py` (new)
- `backend/tests/test_config.py`

- [x] Write tests for UTF-8 parsing, comments/blank lines, whitespace around `=>`, Han-only/equal-length validation, duplicate collapse, conflicting duplicate errors with line numbers, longest-match precedence, and reload after file mtime/content changes.
- [x] Add `Settings.confusions_dir`/`confusions_path` under the configured data directory and ensure directory/file initialization creates `default.txt` with `新资 => 薪资` only when absent. Do not change model or DOCX paths.
- [x] Implement a small repository that reads on each `snapshot()`/`match()` call, validates every line, preserves file order, reports actionable `ValueError` messages, and exposes non-overlapping longest matches over the original text.
- [x] Keep confusion rules separate from the existing terminology repository and matcher; they are model-test detector inputs, not auto-edit rules for DOCX.

## 3. Implement offset-safe MacBERT candidate provider (TDD)

Files:

- `backend/src/typofix_cn/correctors/macbert_candidates.py` (new)
- `backend/src/typofix_cn/documents/chunking.py` (only if a small reusable helper is needed)
- `backend/tests/correctors/test_macbert_candidates.py` (new)

- [x] Create typed candidate records carrying absolute `start/end`, original Han character, candidate text, original probability, candidate probability, and Top-5 candidate list.
- [x] Add a provider that tokenizes complete text with `return_offsets_mapping=True` and special-token masks, forwards only model-supported tensors, computes softmax on logits, and keeps Top-5 non-original candidates.
- [x] Require both source and decoded candidate to be exactly one Han character and require a one-codepoint offset; ignore numeric, Latin, punctuation, whitespace, WordPiece fragments, and multi-character tokens as editable positions while retaining their context.
- [x] For text longer than 120 characters, call the existing `chunk_sentence(text, max_chars=120, overlap=16)`, translate window offsets back to full-text offsets, and de-duplicate overlap candidates by highest candidate score.
- [x] Expose a capability check for a fast tokenizer, model, and logits. If unavailable, return a typed fallback signal; do not catch and downgrade actual tokenizer/model forward exceptions.
- [x] Use fakes in unit tests to cover mixed offsets, multi-token numeric context, Top-2 selection data, long-window offset merging, overlap de-duplication, and capability fallback without loading the real model.

## 4. Implement detector, selector, and diagnostic schema (TDD)

Files:

- `backend/src/typofix_cn/correctors/macbert_decisions.py` (new)
- `backend/src/typofix_cn/correctors/base.py` (only additive response types if needed)
- `backend/tests/correctors/test_macbert_decisions.py` (new)

- [x] Define `detection_score = 1 - original_score`, defaults `detection_threshold=0.50` and `correction_threshold=0.30`, and typed decision/candidate payloads suitable for JSON serialization.
- [x] Apply exact confusion matches first, using longest source match and file order for equal lengths; mark them `provider="confusion"`, `reason="confusion_exact_match"`, and accepted regardless of thresholds.
- [x] For model candidates, choose the highest-scoring non-original candidate, require detection threshold first and correction threshold second, and preserve rejected diagnostics with `detection_below_threshold` or `correction_below_threshold`.
- [x] Keep only model decisions whose best non-original candidate reaches the diagnostic floor (`0.05`), emit `null` for unavailable scores, and prevent model decisions overlapping an accepted confusion range.
- [x] Ensure accepted decisions merge into `target` without changing non-Chinese text and generate existing `(original, suggestion, start)` error tuples at full-text offsets.

## 5. Integrate the pipeline without changing DOCX contracts (TDD)

Files:

- `backend/src/typofix_cn/correctors/macbert.py`
- `backend/src/typofix_cn/application/analyze.py` (only if an additive adapter hook is required)
- `backend/tests/correctors/test_macbert.py`
- `backend/tests/correctors/test_macbert_adapter.py`
- `backend/tests/correctors/test_macbert_smoke.py`

- [x] Refactor `MacBertCorrector` to lazily load the existing backend once, construct the confusion repository from `Settings`/model data root, and compose provider plus detector/selector for `correct_raw()`.
- [x] Change the raw test method to accept the two thresholds and return `source`, `target`, `errors`, and `decisions`; preserve tuple shape and global offsets.
- [x] Keep `correct()` on the old `CorrectionResult`/`CorrectionFinding` contract. It should use approved decisions with default thresholds and never expose `decisions` to DOCX report schemas.
- [x] Implement capability fallback through the existing `correct_batch()` path with `provider="model"`, `reason="backend_fallback"`, and null scores. Raise `ModelInferenceError` for real inference failures.
- [x] Add regression tests for existing loader caching, Chinese-span fallback, non-Chinese bypass, DOCX global offsets, confusion precedence, threshold behavior, and exact mixed sentence recall.

## 6. Synchronize API and homepage controls (TDD)

Files:

- `backend/src/typofix_cn/api/app.py`
- `backend/tests/api/test_macbert.py`
- `frontend/src/types.ts`
- `frontend/src/api/client.ts`
- `frontend/src/pages/CheckPage.tsx`
- `frontend/src/styles.css`
- `frontend/tests/CheckPage.test.tsx`

- [x] Replace the single MacBERT test request threshold with validated `detection_threshold` and `correction_threshold` fields (0.0–1.0), forwarding both to `correct_raw()`.
- [x] Preserve the upload-file/upload-folder controls, job creation payloads, term-library behavior, and all DOCX endpoints unchanged.
- [x] Replace the single homepage slider with two compact labeled sliders using defaults 0.50 and 0.30; render the complete raw JSON including `decisions` and retain loading/error states.
- [x] Update TypeScript types and tests to assert request body, defaults, threshold validation, diagnostics rendering, and continued DOCX entry presence.
- [x] Map confusion configuration errors to a clear API error response without exposing local Python stacks or paths in the browser.

## 7. Verification and acceptance

- [x] Run the full backend suite excluding only explicitly model-marked tests, then run model smoke tests with the local MacBERT weights.
- [x] Run frontend Vitest, lint, and production build.
- [x] Exercise the real endpoint with Unicode-safe input `2023年学员平均就业新资18K/月（高于行业均值32%）`; verify `target` contains `薪资`, error start is 11, and diagnostics identify the accepted candidate. Verify clean controls remain unchanged.
- [x] Confirm DOCX upload entry and job/report APIs still pass their regression tests; do not change report JSON/HTML schemas or history records.
- [x] Review the diff for accidental changes outside the agreed files, update the plan checkboxes, and commit the implementation in the isolated branch.

## 8. Handoff

- [ ] Report test/build results and the exact branch/commit. Offer the user the existing local merge or PR/branch handoff options; do not merge until explicitly selected.

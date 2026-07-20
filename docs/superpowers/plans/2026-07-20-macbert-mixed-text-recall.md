# MacBERT Mixed-Text Recall Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct Chinese typos inside text that also contains digits, Latin letters, or punctuation, while adding an adjustable inference threshold to the homepage model test.

**Architecture:** `MacBertCorrector.correct_raw()` will isolate contiguous Chinese spans, send all spans through one backend batch, and merge corrected text and error offsets into the original mixed text. The API will validate and forward an optional threshold, and the React test panel will expose that threshold without changing the DOCX job request or its default model behavior.

**Tech Stack:** Python 3.12, pycorrector MacBERT, FastAPI/Pydantic, pytest, React 19, TypeScript, Vitest, Testing Library

---

### Task 1: Correct mixed Chinese text and preserve global offsets

**Files:**
- Modify: `backend/tests/correctors/test_macbert.py`
- Modify: `backend/tests/correctors/test_macbert_adapter.py`
- Modify: `backend/src/typofix_cn/correctors/macbert.py:1-75`

- [ ] **Step 1: Write failing corrector tests**

Replace the stubs so they accept the backend threshold argument, then add explicit coverage for mixed text, global offsets, threshold forwarding, and non-Chinese passthrough:

```python
class StubBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], float]] = []

    def correct_batch(self, texts, *, threshold=0.7):
        self.calls.append((list(texts), threshold))
        results = []
        for text in texts:
            if "新资" in text:
                results.append({"source": text, "target": text.replace("新资", "薪资"), "errors": [("新", "薪", text.index("新"))]})
            elif "新" in text:
                results.append({"source": text, "target": text.replace("新", "心"), "errors": [("新", "心", text.index("新"))]})
            else:
                results.append({"source": text, "target": text, "errors": []})
        return results


def test_macbert_corrects_chinese_spans_in_mixed_text(tmp_path) -> None:
    backend = StubBackend()
    corrector = MacBertCorrector(tmp_path, loader=lambda _: backend)
    source = "2023年学员平均就业新资18K/月（高于行业均值32%）"

    result = corrector.correct_raw([source], threshold=0.35)

    assert backend.calls == [(["年学员平均就业新资", "月", "高于行业均值"], 0.35)]
    assert result == [{
        "source": source,
        "target": "2023年学员平均就业薪资18K/月（高于行业均值32%）",
        "errors": [("新", "薪", 11)],
    }]


def test_macbert_does_not_load_backend_for_non_chinese_text(tmp_path) -> None:
    loader = Mock()
    corrector = MacBertCorrector(tmp_path, loader=loader)

    result = corrector.correct_raw(["2023 / MacBERT 18K"])

    assert result == [{"source": "2023 / MacBERT 18K", "target": "2023 / MacBERT 18K", "errors": []}]
    loader.assert_not_called()
```

In `backend/tests/correctors/test_macbert_adapter.py`, change the stub signature to:

```python
def correct_batch(self, texts, *, threshold=0.7):
```

- [ ] **Step 2: Run the focused tests and verify the new behavior fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/correctors/test_macbert.py backend/tests/correctors/test_macbert_adapter.py -q
```

Expected: FAIL because `correct_raw()` does not accept `threshold` and still sends the complete mixed string to the backend.

- [ ] **Step 3: Implement Chinese-span batching and result merging**

Update `backend/src/typofix_cn/correctors/macbert.py` with a compiled Chinese-span expression, threshold forwarding, stable passthrough results, and global error offsets:

```python
import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .base import CorrectionFinding, CorrectionInput, CorrectionResult


_CHINESE_SPAN_PATTERN = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF]+")


class MacBertCorrector:
    # Keep __init__, _ensure_backend, correct, and _convert unchanged.

    def correct_raw(self, texts: Sequence[str], *, threshold: float = 0.7) -> list[dict[str, Any]]:
        if not texts:
            return []

        results = [{"source": text, "target": text, "errors": []} for text in texts]
        spans: list[tuple[int, int, str]] = []
        for text_index, source in enumerate(texts):
            spans.extend((text_index, match.start(), match.group()) for match in _CHINESE_SPAN_PATTERN.finditer(source))
        if not spans:
            return results

        backend = self._ensure_backend()
        try:
            corrected_spans = list(
                backend.correct_batch([span_text for _, _, span_text in spans], threshold=threshold)
            )
            if len(corrected_spans) != len(spans):
                raise ValueError("MacBERT 返回数量与输入片段数量不一致")
        except Exception as exc:
            raise ModelInferenceError("MacBERT 推理失败，请查看服务端日志") from exc

        targets = [list(text) for text in texts]
        merged_errors: list[list[tuple[Any, Any, int]]] = [[] for _ in texts]
        for (text_index, span_start, source_span), raw in zip(spans, corrected_spans, strict=True):
            target_span = raw.get("target", source_span)
            if not isinstance(target_span, str) or len(target_span) != len(source_span):
                continue
            targets[text_index][span_start : span_start + len(source_span)] = target_span
            for error in raw.get("errors", []):
                if not isinstance(error, (list, tuple)) or len(error) != 3:
                    continue
                original, suggestion, local_start = error
                if not isinstance(local_start, int):
                    continue
                if not isinstance(original, str) or source_span[local_start : local_start + len(original)] != original:
                    continue
                merged_errors[text_index].append((original, suggestion, span_start + local_start))

        for index, result in enumerate(results):
            result["target"] = "".join(targets[index])
            result["errors"] = merged_errors[index]
        return results
```

Do not add a new threshold argument to `correct()`: the DOCX path continues to call `correct_raw()` with its default `0.7`.

- [ ] **Step 4: Run focused corrector tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/correctors/test_macbert.py backend/tests/correctors/test_macbert_adapter.py -q
```

Expected: all tests PASS.

- [ ] **Step 5: Commit the corrector change**

```powershell
git add backend/tests/correctors/test_macbert.py backend/tests/correctors/test_macbert_adapter.py backend/src/typofix_cn/correctors/macbert.py
git commit -m "fix: correct MacBERT Chinese spans in mixed text"
```

### Task 2: Validate and forward the model-test threshold

**Files:**
- Modify: `backend/tests/api/test_macbert.py`
- Modify: `backend/src/typofix_cn/api/app.py:12-30,98-105`

- [ ] **Step 1: Write failing API threshold tests**

Make the stub record calls and assert that a custom threshold is forwarded:

```python
class StubRawCorrector:
    def __init__(self) -> None:
        self.calls = []

    def correct_raw(self, texts, *, threshold=0.7):
        self.calls.append((list(texts), threshold))
        return [{"source": texts[0], "target": "今天心情很好", "errors": [["新", "心", 2]]}]


def test_macbert_text_test_forwards_threshold(monkeypatch, tmp_path) -> None:
    corrector = StubRawCorrector()
    monkeypatch.setattr("typofix_cn.api.app.MacBertCorrector", lambda _: corrector)

    with TestClient(create_app(Settings(data_dir=tmp_path / "data"))) as client:
        response = client.post(
            "/api/v1/macbert/test",
            json={"text": "今天新情很好", "threshold": 0.35},
        )

    assert response.status_code == 200
    assert corrector.calls == [(["今天新情很好"], 0.35)]


def test_macbert_text_test_rejects_threshold_outside_range(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("typofix_cn.api.app.MacBertCorrector", lambda _: StubRawCorrector())

    with TestClient(create_app(Settings(data_dir=tmp_path / "data"))) as client:
        response = client.post(
            "/api/v1/macbert/test",
            json={"text": "今天新情很好", "threshold": 1.1},
        )

    assert response.status_code == 422
```

Keep the existing response and blank-text tests. Update the existing test setup to retain its local `StubRawCorrector` instance where required.

- [ ] **Step 2: Run API tests and verify threshold coverage fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/api/test_macbert.py -q
```

Expected: FAIL because the request schema drops `threshold` and the endpoint calls `correct_raw()` without it.

- [ ] **Step 3: Add Pydantic validation and endpoint forwarding**

Change the Pydantic import and request model in `backend/src/typofix_cn/api/app.py`:

```python
from pydantic import BaseModel, Field


class MacBertTestRequest(BaseModel):
    text: str
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)
```

Forward the value in the route:

```python
return macbert_tester.correct_raw([payload.text], threshold=payload.threshold)[0]
```

- [ ] **Step 4: Run API and full non-model backend tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/api/test_macbert.py -q
.\.venv\Scripts\python.exe -m pytest -m "not model" -q
```

Expected: API tests PASS; full backend result is at least the 61-test clean baseline plus the new tests, with the model smoke test deselected.

- [ ] **Step 5: Commit the API change**

```powershell
git add backend/tests/api/test_macbert.py backend/src/typofix_cn/api/app.py
git commit -m "feat: expose MacBERT test threshold"
```

### Task 3: Add threshold control to the homepage model test

**Files:**
- Modify: `frontend/src/api/client.ts:18-24`
- Modify: `frontend/src/pages/CheckPage.tsx:8-74`
- Modify: `frontend/src/styles.css:65-84,217-219`
- Modify: `frontend/tests/CheckPage.test.tsx:1-70`

- [ ] **Step 1: Write a failing UI request test**

Import `fireEvent`, capture the model-test request, adjust the slider, and assert both the request body and retained DOCX entry:

```tsx
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

it("tests plain text with an adjustable MacBERT threshold and keeps the DOCX entry", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/term-libraries")) {
      return new Response(JSON.stringify([]), { status: 200 });
    }
    return new Response(JSON.stringify({
      source: "今天新情很好",
      target: "今天心情很好",
      errors: [["新", "心", 2]],
    }), { status: 200 });
  });
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  render(<CheckPage />);
  await user.type(screen.getByLabelText("测试文本"), "今天新情很好");
  fireEvent.change(screen.getByLabelText("置信度阈值"), { target: { value: "0.35" } });
  await user.click(screen.getByRole("button", { name: "测试模型" }));

  expect(await screen.findByText(/今天心情很好/)).toBeInTheDocument();
  expect(screen.getByText("0.35")).toBeInTheDocument();
  const modelRequest = fetchMock.mock.calls.find(([input]) => String(input).endsWith("/macbert/test"));
  expect(JSON.parse(String(modelRequest?.[1]?.body))).toEqual({ text: "今天新情很好", threshold: 0.35 });
  expect(screen.getByText("上传文件")).toBeInTheDocument();
  expect(screen.queryByText("把论文里的小毛刺，留在交稿前。")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run the focused frontend test and verify it fails**

Run:

```powershell
npm test -- --run tests/CheckPage.test.tsx
```

Expected: FAIL because there is no `置信度阈值` control and the client only sends `{ text }`.

- [ ] **Step 3: Send the threshold from the API client**

Update `frontend/src/api/client.ts`:

```typescript
export function testMacBert(text: string, threshold: number): Promise<MacBertRawResult> {
  return request<MacBertRawResult>("/macbert/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, threshold }),
  });
}
```

- [ ] **Step 4: Add the controlled threshold slider**

In `CheckPage`, add state alongside the existing test state:

```tsx
const [testThreshold, setTestThreshold] = useState(0.7);
```

Call the API with the state value:

```tsx
setTestResult(await testMacBert(testText, testThreshold));
```

Place this control between the textarea and button:

```tsx
<label className="model-test-threshold">
  <span>置信度阈值</span>
  <input
    type="range"
    min="0"
    max="1"
    step="0.05"
    value={testThreshold}
    onChange={(event) => setTestThreshold(Number(event.target.value))}
  />
  <output>{testThreshold.toFixed(2)}</output>
</label>
```

- [ ] **Step 5: Style the threshold control without enlarging the hero**

Add compact grid styles near the existing model-test rules in `frontend/src/styles.css`:

```css
.model-test-threshold {
  display: grid;
  grid-template-columns: auto minmax(110px, 1fr) 3ch;
  align-items: center;
  gap: 10px;
  align-self: end;
  color: var(--muted);
  font-size: .78rem;
  font-weight: 650;
}
.model-test-threshold input { width: 100%; accent-color: var(--accent); }
.model-test-threshold output { color: var(--ink); font-variant-numeric: tabular-nums; }
```

Change `.model-test-panel` to accommodate the text area, slider, and button on wide screens while preserving the existing single-column mobile rule:

```css
.model-test-panel {
  grid-template-columns: minmax(0, 1fr) minmax(210px, .35fr) auto;
}
```

- [ ] **Step 6: Run frontend tests, type checking, and production build**

Run:

```powershell
npm test -- --run
npm run lint
npm run build
```

Expected: 5 or more tests PASS; TypeScript exits 0; Vite creates `frontend/dist` successfully.

- [ ] **Step 7: Commit the frontend change**

```powershell
git add frontend/src/api/client.ts frontend/src/pages/CheckPage.tsx frontend/src/styles.css frontend/tests/CheckPage.test.tsx
git commit -m "feat: adjust MacBERT test threshold"
```

### Task 4: Verify the regression and the real model result

**Files:**
- Modify only if verification reveals a defect in files already listed above.

- [ ] **Step 1: Run the complete automated verification suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not model" -q
npm test -- --run
npm run lint
npm run build
git diff --check
```

Expected: all automated checks PASS and `git diff --check` produces no output.

- [ ] **Step 2: Ensure the model dependencies are available**

Run:

```powershell
uv sync --extra dev --extra model
```

Expected: pycorrector, PyTorch, Transformers, and the project package are installed in the worktree environment without changing application code.

- [ ] **Step 3: Test the exact mixed sentence with the local model**

Run:

```powershell
@'
from typofix_cn.config import Settings
from typofix_cn.correctors.macbert import MacBertCorrector

source = "2023年学员平均就业新资18K/月（高于行业均值32%）"
model_path = Settings().models_dir / "macbert4csc-base-chinese"
result = MacBertCorrector(model_path).correct_raw([source])[0]
print(result)
assert "薪资" in result["target"]
assert any(error[0] == "新" and error[1] == "薪" and error[2] == 11 for error in result["errors"])
'@ | .\.venv\Scripts\python.exe -
```

Expected: output target contains `2023年学员平均就业薪资18K/月（高于行业均值32%）`, and the assertion confirms the global error start is `11`.

- [ ] **Step 4: Inspect the final change set**

Run:

```powershell
git status --short
git diff master...HEAD --stat
git log --oneline --decorate -5
```

Expected: only the planned backend, frontend, tests, and documentation changes are present; generated environments, `node_modules`, and `frontend/dist` remain ignored.

- [ ] **Step 5: Follow the development-branch completion workflow**

Use `superpowers:finishing-a-development-branch` to present the tested branch for merge, pull request, retention, or cleanup. Do not merge or delete the branch without the user's selection.

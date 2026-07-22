# MacBERT 纯文本效果测试入口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用紧凑的 MacBERT 纯文本测试区替换首页大标题，直接展示模型原始 JSON，同时完整保留现有 DOCX 校验流程。

**Architecture:** `MacBertCorrector` 新增复用现有延迟加载和异常边界的原始批量推理方法；FastAPI 新增单文本测试端点并持有专用的应用级 corrector；React 首页在原 hero 位置提交文本并格式化显示原始响应。DOCX 任务端点、队列、分析和报告结构不变。

**Tech Stack:** Python 3.11、FastAPI、pytest、React 19、TypeScript、Vitest、Testing Library、CSS

---

### Task 1: 暴露 MacBERT 原始批量结果

**Files:**
- Modify: `backend/src/typofix_cn/correctors/macbert.py`
- Test: `backend/tests/correctors/test_macbert.py`

- [ ] **Step 1: 写入失败测试**

在 `backend/tests/correctors/test_macbert.py` 增加：

```python
def test_macbert_returns_backend_output_without_conversion(tmp_path) -> None:
    corrector = MacBertCorrector(tmp_path, loader=lambda _: StubBackend())

    result = corrector.correct_raw(["今天新情很好"])

    assert result == [
        {
            "source": "今天新情很好",
            "target": "今天心情很好",
            "errors": [("新", "心", 2)],
        }
    ]
```

- [ ] **Step 2: 运行测试并确认因方法不存在而失败**

Run: `uv run --no-sync pytest backend/tests/correctors/test_macbert.py::test_macbert_returns_backend_output_without_conversion -v`

Expected: FAIL，错误包含 `AttributeError: 'MacBertCorrector' object has no attribute 'correct_raw'`。

- [ ] **Step 3: 实现最小原始推理入口并让现有转换复用它**

在 `MacBertCorrector` 中加入：

```python
def correct_raw(self, texts: Sequence[str]) -> list[dict[str, Any]]:
    if not texts:
        return []
    backend = self._ensure_backend()
    try:
        return list(backend.correct_batch(list(texts)))
    except Exception as exc:
        raise ModelInferenceError("MacBERT 推理失败，请查看服务端日志") from exc
```

把 `correct()` 中直接访问 backend 的部分替换为：

```python
def correct(self, inputs: Sequence[CorrectionInput]) -> list[CorrectionResult]:
    batches = self.correct_raw([item.text for item in inputs])
    return [self._convert(item, raw) for item, raw in zip(inputs, batches, strict=True)]
```

保留当前工作区已有的空字符串和不等长 finding 过滤逻辑。

- [ ] **Step 4: 运行 corrector 测试**

Run: `uv run --no-sync pytest backend/tests/correctors/test_macbert.py backend/tests/correctors/test_macbert_adapter.py -v`

Expected: 全部 PASS；`correct_raw()` 返回原始字典，`correct()` 仍返回 `CorrectionResult`。

### Task 2: 增加纯文本测试 API

**Files:**
- Modify: `backend/src/typofix_cn/api/app.py`
- Create: `backend/tests/api/test_macbert.py`

- [ ] **Step 1: 写成功响应和空文本失败测试**

创建 `backend/tests/api/test_macbert.py`：

```python
from fastapi.testclient import TestClient

from typofix_cn.api.app import create_app
from typofix_cn.config import Settings


class StubRawCorrector:
    def correct_raw(self, texts):
        return [{"source": texts[0], "target": "今天心情很好", "errors": [["新", "心", 2]]}]


def test_macbert_text_test_returns_raw_model_output(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("typofix_cn.api.app.MacBertCorrector", lambda _: StubRawCorrector())

    with TestClient(create_app(Settings(data_dir=tmp_path / "data"))) as client:
        response = client.post("/api/v1/macbert/test", json={"text": "今天新情很好"})

    assert response.status_code == 200
    assert response.json() == {
        "source": "今天新情很好",
        "target": "今天心情很好",
        "errors": [["新", "心", 2]],
    }


def test_macbert_text_test_rejects_blank_text(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("typofix_cn.api.app.MacBertCorrector", lambda _: StubRawCorrector())

    with TestClient(create_app(Settings(data_dir=tmp_path / "data"))) as client:
        response = client.post("/api/v1/macbert/test", json={"text": "   "})

    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "请输入要测试的文本"
```

- [ ] **Step 2: 运行 API 测试并确认端点不存在**

Run: `uv run --no-sync pytest backend/tests/api/test_macbert.py -v`

Expected: FAIL，成功用例返回 404。

- [ ] **Step 3: 实现请求模型和端点**

在 `backend/src/typofix_cn/api/app.py` 导入 `Any`、`BaseModel`，以及 `ModelDependencyMissing`、`ModelInferenceError`、`ModelNotReady`。定义：

```python
class MacBertTestRequest(BaseModel):
    text: str
```

在 `create_app()` 内创建一个专用于交互测试且延迟加载的实例：

```python
macbert_tester = MacBertCorrector(settings.models_dir / "macbert4csc-base-chinese")
```

在通配前端路由之前增加：

```python
@app.post("/api/v1/macbert/test")
def test_macbert(payload: MacBertTestRequest) -> dict[str, Any]:
    if not payload.text.strip():
        raise HTTPException(status_code=422, detail={"code": "EMPTY_TEXT", "message": "请输入要测试的文本"})
    try:
        return macbert_tester.correct_raw([payload.text])[0]
    except (ModelDependencyMissing, ModelNotReady, ModelInferenceError) as exc:
        raise HTTPException(status_code=503, detail={"code": "MODEL_UNAVAILABLE", "message": str(exc)}) from exc
```

不要修改 `run_job()` 中现有 corrector 的创建和 DOCX 分析逻辑。

- [ ] **Step 4: 运行 API 回归测试**

Run: `uv run --no-sync pytest backend/tests/api/test_macbert.py backend/tests/api/test_jobs.py -v`

Expected: 全部 PASS。

### Task 3: 在首页顶部增加紧凑测试区

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/CheckPage.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/tests/CheckPage.test.tsx`

- [ ] **Step 1: 写入首页交互失败测试**

在 `frontend/tests/CheckPage.test.tsx` 增加独立测试；mock 对 `/term-libraries` 返回空数组，对 `/macbert/test` 返回原始结果：

```tsx
it("tests plain text with MacBERT and keeps the DOCX entry", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
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
  await user.click(screen.getByRole("button", { name: "测试模型" }));

  expect(await screen.findByText(/今天心情很好/)).toBeInTheDocument();
  expect(screen.getByText("上传文件")).toBeInTheDocument();
  expect(screen.queryByText("把论文里的小毛刺，留在交稿前。")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: 运行测试并确认因测试入口不存在而失败**

Run: `npm test -- --run tests/CheckPage.test.tsx`

Workdir: `frontend`

Expected: FAIL，找不到标签“测试文本”。

- [ ] **Step 3: 增加客户端类型和调用**

在 `frontend/src/types.ts` 增加：

```typescript
export interface MacBertRawResult {
  source: string;
  target: string;
  errors: unknown[];
  [key: string]: unknown;
}
```

在 `frontend/src/api/client.ts` 导入该类型并增加：

```typescript
export function testMacBert(text: string): Promise<MacBertRawResult> {
  return request<MacBertRawResult>("/macbert/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}
```

- [ ] **Step 4: 实现首页状态和标记**

在 `CheckPage` 中新增 `testText`、`testResult`、`testLoading`、`testError` 状态和异步提交函数。保留所有现有 DOCX 状态、effects 和 `startCheck()`。将旧 `h1` 和 `hero-copy` 替换为：

```tsx
<div className="model-test-panel">
  <div className="model-test-heading">
    <div>
      <p className="eyebrow">MacBERT</p>
      <h1>效果测试</h1>
    </div>
    <span className="quiet-label">原始模型输出</span>
  </div>
  <label className="model-test-input">
    <span>测试文本</span>
    <textarea value={testText} onChange={(event) => setTestText(event.target.value)} />
  </label>
  <button className="primary-button model-test-button" disabled={!testText.trim() || testLoading} onClick={runModelTest}>
    {testLoading ? "测试中…" : "测试模型"}
  </button>
  {testError && <p className="error-copy" role="alert">{testError}</p>}
  {testResult && <pre className="model-test-result">{JSON.stringify(testResult, null, 2)}</pre>}
</div>
```

`runModelTest()` 调用 `testMacBert(testText)`，成功时覆盖旧结果，失败时清空结果并显示错误，最后恢复 loading。

- [ ] **Step 5: 增加紧凑样式且保留当前未提交视觉改版**

在现有 `frontend/src/styles.css` 的当前变量体系上增量加入 `.model-test-panel`、`.model-test-heading`、`.model-test-input`、`.model-test-button`、`.model-test-result` 样式；把 `textarea` 加入字体和 focus 选择器。测试区采用两列输入/结果布局，窄屏改为单列。不要回滚当前工作区已有的 Apple 风格变量、圆角和其他页面样式。

- [ ] **Step 6: 运行首页测试和前端静态校验**

Run: `npm test -- --run tests/CheckPage.test.tsx`

Run: `npm run lint`

Run: `npm run build`

Workdir: `frontend`

Expected: 所有命令退出码 0；现有 DOCX 测试和新模型测试均 PASS。

### Task 4: 完整回归验证

**Files:**
- Verify only

- [ ] **Step 1: 运行后端非模型测试**

Run: `uv run --no-sync pytest backend/tests -m "not model" -v`

Expected: 全部 PASS；不下载或加载真实模型。

- [ ] **Step 2: 运行完整前端测试**

Run: `npm test -- --run`

Workdir: `frontend`

Expected: 全部 PASS。

- [ ] **Step 3: 检查变更范围**

Run: `git -c safe.directory=C:/workspace/typofix-cn diff --check`

Expected: 无空白错误。确认 DOCX API、任务队列、分析服务和报告文件没有行为改动；保留实施前已存在的 `macbert.py` finding 过滤和 `styles.css` 视觉改版。

- [ ] **Step 4: 在可用模型环境做一次真实冒烟测试**

启动本地服务后，在首页输入“今天新情很好”，点击“测试模型”。确认页面显示模型原始 JSON，且下方仍可上传 DOCX。若本机当前没有模型依赖或权重，记录为未执行，不以伪造结果代替。

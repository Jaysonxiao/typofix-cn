# Typofix CN

Typofix CN 是一个本机优先的中文 DOCX 文档校验工具：同一套 Python 核心同时提供 CLI 和 FastAPI Web 界面。MVP 不使用 SQLite，任务报告和术语库都保存在可读的文件中。

## 0. 环境准备

项目使用 uv 管理 Python 版本、虚拟环境和锁定依赖，不需要手动执行 `python -m venv` 或 `pip install`。

先确认本机已安装：

```powershell
uv --version
node --version
npm --version
```

Python 版本由 `.python-version` 固定为 3.12，项目兼容 Python 3.11–3.12。没有 uv 时，Windows PowerShell 可执行：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS/Linux 可执行：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 1. 安装 Python 环境

### 仅规则模式

不下载 MacBERT，适合先验证 DOCX 读取、标点和版式规则：

```powershell
uv sync --extra dev
```

### 完整模型模式

完整模式需要模型依赖和本地权重：

```powershell
uv sync --extra model
uv run typofix model download --data-dir .\data
```

如果还要运行测试：

```powershell
uv sync --extra dev --extra model
```

模型下载只需执行一次。以后启动服务或 CLI 时，必须使用与下载时相同的 `--data-dir`；不传时统一使用系统用户数据目录。

## 2. 本地 CLI 模式

### 仅规则校验

```powershell
uv sync --extra dev
uv run typofix check .\test.docx --rules-only --data-dir .\data
```

### MacBERT 模型 + 规则校验

```powershell
uv sync --extra model
uv run typofix model download --data-dir .\data
uv run typofix check .\test.docx --term-lib default --data-dir .\data
```

也可以递归校验文件夹，并选择多个术语库：

```powershell
uv run typofix check .\论文目录 `
  --term-lib default `
  --term-lib computer-science `
  --data-dir .\data
```

CLI 会输出 JSON 和离线 HTML 报告路径。需要显示内部错误子类型时加 `--verbose`：

```powershell
uv run typofix check .\test.docx --rules-only --verbose --data-dir .\data
```

管理文本术语库：

```powershell
uv run typofix terms list --data-dir .\data
uv run typofix terms add default "项目专用术语" --data-dir .\data
```

## 3. 本地 Web 模式

### 构建前端并启动完整 Web

```powershell
cd frontend
npm install
npm run build
cd ..

uv sync --extra model
uv run typofix model download --data-dir .\data
uv run typofix serve --data-dir .\data
```

浏览器打开 <http://127.0.0.1:8000/>。默认页面使用“模型 + 规则”模式；如果没有安装模型依赖或权重，任务会失败，不会产生 MacBERT 错别字结果。

只想使用规则时，可以不安装 model extra，并在页面选择“仅规则”：

```powershell
uv sync --extra dev
uv run typofix serve --data-dir .\data
```

前端 `npm run dev` 目前只用于 UI 开发预览；端到端 API 流程请使用 `npm run build` 后由 `typofix serve` 托管 `frontend/dist`。

## 4. 数据目录和环境变量

默认数据目录由 `platformdirs` 决定，也可以用 `--data-dir` 或 `TYPOFIX_DATA_DIR` 覆盖：

```powershell
$env:TYPOFIX_DATA_DIR = (Resolve-Path .\data).Path
uv run typofix serve
```

Web、CLI 和模型下载必须使用同一个数据目录。典型结构：

```text
data/
  term-libraries/default.txt   # UTF-8，每行一个术语
  models/macbert4csc-base-chinese/
  jobs/<job-id>/input/
  jobs/<job-id>/manifest.json
  jobs/<job-id>/report.json
  jobs/<job-id>/report.html
```

术语库是普通文本文件，空行和 `#` 注释会忽略；可以直接编辑后重新执行任务。

## 5. 术语库使用

术语库就是普通 UTF-8 文本文件，每行一个术语；空行和 `#` 注释会忽略。修改后重新运行任务即可生效，Web 术语页也支持新增、移除和下载原始 `.txt` 文件。报告页中选中文字添加术语后，会重新匹配当前任务，但不会再次运行模型。

## 6. Python 包构建

构建 Python wheel 和源码包：

```powershell
uv build
```

产物会写入 `dist/`。本地安装 wheel：

```powershell
uv tool install .\dist\typofix_cn-0.1.0-py3-none-any.whl
typofix --help
```

当前 `uv build` 只打包 Python 核心和 CLI，不会把 `frontend/dist`、MacBERT 权重或 PyTorch 一起打进 wheel。需要 Web 时仍需先构建前端，再从源码目录执行 `uv run typofix serve`。

## 7. Windows/macOS 本地发布流程

每台机器第一次部署建议执行：

```powershell
uv sync --extra model
cd frontend
npm install
npm run build
cd ..
uv run typofix model download --data-dir .\data
uv run typofix serve --data-dir .\data
```

规则-only 的轻量部署可以省略 `--extra model` 和模型下载，并在 Web 页面选择“仅规则”。

## 8. 麒麟 ARM / 离线打包说明

当前仓库没有承诺一个跨 Windows、macOS、麒麟 ARM 的单文件安装包。规则模式只依赖通用 Python wheels，可以先执行：

```bash
uv sync --extra dev
uv run typofix check ./test.docx --rules-only --data-dir ./data
```

完整模型模式还需要目标平台可用的 PyTorch、`pycorrector`、Transformers 和模型权重。麒麟 ARM 上应先在目标设备验证：

```bash
uv sync --extra model
uv run typofix model download --data-dir ./data
uv run typofix check ./test.docx --data-dir ./data
```

如果目标平台没有匹配的 PyTorch wheel，不能直接复用 x86/Windows 环境；需要单独选择兼容的 wheel 源或先采用规则-only 模式。

## 9. 测试

```powershell
$env:PYTEST_ADDOPTS = "--basetemp .pytest-tmp"
uv run pytest backend/tests cli/tests -q -m "not model"
cd frontend
npm test -- --run
npm run build
```

真实 MacBERT 冒烟测试需要已经下载模型，并显式设置 `TYPOFIX_RUN_MODEL_TESTS=1`：

```powershell
$env:TYPOFIX_RUN_MODEL_TESTS = "1"
uv run pytest backend/tests/correctors/test_macbert_smoke.py -m model -v
```

## Windows 7 离线发布

完整纠错发布包使用 `packaging/win7` 下的独立 Python 3.8 x64 构建环境和 FP32 ONNX 模型。构建机需要联网下载构建依赖；目标 Windows 7 SP1 电脑只需解压 ZIP 并运行 `TypofixCN.exe`，不需要 Python、Node.js 或网络。

```powershell
py -3.8 -m venv packaging\win7\.venv-win7
packaging\win7\build.ps1
```

最终发布目录是 onedir 形式，模型位于 exe 同级 `data/models/.../onnx`，不会把 PyTorch、Transformers 或重复的 PyTorch 权重放入发布包。完整验收步骤见 `packaging/win7/README-Windows7.txt`。

CPU 依赖不带 CUDA；Windows 和 macOS 可直接本地运行。麒麟 ARM 的 PyTorch wheel、模型加载和内存基线需要在目标设备上单独验证后再制作发行包。

# Typofix CN

Typofix CN 是一个本机优先的中文 DOCX 文档校验工具：同一套 Python 核心同时提供 CLI 和 FastAPI Web 界面。MVP 不使用 SQLite，任务报告和术语库都保存在可读的文件中。

## 快速开始

```powershell
uv sync --extra dev
```

开发前端并启动本地 Web：

```powershell
cd frontend
npm install
npm run build
cd ..
uv run typofix serve --data-dir .\data
```

浏览器打开 <http://127.0.0.1:8000/>。如果没有构建 `frontend/dist`，后端仍可作为纯 API 服务运行。

仅规则校验不需要下载模型。完整校验首次使用前下载 MacBERT：

```powershell
uv sync --extra model
uv run typofix model download --data-dir .\data
```

## CLI

```powershell
uv run typofix check .\论文.docx --rules-only --data-dir .\data
uv run typofix check .\论文目录 --term-lib default --data-dir .\data
uv run typofix terms list --data-dir .\data
uv run typofix terms add default "项目专用术语" --data-dir .\data
```

`check` 会输出 JSON 和离线 HTML 报告路径；`--verbose` 才显示内部子类型。默认用户界面只展示五个错误父类：文字纠错、标点与字符、段落与版式、结构与编号、引用与参考文献。

## 文件布局

默认数据目录由 `platformdirs` 决定（Windows/macOS 为当前用户数据目录），也可以用 `--data-dir` 或 `TYPOFIX_DATA_DIR` 覆盖：

```text
data/
  term-libraries/default.txt   # UTF-8，每行一个术语；空行和 # 注释会忽略
  models/macbert4csc-base-chinese/
  jobs/<job-id>/input/
  jobs/<job-id>/manifest.json
  jobs/<job-id>/report.json
  jobs/<job-id>/report.html
```

术语库就是普通文本文件，修改后重新运行任务即可生效；Web 的术语页也支持新增、移除和下载原始 `.txt` 文件。报告页中选中文字添加术语后，会重新匹配当前任务，但不会再次运行模型。

## 测试

```powershell
$env:PYTEST_ADDOPTS = "--basetemp .pytest-tmp"
uv run pytest backend/tests cli/tests -q -m "not model"
cd frontend
npm test -- --run
npm run build
```

真实 MacBERT 冒烟测试需要已经下载模型，并显式设置 `TYPOFIX_RUN_MODEL_TESTS=1`。CPU 依赖不带 CUDA；Windows 和 macOS 可直接本地运行。麒麟 ARM 的 PyTorch wheel、模型加载和内存基线需要在目标设备上单独验证后再制作发行包。

# Windows 7 Offline FP32 ONNX Packaging Design

## Goal

为 `typofix-cn` 增加一个可在 Windows 7 SP1 x64、4 GB 内存、完全离线环境运行的目录版发布包，保留现有 DOCX 校验、MacBERT 完整纠错、混淆规则、术语库、阈值和 JSON/HTML 报告能力。模型使用 FP32 ONNX，不做量化。

## Constraints

- 目标系统：Windows 7 SP1 x64，Intel i5-6500，4 GB RAM。
- 发布形式：ZIP 解压目录，包含 `TypofixCN.exe`、运行库、前端资源和模型；不要求单文件 EXE。
- 运行方式：完全离线，禁止启动时下载模型或访问 Hugging Face。
- 模型：使用 `data/models/macbert4csc-base-chinese/onnx/model.onnx`，保留 FP32 权重。
- 兼容构建：Python 3.8.10 x64；最终构建和验收在 Windows 7 SP1 虚拟机中完成。
- 资源目标：发布目录约 500–600 MiB；模型和运行库作为可替换的外部文件。
- 非目标：本设计不改动纠错策略、不改变报告协议、不删除当前 PyTorch 开发环境，也不支持 32 位 Windows。

## Architecture

### Inference boundary

保持 `MacBertCorrector` 的公共接口不变。新增 ONNX 后端和 ONNX 候选提供器，负责：

1. 加载 `tokenizer.json` 和 ONNX Runtime CPU Session。
2. 对文本按现有窗口规则分块。
3. 提交 `input_ids`、`attention_mask`、`token_type_ids`。
4. 读取 logits，计算原字概率和 Top-5 单汉字候选。
5. 将 token offset 映射回全文字符位置。

`MacBertCorrector.correct_raw()` 继续负责混淆词优先级、检测阈值、纠正阈值、决策记录和结果转换。开发环境可继续使用现有 PyTorch 后端进行对照测试；Win7 发布构建只收集 ONNX Runtime、tokenizers 和 NumPy。

### Shared model lifetime

`api/app.py` 创建一个共享的 `MacBertCorrector` 实例，API 测试和队列任务共同使用该实例。队列保持单 worker，ONNX Session 配置为 CPU、2 个线程，避免一次进程内重复加载模型造成额外内存压力。

### Frozen resource layout

新增 Win7 启动器和 PyInstaller spec。启动器把 exe 同级 `data` 目录传给 `Settings`，并定位 exe 同级的前端 `dist` 目录。冻结运行时不得依赖源码相对路径、用户目录中的模型缓存或网络下载。

发布目录结构：

```text
TypofixCN/
  TypofixCN.exe
  runtime/                 # PyInstaller 依赖和 VC/UCRT 运行库
  frontend/dist/           # 已构建的 Vite 静态资源
  data/models/.../onnx/    # FP32 ONNX 模型和 tokenizer 文件
  data/term-libraries/
  data/confusions/
  README-Windows7.txt
```

## Compatibility and dependency policy

- Win7 构建使用独立的 Python 3.8 x64 虚拟环境和独立 constraints 文件，不改变当前 Python 3.11–3.12 开发环境。
- Win7 constraints 只包含发布运行时需要的 FastAPI、Uvicorn、python-docx、Pydantic、ONNX Runtime、tokenizers、NumPy、PyInstaller 及其直接依赖。
- 不在发布运行时安装 `torch`、`transformers`、`pycorrector`、Hugging Face Hub 或开发依赖。
- 依赖版本必须同时满足 Python 3.8 wheel 可用、Windows x64 可加载和 Windows 7 SP1 虚拟机离线启动三项验收；通过验收的版本写入 constraints 文件并随构建产物记录。
- 发布包附带所需 VC++/UCRT 运行库，避免目标机依赖系统是否已安装对应运行库。

## Error handling

- 模型文件、tokenizer 文件或 ONNX Runtime 缺失时，服务健康检查返回明确的本地资源错误，浏览器页面不显示 Python traceback。
- ONNX Session 创建失败时，任务进入失败状态并写入现有 manifest/report 错误字段。
- 发布模式禁止执行 `model download` 的联网路径；CLI 仍保留该命令供开发环境使用，但冻结启动器不调用它。
- 输入、术语库、混淆文件和报告路径继续使用现有安全校验。

## Verification

### Unit and integration tests

- 用假的 ONNX Session 验证输入名筛选、logits 解码、Top-5 候选和全文 offset。
- 验证混合数字、英文、汉字、长文本窗口和重叠窗口的结果与现有候选协议一致。
- 验证共享 corrector 只创建一次 backend/session。
- 保持现有 MacBERT pipeline、阈值、混淆和 DOCX 报告测试全部通过。

### Model parity

在开发机上用同一批中文样本分别运行当前 PyTorch 后端和 FP32 ONNX 后端，比较：

- accepted/rejected 决策；
- source、suggestion、start/end；
- detection/correction threshold 边界；
- 混淆规则覆盖结果。

允许不同后端产生极少量浮点排序差异，但核心回归样本和现有报告协议必须一致；出现系统性差异时停止发布构建并修正 ONNX tokenization 或 logits 解码。

### Windows 7 acceptance

在断网的 Windows 7 SP1 x64 虚拟机中验证：

1. 解压 ZIP 后直接运行 `TypofixCN.exe`。
2. 浏览器打开本地页面并通过健康检查。
3. 上传一个包含中文纠错、术语和混淆规则的 DOCX。
4. 生成 JSON 和 HTML 报告，并检查字符位置与建议文本。
5. 连续执行两个任务，确认模型不重复加载且进程不异常退出。
6. 在 4 GB 内存限制下完成单个实际 DOCX 任务。

## Acceptance criteria

- Windows 7 SP1 x64 离线可启动并完成完整 MacBERT 纠错。
- 发布包不包含 Torch、Transformers、pycorrector 或重复的 PyTorch 权重。
- 现有前端、DOCX 处理、术语库、混淆规则、阈值和报告协议保持可用。
- FP32 ONNX 模型保留，发布目录不超过约 600 MiB，具体大小以构建后文件统计为准。
- 构建、单元测试、模型对照测试和 Win7 离线验收均有可复现命令和结果记录。

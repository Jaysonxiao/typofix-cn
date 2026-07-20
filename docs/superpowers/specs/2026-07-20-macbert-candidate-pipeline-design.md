# MacBERT 候选推理与检测纠正分层设计

## 目标

在不更换模型、不训练新检测网络、不改变 DOCX 报告结构的前提下，提高现有 MacBERT 中文拼写检测的召回能力，并保留对误报的可控性。

本次实现包含四项能力：

1. 使用 tokenizer `offset_mapping` 对齐模型 token 与原文字符，保留数字、英文和标点提供的上下文。
2. 增加可人工编辑的 UTF-8 混淆词库。
3. 读取 MacBERT logits 的 Top-K 候选，而不是只使用 argmax。
4. 在工程层拆分候选检测与纠正选择，不训练新的神经检测器。

现有中文分段推理保留为兼容兜底。DOCX 上传、任务队列、规则、术语库、历史任务和报告数据结构保持不变。

## 已确认的运行条件

当前使用 `pycorrector 1.1.3` 和本机 `macbert4csc-base-chinese` 权重。其 `_predict()` 直接执行 argmax，再通过解码 token 数与原文字符数比较决定是否整句回退，因此无法提供 Top-K，也无法正确处理包含多字符 WordPiece token 的混合文本。

本机真实 tokenizer 为 fast tokenizer，能够返回稳定的字符偏移。例如输入：

```text
2023年学员平均就业新资18K/月（高于行业均值32%）
```

其中“新”的 token 偏移为 `[11, 12]`；`202`、`##3`、`18k` 等多字符 token 也有明确范围。因此可以在保留整句上下文的同时，只允许单个汉字位置进入纠正决策。

## 方案选择

采用项目内自定义推理适配层，不修改第三方 pycorrector 源码：

- 相比继续中文分段，该方案保留跨数字和英文边界的上下文，并能实现真实 Top-K。
- 相比 fork pycorrector，该方案避免第三方版本升级冲突。
- 继续复用 pycorrector 加载的 tokenizer、模型、设备和模型权重，不加载第二份模型。

## 组件边界

### MacBertCandidateProvider

负责模型前向推理和 token 到字符的映射：

- 对完整文本执行 tokenizer 和模型前向推理。
- 请求 `offset_mapping`、特殊 token 标记和 attention mask。
- 对每个可修改位置计算 softmax。
- 输出原字概率、Top-5 非原字候选及概率和全文字符范围。
- 只有偏移长度为 1 且原文位置为汉字的 token 可以产生候选。
- 候选 token 也必须能解码为单个汉字；特殊 token、WordPiece 片段和非汉字候选全部过滤。
- 数字、英文、空白、标点和多字符 token 只提供上下文，永远不会被替换。

该组件不决定是否采纳候选，也不读取混淆词库。

### TextConfusionRepository

负责读取和验证全局混淆词库：

```text
data/confusions/default.txt
```

文件格式为：

```text
# 错误写法 => 正确写法
新资 => 薪资
因该 => 应该
```

规则：

- 使用 UTF-8 文本。
- 忽略空行和 `#` 注释。
- `=>` 两侧去除首尾空白。
- 错误写法与正确写法必须非空、只包含汉字且字符数相同，以保持位置映射稳定并保证非汉字永远不被替换。
- 完全重复的规则只生效一次。
- 同一错误写法指向不同正确写法时，返回带文件行号的配置错误，不静默选择。
- 每次检测前重新读取，用户修改文件后无需重启服务。
- 初始化数据目录时创建文件，并预置 `新资 => 薪资`。

### CorrectionDetector

负责判断候选位置是否值得进入纠正层：

- 模型检测分数定义为 `1 - original_score`。
- 模型候选只有在检测分数达到 `detection_threshold` 时才能继续。
- 混淆词精确命中不受检测阈值影响，直接进入纠正层。

默认检测阈值为 `0.50`。

### CorrectionSelector

负责选择最终建议：

- 模型候选中选择概率最高的非原字候选。
- 只有候选概率达到 `correction_threshold` 才采纳。
- 混淆词精确命中直接采纳，不受纠正阈值影响。
- 同一位置同时存在模型和混淆词结果时，混淆词优先。
- 多个混淆词重叠时，最长原文匹配优先；长度相同时按文件顺序。
- 已被一个混淆词占用的字符范围不再接受重叠模型修改。

默认纠正阈值为 `0.30`。

### MacBertCorrector

保留现有公开职责：

- `correct()` 继续返回项目内 `CorrectionResult`，供 DOCX 分析流程使用。
- `correct_raw()` 继续返回 `source / target / errors`，并为测试入口增加 `decisions`。
- `target` 由被采纳且不重叠的决策合并生成。
- `errors` 保持现有三元组结构 `(original, suggestion, start)`。
- `decisions` 不进入 DOCX 报告模型。

## 数据流

一次检测按以下顺序执行：

1. 读取并验证混淆词库。
2. 对完整原文执行混淆词最长匹配，生成确定性候选。
3. 使用 MacBertCandidateProvider 对完整文本执行模型推理。
4. CorrectionDetector 根据原字概率筛选模型候选。
5. CorrectionSelector 根据候选概率、混淆词优先级和重叠规则生成最终决策。
6. 合并 `target`、`errors` 和测试诊断 `decisions`。
7. `correct()` 只把最终 `errors` 转换为 `CorrectionFinding`。

## 诊断输出

`POST /api/v1/macbert/test` 的响应增加 `decisions`：

```json
{
  "source": "平均就业新资18K/月",
  "target": "平均就业薪资18K/月",
  "errors": [["新", "薪", 6]],
  "decisions": [
    {
      "start": 6,
      "end": 7,
      "source": "新",
      "suggestion": "薪",
      "provider": "confusion",
      "original_score": 0.46,
      "suggestion_score": 0.41,
      "accepted": true,
      "reason": "confusion_exact_match",
      "candidates": [
        {"text": "薪", "score": 0.41}
      ]
    }
  ]
}
```

字段规则：

- `provider` 为 `model` 或 `confusion`。
- 混淆词命中即使同时获得模型分数，来源仍为 `confusion`。
- 无法取得对应模型分数时，分数字段为 `null`。
- 模型诊断只保留最佳非原字候选达到最低诊断分数 `0.05` 的位置。
- 被阈值拒绝的模型候选也记录，`accepted=false`，并给出 `detection_below_threshold` 或 `correction_below_threshold`。
- 非汉字位置不产生诊断记录。

DOCX JSON/HTML 报告和历史任务不增加 `decisions`。

## API 与页面

测试请求调整为：

```json
{
  "text": "平均就业新资18K/月",
  "detection_threshold": 0.50,
  "correction_threshold": 0.30
}
```

- 两个阈值范围均为 `0.0` 到 `1.0`。
- 现有单字段 `threshold` 不继续作为请求字段；前后端在同一版本内同步更新。
- 首页测试区把原“置信度阈值”替换为两个紧凑滑杆：检测阈值和纠正阈值。
- JSON 结果继续原样格式化显示完整响应。
- DOCX 上传区域和所有后续操作保持不变。

DOCX 校验不增加可调参数，使用默认检测阈值 `0.50` 和纠正阈值 `0.30`，避免改变任务创建接口和历史任务结构。后续建立验证集后再校准默认值。

## 长文本与批处理

- 单个输入超过 120 个字符时复用现有 `chunk_sentence()`，窗口为 120 字、重叠 16 字。
- 每个窗口的局部偏移转换为全文偏移。
- 重叠区域的相同全文位置按建议候选概率去重；混淆词仍然优先。
- 混淆词匹配始终在完整原文上执行，不受窗口边界影响。
- 同一批输入的窗口合并为批量模型前向推理，避免逐句加载或逐窗口调用模型。
- 每个模型输入保留 `[CLS]` 和 `[SEP]` 所需空间，不允许 tokenizer 静默截断。

## 兼容、降级与错误处理

- backend 提供 fast tokenizer、模型和 logits 时使用新候选推理路径。
- backend 不提供其中任一接口时，降级到现有中文分段 `correct_batch()` 路径。
- 降级结果保持 `source / target / errors`，并在 `decisions` 中记录 `provider=model` 和 `reason=backend_fallback`；无法取得的分数字段为 `null`。
- 模型前向推理异常继续转换为 `ModelInferenceError`，不因异常静默降级。
- 混淆词配置错误返回明确的文件行号和原因；测试接口转为可读的 503 模型配置错误，DOCX 任务记录文档失败原因。
- 浏览器不返回 Python 堆栈和无关本机路径。

## 性能边界

- 只复用已经加载的 MacBERT tokenizer 和模型，不加载第二份模型。
- 每个批次只执行一次模型前向推理；Top-K 在同一 logits 上计算。
- 混淆词文件体积预期很小，每次读取的成本可忽略。
- 本次不增加语言模型、词频服务、数据库、远程 API 或 LLM 审核。

## 测试与验收

### 单元测试

- 混合数字、英文和中文时 token 偏移能够还原全文字符位置。
- 多字符非中文 token 只参与上下文，不产生修改候选。
- 原字仍为 Top-1 时，满足两个阈值的 Top-2 候选能够被采纳。
- 检测阈值和纠正阈值分别拒绝候选，并记录对应原因。
- 混淆词精确命中直接采纳，不受阈值影响。
- 混淆词最长匹配、重复去重、冲突行号、等长校验和每次重新加载。
- 同一位置混淆词覆盖模型候选。
- 长文本窗口、重叠位置去重和全局偏移正确。
- backend 能力不足时进入兼容降级；实际推理异常不静默降级。
- `correct()` 继续生成与 DOCX 分析兼容的 `CorrectionFinding`。

### API 与前端测试

- 两个阈值的默认值、范围校验和透传。
- 响应保留 `source / target / errors` 并增加 `decisions`。
- 页面滑杆、请求体、诊断 JSON 和测试按钮状态。
- DOCX 文件与文件夹上传入口继续存在，任务请求体保持不变。

### 真实模型验收

以下输入应得到“薪资”和全文偏移 11：

```text
2023年学员平均就业新资18K/月（高于行业均值32%）
```

以下正确文本不得修改：

```text
2023年学员平均就业薪资18K/月
MacBERT模型效果测试
```

后端非模型测试、前端测试、类型检查和生产构建必须全部通过。真实模型输出同时检查 `target`、`errors` 和 `decisions`。

## 明确不在本次范围

- 训练 Soft-Masked BERT 或其他神经检测器。
- 领域语料微调、Top-K 词频重排或外部检索。
- 混淆词库 Web 管理页面。
- 自动修改用户 DOCX。
- 修改 DOCX 报告 schema、历史任务 schema 或任务创建参数。

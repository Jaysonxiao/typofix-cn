# Typofix CN 中文文档校验 MVP 设计

日期：2026-07-17  
状态：已确认，待实施计划

## 1. 目标

Typofix CN 是供个人在本机使用的中文 DOCX 校验工具，同时提供 Web 界面和 CLI。MVP 使用 `shibing624/macbert4csc-base-chinese` 识别中文错别字，并用确定性规则检查常见论文写作问题。系统只输出报告，不自动修改原始 DOCX。

核心目标：

- 支持单个 DOCX、多个 DOCX 和目录批量校验。
- 检查正文段落和表格单元格，不检查页眉、页脚、批注、文本框和脚注。
- 用稳定的位置描述代替不可靠的 DOCX 视觉行号：文档、区域、段落、句子和字符范围。
- 使用可人工编辑的 UTF-8 文本文件维护多个术语库。
- 保留完整模型判断，并将命中术语的错字标记为“术语豁免”。
- Web 与 CLI 共用同一校验核心，并生成等价的 JSON 和单文件 HTML 报告。
- 默认纯 CPU 运行，优先支持 Windows 和 macOS，并为后续麒麟 Linux ARM 部署保留兼容路径。

## 2. 非目标

MVP 不包含以下能力：

- 自动修改或回写 DOCX。
- DOC、PDF、WPS 等其他文件格式。
- 页眉、页脚、批注、文本框、脚注和 Word 视觉页码/行号校验。
- 登录、用户、权限、多租户和远程部署。
- 实际调用大模型；只定义纠错适配器入口。
- 针对特定学校的字体、封面、页边距等完整模板校验。
- 完整实现 GB/T 7714 每一种参考文献著录格式。
- 麒麟 ARM 安装包交付；MVP 只避免引入明显的 x86 专属依赖并保留构建入口。

## 3. 总体架构

项目使用单仓库，包含以下模块：

```text
backend/                 FastAPI API 和应用启动入口
backend/typofix/
  application/           校验任务、术语回算、报告等用例
  domain/                文档位置、Issue、报告和任务模型
  documents/             DOCX 读取、段落分类和句子定位
  correctors/            Corrector 接口、MacBERT 和测试替身
  rules/                 标点、段落、结构和引用规则
  terms/                 文本术语库和匹配逻辑
  reports/               JSON 与 HTML 报告生成
  api/                   HTTP 路由和请求/响应模型
cli/                     Typer CLI 入口
frontend/                React、TypeScript 和 Vite 前端
data/                    开发环境默认数据目录，不提交运行数据
docs/                    设计与使用文档
```

开发时前后端分别运行；发布时 React 构建产物由 FastAPI 托管，因此最终只需启动一个本地服务。业务逻辑不放在 API、CLI 或 React 中，Web 与 CLI 都调用 `application` 用例层。

个人使用模式默认监听 `127.0.0.1`，不提供认证。CPU 模型任务由单进程队列串行处理，模型在进程内只加载一次，句子按有上限的小批量推理。

## 4. 校验数据流

1. Web 接收一个或多个上传文件；文件夹选择保留相对路径。CLI 接收一个或多个文件或目录。
2. 系统递归收集 `.docx`，忽略其他文件和 `~$*.docx` 临时文件。
3. 输入文件复制到 `data/jobs/<job-id>/input`，同时创建任务清单。
4. DOCX 解析器提取正文段落和表格单元格，并保留区域、段落、表格/行/列、样式和字符位置。
5. 文本按句切分。长句按模型限制分块并保留重叠区，以便将模型结果映射回原始字符范围并去重。
6. MacBERT 纠错器和确定性规则引擎分别产生原始发现。
7. 标准化器把模型和规则结果转换为统一 `Issue`。
8. 术语策略使用本次选中的多个术语库计算 `actionable` 或 `term_suppressed` 状态。
9. 系统保存完整 JSON，生成自包含 HTML，并将同一报告返回给 Web。
10. 添加或修改术语后，只从原始发现重新计算术语状态、统计和报告，不再次运行模型或规则。

## 5. DOCX 范围与位置模型

### 5.1 支持范围

- 正文中的段落。
- 表格单元格内的段落，包括嵌套遍历时遇到的文本段落。

不支持页眉、页脚、批注、文本框和脚注。解析器必须显式标识支持区域，不能把未知区域误报为正文。

### 5.2 段落角色

段落角色至少包括：

- `body`：普通正文。
- `heading`：标题或具有大纲级别的段落。
- `list_item`：项目符号或编号列表。
- `table_cell`：表格单元格内容。
- `blank`：空段落。
- `unknown`：无法可靠判断。

角色判断优先使用 Word 样式、大纲级别和编号属性，再使用保守的文本特征。只有 `body` 默认参与首行缩进强校验；标题、列表、空段落和表格单元格不强制首行缩进。

### 5.3 位置

DOCX 不存储稳定的视觉行号，因此问题位置使用：

```json
{
  "document_path": "chapter/第一章.docx",
  "region": "body",
  "paragraph_index": 12,
  "sentence_index": 2,
  "start_offset": 8,
  "end_offset": 9,
  "table": null
}
```

表格位置额外包含表格、行、列和单元格内段落序号。所有字符范围采用 Python 字符串的零基、左闭右开语义。面向用户的中文描述转换为一基序号。

## 6. 纠错模型接口

定义统一 `Corrector` 接口：

```text
correct(sentences: list[SentenceInput]) -> list[CorrectionFinding]
```

`CorrectionFinding` 至少包含原文范围、原文、建议文本、可选置信信息和提供者元数据。

MVP 实现 `MacBertCorrector`：

- 模型为 `shibing624/macbert4csc-base-chinese`。
- 设备固定为 CPU。
- 模型使用 `eval` 和无梯度推理模式。
- 模型目录可联网下载，也可由 `--model-dir` 或数据目录提供离线权重。
- 模型未就绪或加载失败时任务明确失败，不静默跳过。
- Web 和 CLI 均提供显式“仅规则校验”模式。

未来的大模型或 ONNX 实现只需实现同一接口，不改变文档、术语和报告模块。

## 7. 两级错误分类

所有问题都有面向用户的父类和面向程序的子类型：

```text
category_code = PARAGRAPH_LAYOUT
type_code     = FIRST_LINE_INDENT_MISSING
```

Web 列表、统计和筛选只展示五个父类。JSON 保留父类与子类型；HTML 默认展示父类和自然语言问题说明；CLI 详细模式可以输出子类型。

### 7.1 文字纠错 `TEXT_CORRECTION`

- `SPELLING_TYPO`：MacBERT 检测到的等长错字替换。
- `REPEATED_WORD`：明显的连续重复字词。
- `TERM_INCONSISTENT`：全文术语写法不一致，作为后续扩展类型。
- `ABBREVIATION_UNEXPLAINED`：缩略语首次出现未解释，作为后续扩展类型。

### 7.2 标点与字符 `PUNCTUATION_CHARACTER`

- `PUNCTUATION_DUPLICATE`
- `PUNCTUATION_UNPAIRED`
- `PUNCTUATION_WIDTH_MISMATCH`
- `PUNCTUATION_COMBINATION_INVALID`
- `ELLIPSIS_OR_DASH_INVALID`
- `PARAGRAPH_END_PUNCTUATION_MISSING`
- `WHITESPACE_REDUNDANT`
- `FULLWIDTH_SPACE_INVALID`
- `NUMBER_STYLE_INCONSISTENT`
- `DATE_FORMAT_SUSPECT`
- `NUMBER_UNIT_SPACING`
- `UNIT_STYLE_INCONSISTENT`

数字、日期和单位规则受学科影响，MVP 默认只产生“提示”。

### 7.3 段落与版式 `PARAGRAPH_LAYOUT`

- `FIRST_LINE_INDENT_MISSING`
- `FIRST_LINE_INDENT_INVALID`
- `MANUAL_INDENT_SPACES`
- `BODY_STYLE_OUTLIER`
- `EXCESSIVE_EMPTY_PARAGRAPH`

正文样式异常以文档主体样式和同类段落的主流值为基线，不能在没有模板时把某一种字体或字号硬编码为唯一正确值。

### 7.4 结构与编号 `STRUCTURE_NUMBERING`

- `HEADING_END_PUNCTUATION`
- `HEADING_NUMBER_INVALID`
- `HEADING_LEVEL_JUMP`
- `HEADING_STYLE_INCONSISTENT`
- `FIGURE_NUMBER_DUPLICATE_OR_GAP`
- `TABLE_NUMBER_DUPLICATE_OR_GAP`
- `CAPTION_STYLE_INCONSISTENT`
- `CROSS_REFERENCE_TARGET_MISSING`
- 学校模板相关结构类型保留扩展入口，MVP 不启用。

### 7.5 引用与参考文献 `CITATION_REFERENCE`

- `CITATION_TARGET_MISSING`
- `REFERENCE_NOT_CITED`
- `REFERENCE_NUMBER_DUPLICATE_OR_GAP`
- `REFERENCE_STYLE_INCONSISTENT`

MVP 实现数字顺序编码制中可高置信判断的编号、缺失引用和明显一致性检查，不宣称完成全部 GB/T 7714 著录校验。

### 7.6 MVP 启用范围

MVP 首批启用：

- 文字纠错中的模型错字和明显重复字词。
- 标点、空白、全半角、省略号和破折号等高可靠规则。
- 首行缩进、手工空格缩进、正文样式离群和连续空段落。
- 标题层级/编号、图表编号和交叉引用中的高可靠检查。
- 数字顺序编码制参考文献的编号和目标一致性检查。

规则必须声明默认严重程度以及是否默认开启。容易受学校、学科或写作风格影响的规则默认为“提示”，或保留类型但默认关闭。

## 8. Issue 领域模型

每条 `Issue` 至少包含：

- 稳定问题 ID；由任务内文档标识、来源、子类型、位置、原文和建议生成，不包含术语状态，因此重新匹配前后保持不变。
- `source`：`model` 或 `rule`。
- `category_code` 和 `type_code`。
- `severity`：`error`、`warning` 或 `info`。
- `status`：`actionable` 或 `term_suppressed`。
- 文档及精确位置。
- 原文片段、建议文本、自然语言说明和上下文。
- 可选模型置信信息或规则编码。
- 命中的术语、术语库和术语范围。

术语状态不覆盖或删除原始模型发现。汇总统计同时提供总发现数、待处理数和术语豁免数。

## 9. 术语库

### 9.1 文件格式

术语库存放在 `data/term-libraries/*.txt`。每个文件代表一个术语库，每行一个术语：

```text
麒麟操作系统
MacBERT
自然语言处理
# 以井号开头的行是注释
```

读取规则：

- UTF-8，兼容 UTF-8 BOM。
- 忽略空行、首尾空白和以 `#` 开头的注释行。
- 同一文件中的重复术语只生效一次。
- 文件名必须满足安全的术语库名称规则，不能包含路径分隔符。
- 每次新任务从磁盘重新加载所选术语库。

### 9.2 匹配语义

- 在原始句子中做连续、精确匹配。
- 原文和术语先做 Unicode NFC 规范化，再进行区分大小写的匹配；实现必须保留规范化文本到原文字符范围的映射。
- 不做模糊、同义词、英文大小写折叠或繁简转换。
- 只有 `SPELLING_TYPO` 可以被术语豁免。
- 错误字符范围完全包含在命中术语范围内时，状态改为 `term_suppressed`。
- 多个术语或术语库重叠命中时全部记录。

### 9.3 划词添加与回算

用户在问题上下文中选择连续文本，再选择一个目标术语库。后端验证选区非空、不跨段落、不含换行，MVP 最大长度为 100 个字符。写入采用临时文件原子替换并去重。

添加成功后，系统基于任务中保存的原始发现重新执行全部术语匹配，重写报告状态、汇总、JSON 和 HTML，不运行模型或规则。页面也提供“重新加载术语库并匹配”，用于用户在文本编辑器中手工修改文件后的即时刷新。

## 10. 任务与文件存储

系统不使用数据库。数据根目录结构为：

```text
data/
  term-libraries/
    default.txt
  models/
  jobs/
    <job-id>/
      input/
      manifest.json
      report.json
      report.html
```

开发环境默认使用项目下的 `data`。安装环境默认使用系统用户数据目录，并允许通过 `--data-dir` 或 `TYPOFIX_DATA_DIR` 覆盖。Web 术语页面展示实际目录。

任务状态包括：

- `queued`
- `running`
- `completed`
- `completed_with_document_failures`
- `failed`
- `interrupted`

`manifest.json` 在阶段变化时原子更新。应用启动时，残留的 `queued` 或 `running` 任务转换为 `interrupted`。最近任务列表通过扫描任务清单获得，不维护额外索引数据库。

## 11. 报告

### 11.1 JSON

JSON 顶层至少包含：

- `schema_version`
- 任务 ID、时间、状态和执行模式。
- 模型、规则版本和运行平台信息。
- 所选术语库名称、修改时间和内容摘要。
- 文档列表、成功/失败状态和失败原因。
- 原始发现、当前 Issue 状态和位置。
- 按文档、父类、来源、严重程度和状态统计的汇总。

初始 `schema_version` 为 `1`。报告读取器必须按版本分发，不能无版本解析。

### 11.2 HTML

HTML 为可离线打开的单文件报告：

- 不请求后端资源。
- 内嵌必要样式和已转义的报告数据。
- 展示汇总、父类、位置、原文、建议、状态和上下文。
- 支持在静态报告内进行父类、文档、来源和状态筛选。
- 静态 HTML 不提供写术语功能；划词添加仅在运行中的 Web 工作台提供。

报告和术语文件都使用同目录临时文件加原子替换，避免中断产生半写文件。

## 12. Web 界面

### 12.1 校验首页

- 单文件/多文件上传入口。
- 文件夹选择入口，并保留相对路径；浏览器不支持文件夹选择时允许多文件回退。
- 待处理 DOCX 列表。
- 多选术语库。
- “完整校验”和“仅规则校验”模式。
- 任务进度、文档数和当前阶段。
- 最近任务列表和重新打开入口。

### 12.2 报告工作台

顶部展示文档数、问题总数、待处理数、术语豁免数、五个父类数量，以及 JSON/HTML 下载入口。

筛选维度：

- 文档。
- 五个错误父类。
- `待处理` / `术语豁免`。
- `模型异常` / `规则异常`。

问题列表只展示父类、位置、原文、建议和状态。详情展示完整上下文并高亮范围。用户可在上下文中划词，选择目标术语库并添加；成功后原地刷新当前任务。

### 12.3 术语库页面

- 查看术语库名称、术语数量、更新时间和文件路径。
- 创建术语库。
- 查看、搜索、添加和删除术语。
- 下载原始 TXT。
- 触发重新加载。

## 13. HTTP API 边界

API 使用 `/api/v1` 前缀。主要能力：

- 创建任务并上传文件。
- 获取任务列表、清单、进度和报告。
- 下载 JSON、HTML 和失败明细。
- 对指定任务重新执行术语匹配。
- 列出、创建术语库。
- 列出、添加和删除术语。
- 获取模型就绪状态。

长任务通过状态轮询更新。单用户 MVP 不引入外部队列或消息中间件。API 返回面向用户的错误代码和安全说明；内部堆栈只写服务端日志。

## 14. CLI

主要命令：

```powershell
typofix check .\论文.docx --term-lib default --html
typofix check .\论文目录 --term-lib default --term-lib computer-science
typofix check .\论文.docx --rules-only
typofix serve
typofix terms list
typofix terms add default "麒麟操作系统"
typofix model download
```

CLI 行为：

- `check` 接受文件、多个路径或递归目录。
- 默认生成 JSON 和 HTML，输出目录可覆盖。
- `serve` 默认监听 `127.0.0.1`。
- `model download` 写入配置的模型目录。
- 输入、配置、模型或系统失败返回非零退出码。
- 文档中发现问题不等同程序失败，默认退出码仍为零。
- `--verbose` 显示内部子类型；普通输出只显示父类。

## 15. 异常与安全边界

- 校验扩展名、ZIP/DOCX 结构和必要的 OOXML 内容。
- 限制单文件大小、解压后总大小、批量文件数和句子批量大小，默认值可配置。
- 损坏、加密、伪装或超限 DOCX 给出明确文档失败原因。
- 批量任务中单个文档失败不终止其他文档。
- 模型未就绪时完整校验任务失败，不能静默变成仅规则校验。
- 输入相对路径经过规范化，禁止绝对路径和 `..` 写出任务目录。
- HTML 转义所有文档文本和文件名，避免内容被作为脚本执行。
- API 不向浏览器返回 Python 堆栈或本机敏感路径；术语管理页只显示用户选择的数据目录。
- 本地服务默认不监听局域网地址。用户显式修改监听地址时由文档提示无认证风险。

## 16. 跨平台与打包

- Python 基线为 3.11。
- 后端使用 PyTorch、Transformers、python-docx、FastAPI、Pydantic 和 Typer 等跨平台依赖。
- 前端使用 React、TypeScript 和 Vite，发布产物为静态文件。
- Windows、macOS 和 Linux ARM 分别锁定和构建依赖，不尝试制作单一跨系统安装包。
- CPU 包不引入 CUDA；不使用明确依赖 x86 的扩展。
- 模型权重与程序分离，可下载或复制到离线目录。
- Windows 和 macOS MVP 提供开发/本地启动方式，后续再基于实际交付需要选择平台安装器。
- 麒麟 ARM 打包前必须在目标设备验证 PyTorch aarch64 wheel、模型加载、中文字体、峰值内存和处理性能；未实机验证前不承诺可部署产物。

## 17. 测试策略

### 17.1 单元测试

- DOCX 正文、表格、段落角色和字符位置映射。
- 每条规则及其严重程度、开关和父子类型。
- 术语文件读取、多库合并、重叠匹配和原子写入。
- 术语只豁免 `SPELLING_TYPO`。
- JSON 版本和 HTML 转义。

### 17.2 模型测试

- 普通测试使用确定性的假 `Corrector`，不下载权重。
- 验证长句分块、重叠去重和字符回映。
- 真实 MacBERT 冒烟测试使用固定中文错句，仅在模型已存在或显式启用时运行。

### 17.3 API、CLI 与前端测试

- 文件、文件夹、多术语库任务。
- 排队、进度、完成、部分失败和中断状态。
- CLI 输入、退出码和报告输出。
- 前端父类/状态/来源/文档筛选。
- 上下文高亮和划词添加术语。
- 添加术语后模型调用次数不增加，报告状态和统计更新。

### 17.4 集成与跨平台测试

程序生成小型 DOCX 样本，覆盖正文、标题、列表、表格、跨 Run 文本、中文路径、损坏文件、标点、缩进、编号和引用。自动测试覆盖 Windows、macOS 和 Linux x86；麒麟 ARM 在交付阶段使用真实设备冒烟测试。

## 18. MVP 验收标准

- Web 和 CLI 均可处理单个 DOCX 和递归目录。
- 正确读取正文和表格，排除约定的不支持区域。
- 模型和规则结果生成统一 JSON 和离线 HTML。
- 每条问题可定位到文档、区域、段落、句子和字符范围。
- 页面只展示五个父类，并可按父类、状态、来源和文档筛选。
- 多个术语库可以同时生效。
- 划词添加术语后，当前任务全部重新匹配且不重复运行模型。
- 模型异常但被术语豁免的记录仍可查看。
- 单个损坏文档不影响批量中的正常文档。
- 模型只加载一次，批量和内存使用有配置上限。
- 相同输入下，Web 与 CLI 产生等价问题记录。
- 首个可运行版本记录模型加载时间、每万字处理时间和峰值内存，形成 Windows 与 macOS CPU 性能基线，再据此设定硬性性能目标。

## 19. 规范依据

- GB/T 7713.1-2025《信息与文献 编写规则 第1部分：学位论文》，2026-02-01 实施。
- GB/T 7714-2025《信息与文献 参考文献著录规则》，2026-07-01 实施。
- GB/T 15834-2011《标点符号用法》。
- GB/T 15835-2011《出版物上数字用法》。
- 高校现行论文规范只用于总结常见问题；学校专属版式不作为通用硬编码规则。

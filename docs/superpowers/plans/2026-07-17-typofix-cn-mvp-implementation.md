# Typofix CN MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first Chinese DOCX validation application with a shared Python core, MacBERT and deterministic rules, editable text terminology libraries, JSON/HTML reports, a Typer CLI, and a React/FastAPI Web interface.

**Architecture:** The Python domain and application layers own document extraction, correction, rules, terminology decisions, jobs, and reports. FastAPI and Typer are thin adapters over those use cases, while React consumes versioned HTTP report models. Runtime state is stored as atomic JSON, HTML, DOCX, and UTF-8 text files under one configurable data directory; no database or external queue is used.

**Tech Stack:** Python 3.11, uv, Pydantic, FastAPI, Typer, python-docx, PyTorch, Transformers/pycorrector, Jinja2, pytest, React, TypeScript, Vite, Vitest, Testing Library, Playwright.

---

## Planned file map

```text
pyproject.toml                         Python package, dependency groups and CLI entry point
.gitignore                            Runtime, model, build and test artifacts
README.md                             Local setup, CLI/Web use and data locations
backend/src/typofix_cn/config.py      Runtime settings and path resolution
backend/src/typofix_cn/domain/        Enums, positions, issues, reports and jobs
backend/src/typofix_cn/documents/     DOCX extraction, paragraph roles, sentences and chunks
backend/src/typofix_cn/correctors/    Corrector protocol, fake and MacBERT adapters
backend/src/typofix_cn/rules/         Rule protocol and rule families
backend/src/typofix_cn/terms/         Text-file repository and exact matcher
backend/src/typofix_cn/reports/       JSON and self-contained HTML writers
backend/src/typofix_cn/jobs/          File job repository, runner and single-worker queue
backend/src/typofix_cn/api/           FastAPI app, job routes, terminology routes and errors
backend/tests/                        Unit, integration and API tests
cli/src/typofix_cli/main.py           Typer commands
cli/tests/                            CLI tests
frontend/src/api/                     Typed API client
frontend/src/pages/                   Upload, report and terminology pages
frontend/src/components/              Reusable filters, issue context and task controls
frontend/src/types.ts                 API/report types matching schema version 1
frontend/tests/                       Vitest component tests
frontend/e2e/                         Playwright acceptance tests
scripts/                              Cross-platform smoke and packaging helpers
```

## Phase 1: Shared core and CLI

### Task 1: Scaffold the Python package and stable domain models

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `backend/src/typofix_cn/__init__.py`
- Create: `backend/src/typofix_cn/config.py`
- Create: `backend/src/typofix_cn/domain/enums.py`
- Create: `backend/src/typofix_cn/domain/catalog.py`
- Create: `backend/src/typofix_cn/domain/locations.py`
- Create: `backend/src/typofix_cn/domain/issues.py`
- Create: `backend/src/typofix_cn/domain/jobs.py`
- Create: `backend/tests/domain/test_issues.py`
- Create: `backend/tests/test_config.py`
- Create: `conftest.py`

- [ ] **Step 1: Write failing domain and configuration tests**

```python
# backend/tests/domain/test_issues.py
from typofix_cn.domain.enums import IssueCategory, IssueSource, IssueStatus, Severity
from typofix_cn.domain.issues import Issue
from typofix_cn.domain.locations import TextLocation


def test_issue_id_does_not_change_when_term_status_changes() -> None:
    location = TextLocation(
        document_path="论文.docx",
        region="body",
        paragraph_index=2,
        sentence_index=1,
        start_offset=3,
        end_offset=4,
    )
    issue = Issue.create(
        source=IssueSource.MODEL,
        category=IssueCategory.TEXT_CORRECTION,
        type_code="SPELLING_TYPO",
        severity=Severity.ERROR,
        location=location,
        original="新",
        suggestion="心",
        message="疑似错别字",
        context="今天新情很好",
    )
    suppressed = issue.model_copy(update={"status": IssueStatus.TERM_SUPPRESSED})
    assert issue.issue_id == suppressed.issue_id


def test_every_subtype_maps_to_one_user_visible_parent() -> None:
    from typofix_cn.domain.catalog import ERROR_TYPES

    assert len(ERROR_TYPES) == len(set(ERROR_TYPES))
    assert all(item.category in set(IssueCategory) for item in ERROR_TYPES.values())
    assert ERROR_TYPES["FIRST_LINE_INDENT_MISSING"].category == IssueCategory.PARAGRAPH_LAYOUT


# backend/tests/test_config.py
from typofix_cn.config import Settings


def test_settings_create_expected_data_paths(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path)
    settings.ensure_directories()
    assert settings.jobs_dir == tmp_path / "jobs"
    assert settings.term_libraries_dir == tmp_path / "term-libraries"
    assert settings.models_dir == tmp_path / "models"
    assert (settings.term_libraries_dir / "default.txt").exists()
```

- [ ] **Step 2: Run the tests and verify import failures**

Run: `uv run pytest backend/tests/domain/test_issues.py backend/tests/test_config.py -v`  
Expected: FAIL because `typofix_cn` and its models do not exist.

- [ ] **Step 3: Add package metadata, dependencies and domain models**

```toml
# pyproject.toml
[project]
name = "typofix-cn"
version = "0.1.0"
requires-python = ">=3.11,<3.12"
dependencies = [
  "fastapi>=0.116,<1",
  "jinja2>=3.1,<4",
  "platformdirs>=4.3,<5",
  "pydantic>=2.11,<3",
  "pydantic-settings>=2.10,<3",
  "python-docx>=1.2,<2",
  "python-multipart>=0.0.20,<1",
  "typer>=0.16,<1",
  "uvicorn[standard]>=0.35,<1",
]

[project.optional-dependencies]
model = [
  "huggingface-hub>=0.34,<2",
  "pycorrector>=1.1.2,<2",
  "torch>=2.6,<3",
  "transformers>=4.45,<6",
]
dev = [
  "httpx>=0.28,<1",
  "pytest>=8.4,<9",
  "pytest-asyncio>=1.1,<2",
  "pytest-cov>=6.2,<7",
]

[project.scripts]
typofix = "typofix_cli.main:app"

[tool.setuptools.packages.find]
where = ["backend/src", "cli/src"]

[tool.pytest.ini_options]
pythonpath = ["backend/src", "cli/src"]
testpaths = ["backend/tests", "cli/tests"]
```

```gitignore
# .gitignore
.venv/
.pytest_cache/
.coverage
htmlcov/
__pycache__/
*.py[cod]
frontend/node_modules/
frontend/dist/
frontend/playwright-report/
frontend/test-results/
data/jobs/
data/models/
data/term-libraries/*.txt
!data/term-libraries/.gitkeep
```

Create root `conftest.py` with shared `tmp_path`-based DOCX builders and fake report factories so both `backend/tests` and `cli/tests` use the same fixtures. The fixture must not download a model or write into the repository data directory.

```python
# backend/src/typofix_cn/domain/enums.py
from enum import StrEnum


class IssueSource(StrEnum):
    MODEL = "model"
    RULE = "rule"


class IssueStatus(StrEnum):
    ACTIONABLE = "actionable"
    TERM_SUPPRESSED = "term_suppressed"


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueCategory(StrEnum):
    TEXT_CORRECTION = "TEXT_CORRECTION"
    PUNCTUATION_CHARACTER = "PUNCTUATION_CHARACTER"
    PARAGRAPH_LAYOUT = "PARAGRAPH_LAYOUT"
    STRUCTURE_NUMBERING = "STRUCTURE_NUMBERING"
    CITATION_REFERENCE = "CITATION_REFERENCE"
```

```python
# backend/src/typofix_cn/domain/catalog.py
from dataclasses import dataclass
from .enums import IssueCategory, Severity


@dataclass(frozen=True)
class ErrorTypeDefinition:
    category: IssueCategory
    default_severity: Severity
    default_enabled: bool


def _definition(category: IssueCategory, severity: Severity, enabled: bool = True) -> ErrorTypeDefinition:
    return ErrorTypeDefinition(category, severity, enabled)


ERROR_TYPES = {
    "SPELLING_TYPO": _definition(IssueCategory.TEXT_CORRECTION, Severity.ERROR),
    "REPEATED_WORD": _definition(IssueCategory.TEXT_CORRECTION, Severity.WARNING),
    "TERM_INCONSISTENT": _definition(IssueCategory.TEXT_CORRECTION, Severity.INFO, False),
    "ABBREVIATION_UNEXPLAINED": _definition(IssueCategory.TEXT_CORRECTION, Severity.INFO, False),
    "PUNCTUATION_DUPLICATE": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.WARNING),
    "PUNCTUATION_UNPAIRED": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.ERROR),
    "PUNCTUATION_WIDTH_MISMATCH": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.WARNING),
    "PUNCTUATION_COMBINATION_INVALID": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.WARNING),
    "ELLIPSIS_OR_DASH_INVALID": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.WARNING),
    "PARAGRAPH_END_PUNCTUATION_MISSING": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.INFO),
    "WHITESPACE_REDUNDANT": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.WARNING),
    "FULLWIDTH_SPACE_INVALID": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.WARNING),
    "NUMBER_STYLE_INCONSISTENT": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.INFO),
    "DATE_FORMAT_SUSPECT": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.INFO),
    "NUMBER_UNIT_SPACING": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.INFO),
    "UNIT_STYLE_INCONSISTENT": _definition(IssueCategory.PUNCTUATION_CHARACTER, Severity.INFO),
    "FIRST_LINE_INDENT_MISSING": _definition(IssueCategory.PARAGRAPH_LAYOUT, Severity.WARNING),
    "FIRST_LINE_INDENT_INVALID": _definition(IssueCategory.PARAGRAPH_LAYOUT, Severity.WARNING),
    "MANUAL_INDENT_SPACES": _definition(IssueCategory.PARAGRAPH_LAYOUT, Severity.WARNING),
    "BODY_STYLE_OUTLIER": _definition(IssueCategory.PARAGRAPH_LAYOUT, Severity.INFO),
    "EXCESSIVE_EMPTY_PARAGRAPH": _definition(IssueCategory.PARAGRAPH_LAYOUT, Severity.INFO),
    "HEADING_END_PUNCTUATION": _definition(IssueCategory.STRUCTURE_NUMBERING, Severity.WARNING),
    "HEADING_NUMBER_INVALID": _definition(IssueCategory.STRUCTURE_NUMBERING, Severity.WARNING),
    "HEADING_LEVEL_JUMP": _definition(IssueCategory.STRUCTURE_NUMBERING, Severity.WARNING),
    "HEADING_STYLE_INCONSISTENT": _definition(IssueCategory.STRUCTURE_NUMBERING, Severity.INFO),
    "FIGURE_NUMBER_DUPLICATE_OR_GAP": _definition(IssueCategory.STRUCTURE_NUMBERING, Severity.WARNING),
    "TABLE_NUMBER_DUPLICATE_OR_GAP": _definition(IssueCategory.STRUCTURE_NUMBERING, Severity.WARNING),
    "CAPTION_STYLE_INCONSISTENT": _definition(IssueCategory.STRUCTURE_NUMBERING, Severity.INFO),
    "CROSS_REFERENCE_TARGET_MISSING": _definition(IssueCategory.STRUCTURE_NUMBERING, Severity.ERROR),
    "CITATION_TARGET_MISSING": _definition(IssueCategory.CITATION_REFERENCE, Severity.ERROR),
    "REFERENCE_NOT_CITED": _definition(IssueCategory.CITATION_REFERENCE, Severity.WARNING),
    "REFERENCE_NUMBER_DUPLICATE_OR_GAP": _definition(IssueCategory.CITATION_REFERENCE, Severity.WARNING),
    "REFERENCE_STYLE_INCONSISTENT": _definition(IssueCategory.CITATION_REFERENCE, Severity.INFO),
}
```

```python
# backend/src/typofix_cn/domain/locations.py
from pydantic import BaseModel, Field


class TableLocation(BaseModel):
    table_index: int = Field(ge=0)
    row_index: int = Field(ge=0)
    column_index: int = Field(ge=0)
    cell_paragraph_index: int = Field(ge=0)


class TextLocation(BaseModel):
    document_path: str
    region: str
    paragraph_index: int = Field(ge=0)
    sentence_index: int = Field(ge=0)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    table: TableLocation | None = None
```

```python
# backend/src/typofix_cn/domain/issues.py
import hashlib
import json
from pydantic import BaseModel, Field
from .enums import IssueCategory, IssueSource, IssueStatus, Severity
from .locations import TextLocation


class TermHit(BaseModel):
    library: str
    term: str
    start_offset: int
    end_offset: int


class Issue(BaseModel):
    issue_id: str
    source: IssueSource
    category: IssueCategory
    type_code: str
    severity: Severity
    status: IssueStatus = IssueStatus.ACTIONABLE
    location: TextLocation
    original: str
    suggestion: str | None = None
    message: str
    context: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    rule_code: str | None = None
    term_hits: list[TermHit] = Field(default_factory=list)

    @classmethod
    def create(cls, **values):
        identity = {
            key: values[key]
            for key in ("source", "type_code", "location", "original", "suggestion")
        }
        payload = json.dumps(identity, ensure_ascii=False, sort_keys=True, default=str)
        return cls(issue_id=hashlib.sha256(payload.encode()).hexdigest()[:20], **values)
```

Implement `Settings` with `Path` fields, `platformdirs.user_data_path("TypofixCN")` as the installed default, `TYPOFIX_` environment prefix, derived `jobs_dir`, `models_dir`, and `term_libraries_dir` properties, plus `ensure_directories()` that creates `default.txt` as UTF-8 only when absent. Define job enums and a minimal `JobManifest` in `domain/jobs.py` with `schema_version=1`, timestamps, mode, relative input paths, progress counters, status, and document failures.

- [ ] **Step 4: Install, lock and run the tests**

Run: `uv sync --extra dev`  
Expected: dependency resolution succeeds and creates `uv.lock`.

Run: `uv run pytest backend/tests/domain/test_issues.py backend/tests/test_config.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit the scaffold**

```powershell
git add pyproject.toml uv.lock .gitignore backend
git commit -m "build: scaffold Typofix core"
```

### Task 2: Extract supported DOCX content with stable locations

**Files:**
- Create: `backend/src/typofix_cn/documents/models.py`
- Create: `backend/src/typofix_cn/documents/roles.py`
- Create: `backend/src/typofix_cn/documents/docx_reader.py`
- Create: `backend/tests/documents/test_docx_reader.py`

- [ ] **Step 1: Write DOCX extraction tests**

```python
from docx import Document
from typofix_cn.documents.docx_reader import DocxReader


def test_reader_extracts_body_and_table_but_not_header(tmp_path) -> None:
    path = tmp_path / "论文.docx"
    document = Document()
    document.add_heading("第一章 绪论", level=1)
    paragraph = document.add_paragraph("这是正文。")
    paragraph.style = document.styles["Normal"]
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "表格文本。"
    document.sections[0].header.paragraphs[0].text = "页眉不检查"
    document.save(path)

    blocks = DocxReader().read(path, relative_path="论文.docx")

    assert [block.text for block in blocks] == ["第一章 绪论", "这是正文。", "表格文本。"]
    assert blocks[0].role == "heading"
    assert blocks[1].role == "body"
    assert blocks[2].region == "table_cell"
    assert blocks[2].table.row_index == 0
```

Add tests for text split across multiple Word runs, list paragraphs, blank paragraphs, nested table paragraphs, corrupt files, and non-DOCX ZIP files.

- [ ] **Step 2: Run the reader test and verify failure**

Run: `uv run pytest backend/tests/documents/test_docx_reader.py -v`  
Expected: FAIL because `DocxReader` does not exist.

- [ ] **Step 3: Implement extraction and paragraph roles**

```python
# backend/src/typofix_cn/documents/models.py
from pydantic import BaseModel
from typofix_cn.domain.locations import TableLocation


class ExtractedBlock(BaseModel):
    document_path: str
    region: str
    paragraph_index: int
    text: str
    role: str
    style_name: str | None
    first_line_indent_pt: float | None
    left_indent_pt: float | None
    alignment: str | None
    line_spacing: float | None
    space_before_pt: float | None
    space_after_pt: float | None
    table: TableLocation | None = None
```

Implement `DocxReader.read(path, relative_path)` with `python-docx`. Iterate body paragraphs and tables in XML document order; recursively visit tables inside cells while preventing duplicate cell traversal caused by merged cells. Concatenate `paragraph.runs` without losing character order. Resolve effective paragraph formatting from direct properties first and the paragraph style second. `roles.py` must classify headings from outline level or heading style, lists from numbering properties, table content from its region, and empty text as blank; all other paragraphs are body unless evidence is insufficient, in which case return unknown. Raise typed `InvalidDocxError`, `EncryptedDocxError`, or `UnsupportedDocxError`.

- [ ] **Step 4: Run focused and full Python tests**

Run: `uv run pytest backend/tests/documents/test_docx_reader.py -v`  
Expected: PASS.

Run: `uv run pytest backend/tests -v`  
Expected: PASS.

- [ ] **Step 5: Commit DOCX extraction**

```powershell
git add backend/src/typofix_cn/documents backend/tests/documents
git commit -m "feat: extract supported DOCX content"
```

### Task 3: Segment sentences and chunk long model inputs

**Files:**
- Create: `backend/src/typofix_cn/documents/sentences.py`
- Create: `backend/src/typofix_cn/documents/chunking.py`
- Create: `backend/tests/documents/test_sentences.py`
- Create: `backend/tests/documents/test_chunking.py`

- [ ] **Step 1: Write mapping and chunk overlap tests**

```python
from typofix_cn.documents.sentences import split_sentences
from typofix_cn.documents.chunking import chunk_sentence


def test_sentence_offsets_reference_original_paragraph() -> None:
    sentences = split_sentences("第一句。第二句！末句")
    assert [(item.text, item.start, item.end) for item in sentences] == [
        ("第一句。", 0, 4),
        ("第二句！", 4, 8),
        ("末句", 8, 10),
    ]


def test_long_sentence_chunks_overlap_without_losing_offsets() -> None:
    chunks = chunk_sentence("甲" * 20, max_chars=8, overlap=2)
    assert [(chunk.start, chunk.end) for chunk in chunks] == [(0, 8), (6, 14), (12, 20)]
    assert all(chunk.text == "甲" * (chunk.end - chunk.start) for chunk in chunks)
```

- [ ] **Step 2: Verify the tests fail**

Run: `uv run pytest backend/tests/documents/test_sentences.py backend/tests/documents/test_chunking.py -v`  
Expected: FAIL with missing modules.

- [ ] **Step 3: Implement sentence and chunk value objects**

```python
class SentenceSpan(BaseModel):
    index: int
    text: str
    start: int
    end: int


class TextChunk(BaseModel):
    text: str
    start: int
    end: int
```

Split after `。！？!?；;` while retaining terminal punctuation, treat paired closing quotes/brackets immediately after terminal punctuation as part of the sentence, and return remaining text as the last sentence. `chunk_sentence` must validate `0 <= overlap < max_chars`, advance by `max_chars - overlap`, and stop exactly at the source end. Add `deduplicate_findings()` keyed by source range, original, and suggestion so overlapping chunks do not duplicate corrections.

- [ ] **Step 4: Run the focused tests**

Run: `uv run pytest backend/tests/documents/test_sentences.py backend/tests/documents/test_chunking.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit sentence mapping**

```powershell
git add backend/src/typofix_cn/documents backend/tests/documents
git commit -m "feat: add sentence mapping and model chunking"
```

### Task 4: Implement editable text terminology libraries and exact suppression

**Files:**
- Create: `backend/src/typofix_cn/terms/models.py`
- Create: `backend/src/typofix_cn/terms/repository.py`
- Create: `backend/src/typofix_cn/terms/matcher.py`
- Create: `backend/tests/terms/test_repository.py`
- Create: `backend/tests/terms/test_matcher.py`

- [ ] **Step 1: Write terminology repository and suppression tests**

```python
from typofix_cn.terms.repository import TextTermRepository


def test_repository_reads_bom_comments_blanks_and_duplicates(tmp_path) -> None:
    root = tmp_path / "term-libraries"
    root.mkdir()
    (root / "default.txt").write_text(
        "\ufeff麒麟操作系统\n# 说明\n\nMacBERT\nMacBERT\n", encoding="utf-8"
    )
    repository = TextTermRepository(root)
    assert repository.load("default").terms == ["麒麟操作系统", "MacBERT"]


def test_add_term_is_idempotent_and_rejects_path_names(tmp_path) -> None:
    repository = TextTermRepository(tmp_path)
    repository.create("default")
    repository.add("default", "自然语言处理")
    repository.add("default", "自然语言处理")
    assert repository.load("default").terms == ["自然语言处理"]
    with pytest.raises(InvalidLibraryName):
        repository.create("../escape")
```

```python
def test_only_model_typo_fully_inside_term_is_suppressed(model_issue, rule_issue) -> None:
    matcher = TermMatcher({"default": ["麒麟操作系统"]})
    issues = matcher.apply("支持麒麟操作系统部署", [model_issue, rule_issue])
    assert issues[0].status == "term_suppressed"
    assert issues[1].status == "actionable"
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest backend/tests/terms -v`  
Expected: FAIL because repository and matcher do not exist.

- [ ] **Step 3: Implement atomic files, NFC matching and overlap tracking**

```python
class TermLibrary(BaseModel):
    name: str
    terms: list[str]
    modified_at: datetime
    content_sha256: str


_VALID_NAME = re.compile(r"^[\w\-\u4e00-\u9fff]{1,80}$")
```

Use `utf-8-sig` for reads and UTF-8 with `\n` for writes. Ignore blank and comment lines after trimming. Write to a temporary sibling, flush, then `os.replace`. `add` rejects empty strings, newlines, and values over 100 characters. `delete` removes an exact term. The matcher normalizes original text and terms with NFC, performs case-sensitive substring matching, preserves normalized-to-original offsets, records every overlap, and changes status only when a `SPELLING_TYPO` source range is fully covered.

- [ ] **Step 4: Run terminology and domain tests**

Run: `uv run pytest backend/tests/terms backend/tests/domain -v`  
Expected: PASS.

- [ ] **Step 5: Commit terminology support**

```powershell
git add backend/src/typofix_cn/terms backend/tests/terms
git commit -m "feat: add text terminology libraries"
```

### Task 5: Add the rule protocol and high-confidence text rules

**Files:**
- Create: `backend/src/typofix_cn/rules/base.py`
- Create: `backend/src/typofix_cn/rules/registry.py`
- Create: `backend/src/typofix_cn/rules/text_rules.py`
- Create: `backend/src/typofix_cn/rules/punctuation_rules.py`
- Create: `backend/tests/rules/test_text_rules.py`
- Create: `backend/tests/rules/test_punctuation_rules.py`

- [ ] **Step 1: Write one parameterized contract test per enabled text rule**

```python
@pytest.mark.parametrize(
    ("text", "type_code"),
    [
        ("研究研究表明", "REPEATED_WORD"),
        ("结果。。如下", "PUNCTUATION_DUPLICATE"),
        ("采用（测试方法。", "PUNCTUATION_UNPAIRED"),
        ("中文句子,使用半角逗号。", "PUNCTUATION_WIDTH_MISMATCH"),
        ("这里使用" + "." * 6 + "表示省略", "ELLIPSIS_OR_DASH_INVALID"),
        ("中文  之间有空格。", "WHITESPACE_REDUNDANT"),
        ("正文中有　全角空格。", "FULLWIDTH_SPACE_INVALID"),
    ],
)
def test_rule_reports_expected_subtype(rule_registry, text, type_code) -> None:
    issues = rule_registry.check(make_rule_context(text))
    assert type_code in {issue.type_code for issue in issues}
    assert all(issue.category in {"TEXT_CORRECTION", "PUNCTUATION_CHARACTER"} for issue in issues)
```

Add negative tests for legitimate `？！`, nested Chinese quote pairs, English-only sentences, decimal numbers, URLs, and repeated single-character words that are valid Chinese expressions.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run pytest backend/tests/rules/test_text_rules.py backend/tests/rules/test_punctuation_rules.py -v`  
Expected: FAIL with missing rule registry.

- [ ] **Step 3: Implement the protocol, registry and rules**

```python
class RuleContext(BaseModel):
    block: ExtractedBlock
    sentence: SentenceSpan


class Rule(Protocol):
    code: str
    default_severity: Severity
    default_enabled: bool

    def check(self, context: RuleContext) -> list[Issue]:
        raise RuntimeError("Rule protocol method must be implemented")


class RuleRegistry:
    def __init__(self, rules: Sequence[Rule]) -> None:
        self._rules = tuple(rules)

    def check(self, context: RuleContext) -> list[Issue]:
        return [issue for rule in self._rules if rule.default_enabled for issue in rule.check(context)]
```

Each rule must create exact left-closed/right-open character ranges relative to the sentence and use the five parent categories. Build paired-symbol checking with a stack, explicit accepted Chinese punctuation combinations, and URL/email/decimal protection before half-width punctuation checks. Mark paragraph-ending punctuation as `INFO` and skip headings, list items, table cells, blank paragraphs, URLs, equations, and paragraphs under 12 Chinese characters.

- [ ] **Step 4: Run rule tests and coverage**

Run: `uv run pytest backend/tests/rules -v --cov=typofix_cn.rules --cov-report=term-missing`  
Expected: PASS and every enabled rule has positive and negative coverage.

- [ ] **Step 5: Commit text rules**

```powershell
git add backend/src/typofix_cn/rules backend/tests/rules
git commit -m "feat: add text and punctuation rules"
```

### Task 6: Add paragraph layout and style-outlier rules

**Files:**
- Create: `backend/src/typofix_cn/rules/layout_rules.py`
- Create: `backend/src/typofix_cn/rules/style_profile.py`
- Create: `backend/tests/rules/test_layout_rules.py`
- Modify: `backend/src/typofix_cn/rules/registry.py`

- [ ] **Step 1: Write layout behavior tests**

```python
def test_body_without_indent_is_reported(body_block) -> None:
    body_block.first_line_indent_pt = 0
    issues = FirstLineIndentRule().check(block_context(body_block))
    assert [issue.type_code for issue in issues] == ["FIRST_LINE_INDENT_MISSING"]


def test_heading_list_and_table_do_not_require_indent(heading_block, list_block, table_block) -> None:
    rule = FirstLineIndentRule()
    assert rule.check(block_context(heading_block)) == []
    assert rule.check(block_context(list_block)) == []
    assert rule.check(block_context(table_block)) == []


def test_single_body_style_outlier_is_reported() -> None:
    profile = build_style_profile([body(font_size=12)] * 9 + [body(font_size=18)])
    assert profile.outlier_indexes == {9}
```

Add tests for two ideographic spaces at paragraph start, valid two-character Word indentation, inherited style indentation, intentionally blank single separators, and three consecutive blank paragraphs.

- [ ] **Step 2: Verify tests fail**

Run: `uv run pytest backend/tests/rules/test_layout_rules.py -v`  
Expected: FAIL because layout rules do not exist.

- [ ] **Step 3: Implement conservative layout rules**

Use effective paragraph formatting extracted by `DocxReader`. Treat a body paragraph as missing indentation when effective first-line indent is absent/zero and it does not begin with manual spaces. Emit `MANUAL_INDENT_SPACES` for leading ASCII or ideographic spaces and do not also emit `FIRST_LINE_INDENT_MISSING`. Compare nonzero indent to the document's dominant body indent, accepting a tolerance of 0.25 em. Build a style signature from font family, size, alignment, line spacing, and paragraph spacing; only report an outlier when at least five comparable body paragraphs exist and one signature represents at least 70% of them. Emit `EXCESSIVE_EMPTY_PARAGRAPH` only for the third and later consecutive blank paragraph.

- [ ] **Step 4: Run all rule tests**

Run: `uv run pytest backend/tests/rules -v`  
Expected: PASS.

- [ ] **Step 5: Commit layout rules**

```powershell
git add backend/src/typofix_cn/rules backend/tests/rules
git commit -m "feat: add paragraph layout rules"
```

### Task 7: Add heading, figure/table and numeric-reference consistency rules

**Files:**
- Create: `backend/src/typofix_cn/rules/structure_rules.py`
- Create: `backend/src/typofix_cn/rules/reference_rules.py`
- Create: `backend/tests/rules/test_structure_rules.py`
- Create: `backend/tests/rules/test_reference_rules.py`
- Modify: `backend/src/typofix_cn/rules/registry.py`

- [ ] **Step 1: Write document-level rule tests**

```python
def test_heading_level_jump_and_terminal_punctuation_are_reported() -> None:
    blocks = [heading("第一章 绪论", 1), heading("1.1.1 方法。", 3)]
    codes = {issue.type_code for issue in StructureRuleSet().check_document(blocks)}
    assert codes == {"HEADING_LEVEL_JUMP", "HEADING_END_PUNCTUATION"}


def test_missing_figure_and_reference_targets_are_reported() -> None:
    blocks = [body("如图2.3所示，相关结论见文献[4]。"), body("参考文献"), body("[1] 作者. 题名.")]
    codes = {issue.type_code for issue in AcademicReferenceRuleSet().check_document(blocks)}
    assert "CROSS_REFERENCE_TARGET_MISSING" in codes
    assert "CITATION_TARGET_MISSING" in codes
```

Add negative tests for valid heading sequences, appendix identifiers, ranges such as `[1-3]`, multiple citations `[1, 3]`, valid figure/table captions, and author-year citations that must be left unchanged.

- [ ] **Step 2: Verify document-level tests fail**

Run: `uv run pytest backend/tests/rules/test_structure_rules.py backend/tests/rules/test_reference_rules.py -v`  
Expected: FAIL with missing rule sets.

- [ ] **Step 3: Implement high-confidence document scans**

Detect heading levels from paragraph roles and parsed numbering; report punctuation, level jumps, mixed numbering syntax within the same hierarchy, and duplicate/gapped numeric figure/table captions. Build target sets from captions matching `图N(.N)*` and `表N(.N)*`, then report only explicit textual references with no target. Detect a `参考文献` heading, parse numeric entries beginning with `[N]`, and compare them with bracketed numeric citations before that section. Do not validate author-year references or the full bibliographic field grammar. Mark unused references and numeric gaps as `WARNING`, missing targets as `ERROR`, and formatting inconsistency as `INFO`.

- [ ] **Step 4: Run the complete rule suite**

Run: `uv run pytest backend/tests/rules -v`  
Expected: PASS.

- [ ] **Step 5: Commit academic consistency rules**

```powershell
git add backend/src/typofix_cn/rules backend/tests/rules
git commit -m "feat: add academic structure rules"
```

### Task 8: Add the Corrector protocol, deterministic fake and lazy MacBERT adapter

**Files:**
- Create: `backend/src/typofix_cn/correctors/base.py`
- Create: `backend/src/typofix_cn/correctors/fake.py`
- Create: `backend/src/typofix_cn/correctors/macbert.py`
- Create: `backend/tests/correctors/test_fake.py`
- Create: `backend/tests/correctors/test_macbert.py`
- Create: `backend/tests/correctors/test_macbert_smoke.py`

- [ ] **Step 1: Write adapter contract and lazy-loading tests**

```python
def test_fake_corrector_returns_source_relative_findings() -> None:
    corrector = FakeCorrector({"今天新情很好": [("新", "心", 2)]})
    result = corrector.correct([CorrectionInput(key="s1", text="今天新情很好")])
    assert result[0].findings[0].model_dump() == {
        "start": 2,
        "end": 3,
        "original": "新",
        "suggestion": "心",
        "confidence": None,
    }


def test_macbert_loads_backend_once(monkeypatch, tmp_path) -> None:
    loader = Mock(return_value=stub_backend([{"source": "今天新情很好", "errors": [("新", "心", 2)]}]))
    corrector = MacBertCorrector(tmp_path, loader=loader)
    corrector.correct([CorrectionInput(key="a", text="今天新情很好")])
    corrector.correct([CorrectionInput(key="b", text="今天新情很好")])
    loader.assert_called_once()
```

- [ ] **Step 2: Run adapter tests and verify failure**

Run: `uv run pytest backend/tests/correctors/test_fake.py backend/tests/correctors/test_macbert.py -v`  
Expected: FAIL because corrector modules do not exist.

- [ ] **Step 3: Implement the adapters**

```python
class CorrectionInput(BaseModel):
    key: str
    text: str


class CorrectionFinding(BaseModel):
    start: int
    end: int
    original: str
    suggestion: str
    confidence: float | None = None


class Corrector(Protocol):
    def correct(self, inputs: Sequence[CorrectionInput]) -> list[CorrectionResult]:
        raise RuntimeError("Corrector protocol method must be implemented")
```

`MacBertCorrector` lazily imports `pycorrector`, instantiates `pycorrector.MacBertCorrector(model_dir_or_name)`, forces the underlying torch model to CPU/eval where exposed, and wraps calls in `torch.inference_mode()`. Use `correct_batch` and validate every returned error against the source substring before accepting it. Raise `ModelDependencyMissing`, `ModelNotReady`, or `ModelInferenceError` with safe messages. The smoke test must be marked `@pytest.mark.model` and skip unless `TYPOFIX_RUN_MODEL_TESTS=1`.

- [ ] **Step 4: Run fake/unit tests, then optional real smoke**

Run: `uv run pytest backend/tests/correctors -v -m "not model"`  
Expected: PASS without downloading model weights.

Run when weights are available: `$env:TYPOFIX_RUN_MODEL_TESTS='1'; uv run --extra model pytest backend/tests/correctors/test_macbert_smoke.py -v -m model`  
Expected: `今天新情很好` produces a correction covering `新` with suggestion `心`.

- [ ] **Step 5: Commit corrector adapters**

```powershell
git add backend/src/typofix_cn/correctors backend/tests/correctors pyproject.toml uv.lock
git commit -m "feat: add MacBERT corrector adapter"
```

### Task 9: Compose extraction, model, rules and terminology into one analysis service

**Files:**
- Create: `backend/src/typofix_cn/application/analyze.py`
- Create: `backend/src/typofix_cn/domain/reports.py`
- Create: `backend/tests/application/test_analyze.py`

- [ ] **Step 1: Write an end-to-end core test with a fake model**

```python
def test_analysis_combines_model_rules_and_term_status(sample_docx, tmp_path) -> None:
    service = build_analysis_service(
        corrector=FakeCorrector({"支持麒麟操做系统。": [("做", "作", 5)]}),
        term_libraries={"default": ["麒麟操做系统"]},
    )
    report = service.analyze([sample_docx], selected_libraries=["default"])
    typo = next(issue for issue in report.issues if issue.type_code == "SPELLING_TYPO")
    assert typo.status == "term_suppressed"
    assert typo.location.paragraph_index == 0
    assert report.summary.term_suppressed == 1
    assert report.summary.actionable >= 1
```

Add a test proving long-chunk duplicate findings become one issue and a test proving rules-only mode never calls the corrector.

- [ ] **Step 2: Verify the application test fails**

Run: `uv run pytest backend/tests/application/test_analyze.py -v`  
Expected: FAIL because `AnalysisService` and report models do not exist.

- [ ] **Step 3: Implement report models and analysis orchestration**

```python
class ReportSummary(BaseModel):
    total: int
    actionable: int
    term_suppressed: int
    by_category: dict[IssueCategory, int]
    by_source: dict[IssueSource, int]


class AnalysisReport(BaseModel):
    schema_version: Literal[1] = 1
    job_id: str
    mode: Literal["full", "rules_only"]
    documents: list[DocumentResult]
    issues: list[Issue]
    summary: ReportSummary
```

Add report metadata fields for model identifier, model adapter version, rule catalog version, selected terminology library names/content hashes, Python/torch/platform versions, creation time, and document failures. `AnalysisService` must read documents, segment blocks, build style profiles, run document-level and sentence-level rules, batch model chunks, convert chunk offsets through sentence and paragraph offsets, deduplicate findings, create model Issues, apply selected term libraries, and calculate summary counts. Accept progress callbacks at document and phase boundaries. Per-document extraction failure becomes a `DocumentFailure` while other files continue. Model failure in full mode fails the whole job.

- [ ] **Step 4: Run all core tests**

Run: `uv run pytest backend/tests/application backend/tests/documents backend/tests/rules backend/tests/terms backend/tests/correctors -v -m "not model"`  
Expected: PASS.

- [ ] **Step 5: Commit the shared analysis use case**

```powershell
git add backend/src/typofix_cn/application backend/src/typofix_cn/domain backend/tests/application
git commit -m "feat: compose document analysis pipeline"
```

### Task 10: Persist jobs and generate versioned JSON and offline HTML reports

**Files:**
- Create: `backend/src/typofix_cn/jobs/repository.py`
- Create: `backend/src/typofix_cn/reports/json_report.py`
- Create: `backend/src/typofix_cn/reports/html_report.py`
- Create: `backend/src/typofix_cn/reports/templates/report.html.j2`
- Create: `backend/tests/jobs/test_repository.py`
- Create: `backend/tests/reports/test_reports.py`

- [ ] **Step 1: Write atomic job and self-contained report tests**

```python
def test_running_jobs_are_marked_interrupted_on_startup(tmp_path) -> None:
    repository = JobRepository(tmp_path)
    manifest = repository.create(["论文.docx"], mode="rules_only", libraries=[])
    repository.update(manifest.model_copy(update={"status": "running"}))
    repository.recover_interrupted()
    assert repository.get(manifest.job_id).status == "interrupted"


def test_report_outputs_versioned_json_and_safe_offline_html(tmp_path, analysis_report) -> None:
    JsonReportWriter().write(analysis_report, tmp_path / "report.json")
    HtmlReportWriter().write(analysis_report, tmp_path / "report.html")
    payload = json.loads((tmp_path / "report.json").read_text("utf-8"))
    html = (tmp_path / "report.html").read_text("utf-8")
    assert payload["schema_version"] == 1
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "fetch(" not in html
```

- [ ] **Step 2: Verify persistence/report tests fail**

Run: `uv run pytest backend/tests/jobs backend/tests/reports -v`  
Expected: FAIL with missing repositories and writers.

- [ ] **Step 3: Implement filesystem jobs and report writers**

Create UUIDv7-compatible sortable job IDs or use UUID4 plus `created_at` sorting. Copy validated inputs beneath `jobs/<id>/input` while preserving safe relative paths. Write `manifest.json`, `report.json`, and `report.html` through one reusable `atomic_write_text` helper. Scan manifests for recent jobs; invalid manifests are logged and omitted from the list rather than crashing the app. HTML must embed escaped report JSON, include local CSS and filtering JavaScript, expose five category labels, and contain no remote URL or network call.

- [ ] **Step 4: Run persistence and report tests**

Run: `uv run pytest backend/tests/jobs backend/tests/reports -v`  
Expected: PASS.

- [ ] **Step 5: Commit job and report persistence**

```powershell
git add backend/src/typofix_cn/jobs backend/src/typofix_cn/reports backend/tests/jobs backend/tests/reports
git commit -m "feat: persist jobs and offline reports"
```

### Task 11: Expose the shared core through Typer CLI

**Files:**
- Create: `cli/src/typofix_cli/__init__.py`
- Create: `cli/src/typofix_cli/main.py`
- Create: `cli/src/typofix_cli/container.py`
- Create: `cli/tests/test_cli.py`

- [ ] **Step 1: Write CLI contract tests**

```python
from typer.testing import CliRunner
from typofix_cli.main import app


def test_rules_only_directory_check_creates_both_reports(tmp_path, sample_docx) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["check", str(sample_docx.parent), "--rules-only", "--data-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "report.json" in result.stdout
    assert "report.html" in result.stdout


def test_term_add_is_idempotent(tmp_path) -> None:
    runner = CliRunner()
    args = ["terms", "add", "default", "麒麟操作系统", "--data-dir", str(tmp_path)]
    assert runner.invoke(app, args).exit_code == 0
    assert runner.invoke(app, args).exit_code == 0
```

Add tests for a single file, recursive folders, multiple `--term-lib`, missing model, corrupt input, `terms list`, `model download`, and `serve` option parsing. Issues in a valid report must leave exit code zero.

- [ ] **Step 2: Verify CLI tests fail**

Run: `uv run pytest cli/tests/test_cli.py -v`  
Expected: FAIL because the CLI package does not exist.

- [ ] **Step 3: Implement `check`, `serve`, `terms` and `model` commands**

```python
app = typer.Typer(no_args_is_help=True)
terms_app = typer.Typer(no_args_is_help=True)
model_app = typer.Typer(no_args_is_help=True)
app.add_typer(terms_app, name="terms")
app.add_typer(model_app, name="model")


@app.command()
def check(
    paths: list[Path],
    term_lib: list[str] = typer.Option([], "--term-lib"),
    rules_only: bool = False,
    data_dir: Path | None = None,
    verbose: bool = False,
) -> None:
    container = build_container(data_dir=data_dir, include_model=not rules_only)
    outcome = container.run_check(
        paths=paths,
        selected_libraries=term_lib,
        mode="rules_only" if rules_only else "full",
    )
    typer.echo(f"JSON: {outcome.json_path}")
    typer.echo(f"HTML: {outcome.html_path}")
    if verbose:
        for issue in outcome.report.issues:
            typer.echo(f"{issue.category.value}/{issue.type_code}: {issue.message}")
```

Define `CliContainer.run_check()` in `cli/src/typofix_cli/container.py` as the thin composition of `JobRepository`, `AnalysisService`, and both report writers; CLI code must not reimplement analysis. Return a `CheckOutcome(report, json_path, html_path)` value object. `model download` must call `huggingface_hub.snapshot_download` only after the model extra is installed and write to `settings.models_dir`. Print safe actionable errors and exit with code 2 for input/config/model failures.

- [ ] **Step 4: Run CLI and all Python tests**

Run: `uv run pytest backend/tests cli/tests -v -m "not model"`  
Expected: PASS.

Run: `uv run typofix --help`  
Expected: help lists `check`, `serve`, `terms`, and `model`.

- [ ] **Step 5: Commit the CLI**

```powershell
git add cli pyproject.toml uv.lock
git commit -m "feat: add Typofix CLI"
```

## Phase 2: FastAPI and React Web application

### Task 12: Add the FastAPI application, job endpoints and single-worker queue

**Files:**
- Create: `backend/src/typofix_cn/jobs/queue.py`
- Create: `backend/src/typofix_cn/api/app.py`
- Create: `backend/src/typofix_cn/api/dependencies.py`
- Create: `backend/src/typofix_cn/api/errors.py`
- Create: `backend/src/typofix_cn/api/routes/jobs.py`
- Create: `backend/tests/api/test_jobs.py`
- Create: `backend/tests/jobs/test_queue.py`

- [ ] **Step 1: Write API and queue lifecycle tests**

```python
def test_create_rules_only_job_and_poll_to_completion(client, sample_docx) -> None:
    with sample_docx.open("rb") as stream:
        response = client.post(
            "/api/v1/jobs",
            data={"mode": "rules_only", "term_libraries": "default"},
            files=[("files", ("论文.docx", stream, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
        )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    finished = poll_test_job(client, job_id)
    assert finished["status"] in {"completed", "completed_with_document_failures"}


def test_queue_runs_only_one_analysis_at_a_time(tmp_path) -> None:
    probe = ConcurrencyProbe()
    queue = JobQueue(worker=probe.run)
    queue.start()
    queue.submit("a")
    queue.submit("b")
    probe.wait_for_all()
    assert probe.max_concurrency == 1
```

Add tests for recent jobs, report/download endpoints, progress fields, per-document failure, model-not-ready HTTP error, upload count/size limits, unsafe relative paths, and restart recovery.

- [ ] **Step 2: Verify API tests fail**

Run: `uv run pytest backend/tests/api/test_jobs.py backend/tests/jobs/test_queue.py -v`  
Expected: FAIL because the app and queue do not exist.

- [ ] **Step 3: Implement app lifespan, queue and `/api/v1/jobs` routes**

Use FastAPI lifespan to ensure data directories, recover interrupted manifests, start one daemon worker thread, and stop it cleanly. Endpoints:

```text
POST /api/v1/jobs
GET  /api/v1/jobs
GET  /api/v1/jobs/{job_id}
GET  /api/v1/jobs/{job_id}/report
GET  /api/v1/jobs/{job_id}/report.json
GET  /api/v1/jobs/{job_id}/report.html
```

Validate MIME, `.docx`, OOXML ZIP structure, configurable count, upload bytes, and expanded ZIP bytes before queue submission. Map typed domain failures to stable API error codes. Log exceptions server-side; return no tracebacks. Update manifest progress after every document and phase.

- [ ] **Step 4: Run API and Python test suites**

Run: `uv run pytest backend/tests cli/tests -v -m "not model"`  
Expected: PASS.

- [ ] **Step 5: Commit the job API**

```powershell
git add backend/src/typofix_cn/api backend/src/typofix_cn/jobs backend/tests/api backend/tests/jobs
git commit -m "feat: add queued job API"
```

### Task 13: Add terminology APIs and persisted report rematching

**Files:**
- Create: `backend/src/typofix_cn/application/rematch.py`
- Create: `backend/src/typofix_cn/api/routes/terms.py`
- Create: `backend/tests/api/test_terms.py`
- Create: `backend/tests/application/test_rematch.py`
- Modify: `backend/src/typofix_cn/api/app.py`

- [ ] **Step 1: Write terminology management and no-model-rematch tests**

```python
def test_add_selected_text_rematches_job_without_model_call(client, completed_job, model_probe) -> None:
    response = client.post(
        "/api/v1/term-libraries/default/terms",
        json={"term": "麒麟操作系统", "rematch_job_id": completed_job.job_id},
    )
    assert response.status_code == 200
    assert response.json()["report_summary"]["term_suppressed"] == 1
    assert model_probe.calls == 0


def test_invalid_library_name_does_not_escape_root(client) -> None:
    response = client.post("/api/v1/term-libraries", json={"name": "../outside"})
    assert response.status_code == 422
```

Add create/list/detail/search/add/delete tests, exact case-sensitive terms, 100-character limit, external file edit plus rematch, and stable issue IDs before/after rematch.

- [ ] **Step 2: Verify tests fail**

Run: `uv run pytest backend/tests/api/test_terms.py backend/tests/application/test_rematch.py -v`  
Expected: FAIL because term routes and rematch use case do not exist.

- [ ] **Step 3: Implement terminology routes and `RematchService`**

```text
GET    /api/v1/term-libraries
POST   /api/v1/term-libraries
GET    /api/v1/term-libraries/{name}
GET    /api/v1/term-libraries/{name}/download
POST   /api/v1/term-libraries/{name}/terms
DELETE /api/v1/term-libraries/{name}/terms
POST   /api/v1/jobs/{job_id}/rematch
```

`RematchService` loads the existing schema-1 report, restores model issues to actionable with empty term hits, reloads selected libraries, reapplies `TermMatcher`, recalculates summary, and atomically rewrites JSON and HTML. Reject rematch of incomplete or incompatible reports. The service must have no Corrector dependency.

- [ ] **Step 4: Run API/application tests**

Run: `uv run pytest backend/tests/api backend/tests/application -v`  
Expected: PASS.

- [ ] **Step 5: Commit terminology APIs**

```powershell
git add backend/src/typofix_cn/application backend/src/typofix_cn/api backend/tests/api backend/tests/application
git commit -m "feat: add terminology management and rematching"
```

### Task 14: Scaffold React and implement upload, folder selection and progress

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/pages/CheckPage.tsx`
- Create: `frontend/src/components/FilePicker.tsx`
- Create: `frontend/src/components/JobProgress.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/tests/CheckPage.test.tsx`
- Create: `frontend/tests/mocks.ts`

- [ ] **Step 1: Write upload workflow component tests**

```tsx
it("uploads files with selected terminology libraries and shows progress", async () => {
  server.use(mockLibraries(["default", "computer-science"]), mockQueuedJob("job-1"));
  render(<CheckPage />);
  await userEvent.upload(screen.getByLabelText("上传文件"), makeDocxFile("论文.docx"));
  await userEvent.click(screen.getByLabelText("default"));
  await userEvent.click(screen.getByRole("button", { name: "开始校验" }));
  expect(await screen.findByText("正在校验"))toBeInTheDocument();
  expect(lastJobRequest()).toMatchObject({ mode: "full", termLibraries: ["default"] });
});
```

Add tests for folder relative paths, ignored non-DOCX display, rules-only mode, disabled submit with no files, safe API error copy, and navigation when polling reaches completion. Implement `mockLibraries`, `mockQueuedJob`, `makeDocxFile`, and request-capture helpers in `frontend/tests/mocks.ts` using MSW; extend that file in Tasks 15 and 16 for report and history responses.

- [ ] **Step 2: Install frontend test tooling and verify the test fails**

Run: `npm install` in `frontend` after defining React/Vite/runtime dependencies and Vitest, jsdom, MSW, Testing Library, Playwright, ESLint, and TypeScript dev dependencies.  
Expected: `package-lock.json` is created.

Run: `npm test -- --run tests/CheckPage.test.tsx`  
Expected: FAIL because the page is not implemented.

- [ ] **Step 3: Implement typed API client and upload page**

```ts
export type IssueCategory =
  | "TEXT_CORRECTION"
  | "PUNCTUATION_CHARACTER"
  | "PARAGRAPH_LAYOUT"
  | "STRUCTURE_NUMBERING"
  | "CITATION_REFERENCE";

export interface JobSummary {
  jobId: string;
  status: "queued" | "running" | "completed" | "completed_with_document_failures" | "failed" | "interrupted";
  processedDocuments: number;
  totalDocuments: number;
  phase: string;
}
```

Use separate file and folder inputs; set `webkitdirectory` through a typed ref for folder selection. Send `webkitRelativePath` in a parallel relative-path form field. Show selected `.docx` files only, selected terminology libraries, full/rules-only mode, upload progress, job progress, partial failures, and user-safe errors. Poll no faster than once per second and stop on terminal status or unmount.

- [ ] **Step 4: Run frontend tests and production build**

Run in `frontend`: `npm test -- --run`  
Expected: PASS.

Run in `frontend`: `npm run build`  
Expected: TypeScript and Vite build succeed.

- [ ] **Step 5: Commit frontend foundation**

```powershell
git add frontend
git commit -m "feat: add Web upload workflow"
```

### Task 15: Implement the report workbench, parent filters and selection-to-term flow

**Files:**
- Create: `frontend/src/pages/ReportPage.tsx`
- Create: `frontend/src/components/ReportSummary.tsx`
- Create: `frontend/src/components/IssueFilters.tsx`
- Create: `frontend/src/components/IssueList.tsx`
- Create: `frontend/src/components/IssueContext.tsx`
- Create: `frontend/src/components/AddTermDialog.tsx`
- Create: `frontend/tests/ReportPage.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/types.ts`

- [ ] **Step 1: Write workbench behavior tests**

```tsx
it("shows only parent categories and filters suppressed model findings", async () => {
  server.use(mockReport(reportWithActionableAndSuppressedIssues()));
  render(<ReportPage jobId="job-1" />);
  expect(await screen.findByText("文字纠错"))toBeInTheDocument();
  expect(screen.queryByText("SPELLING_TYPO")).not.toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText("状态"), "term_suppressed");
  expect(screen.getAllByTestId("issue-row")).toHaveLength(1);
});


it("adds selected context to a library and refreshes the report", async () => {
  server.use(mockReport(reportWithTypo()), mockAddTermAndRematchedReport());
  render(<ReportPage jobId="job-1" />);
  selectTextWithin(screen.getByTestId("issue-context"), "麒麟操作系统");
  await userEvent.click(screen.getByRole("button", { name: "添加为术语" }));
  await userEvent.selectOptions(screen.getByLabelText("目标术语库"), "default");
  await userEvent.click(screen.getByRole("button", { name: "确认添加" }));
  expect(await screen.findByText("已由术语库豁免"))toBeInTheDocument();
});
```

Add tests for category/document/source/status combinations, summary counts, context range highlighting, no cross-paragraph selection, 100-character limit, report downloads, and partial document failures.

- [ ] **Step 2: Verify workbench tests fail**

Run in `frontend`: `npm test -- --run tests/ReportPage.test.tsx`  
Expected: FAIL because report components do not exist.

- [ ] **Step 3: Implement report types and components**

Map only parent codes to these labels: 文字纠错、标点与字符、段落与版式、结构与编号、引用与参考文献. Keep `typeCode` in TypeScript for data fidelity but never render it in normal UI. Use a semantic `<mark>` around the exact error span. On pointer/keyboard selection, confirm the Range start/end are inside the same context container, extract selected text, and open the library dialog. POST the term with `rematch_job_id`, replace the local report with the response, and preserve active filters when possible.

- [ ] **Step 4: Run frontend tests and build**

Run in `frontend`: `npm test -- --run`  
Expected: PASS.

Run in `frontend`: `npm run build`  
Expected: PASS.

- [ ] **Step 5: Commit the report workbench**

```powershell
git add frontend
git commit -m "feat: add interactive report workbench"
```

### Task 16: Implement terminology management and recent-job pages

**Files:**
- Create: `frontend/src/pages/TermsPage.tsx`
- Create: `frontend/src/pages/RecentJobsPage.tsx`
- Create: `frontend/src/components/TermLibraryList.tsx`
- Create: `frontend/src/components/TermEditor.tsx`
- Create: `frontend/tests/TermsPage.test.tsx`
- Create: `frontend/tests/RecentJobsPage.test.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write management page tests**

```tsx
it("creates a library and edits exact text terms", async () => {
  server.use(mockEmptyLibraries(), mockCreateLibrary(), mockAddAndDeleteTerm());
  render(<TermsPage />);
  await userEvent.click(screen.getByRole("button", { name: "新建术语库" }));
  await userEvent.type(screen.getByLabelText("术语库名称"), "computer-science");
  await userEvent.click(screen.getByRole("button", { name: "创建" }));
  await userEvent.type(screen.getByLabelText("添加术语"), "MacBERT");
  await userEvent.click(screen.getByRole("button", { name: "添加" }));
  expect(await screen.findByText("MacBERT"))toBeInTheDocument();
});


it("reopens a completed recent job", async () => {
  server.use(mockRecentJobs([{ jobId: "job-1", status: "completed" }]));
  render(<RecentJobsPage />);
  await userEvent.click(await screen.findByRole("link", { name: "查看报告" }));
  expect(currentRoute()).toBe("/jobs/job-1");
});
```

- [ ] **Step 2: Verify page tests fail**

Run in `frontend`: `npm test -- --run tests/TermsPage.test.tsx tests/RecentJobsPage.test.tsx`  
Expected: FAIL because pages do not exist.

- [ ] **Step 3: Implement simple routing and pages**

Use React Router routes `/`, `/jobs`, `/jobs/:jobId`, and `/terms`. Show library path, count, modified time, search, exact add/delete, TXT download, and a manual reload action. Show recent job creation time, status, document count, problem counts when available, reopen link, and safe failure summary. Do not add user accounts, remote sharing, or a visual rules editor.

- [ ] **Step 4: Run frontend quality gates**

Run in `frontend`: `npm run lint`  
Expected: PASS.

Run in `frontend`: `npm test -- --run`  
Expected: PASS.

Run in `frontend`: `npm run build`  
Expected: PASS.

- [ ] **Step 5: Commit terminology and history UI**

```powershell
git add frontend
git commit -m "feat: add terminology and history pages"
```

## Phase 3: Integrated delivery and platform evidence

### Task 17: Serve the built SPA, add acceptance tests, documentation and platform smoke scripts

**Files:**
- Modify: `backend/src/typofix_cn/api/app.py`
- Create: `backend/tests/integration/test_web_cli_equivalence.py`
- Create: `frontend/e2e/mvp.spec.ts`
- Create: `scripts/smoke.ps1`
- Create: `scripts/smoke.sh`
- Create: `scripts/benchmark.py`
- Create: `README.md`
- Create: `docs/deployment.md`
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write the Web/CLI equivalence integration test**

```python
def test_web_and_cli_emit_equivalent_issue_records(app_client, cli_runner, sample_corpus, tmp_path) -> None:
    api_report = run_rules_only_api_job(app_client, sample_corpus)
    cli_report = run_rules_only_cli_job(cli_runner, sample_corpus, tmp_path)
    normalize = lambda report: sorted(
        (item["source"], item["category"], item["type_code"], item["location"], item["original"], item["suggestion"])
        for item in report["issues"]
    )
    assert normalize(api_report) == normalize(cli_report)
```

Write a Playwright test that uploads a folder containing two valid DOCX files and one corrupt DOCX, selects two libraries, completes with document failures, filters a suppressed model issue, adds a selected term, and downloads both reports. Use a fake corrector injected by the test server so the test is deterministic.

- [ ] **Step 2: Run acceptance tests and verify missing integration behavior**

Run: `uv run pytest backend/tests/integration/test_web_cli_equivalence.py -v`  
Expected before wiring static assets: Python equivalence passes; the Web root is not yet served.

Run in `frontend`: `npx playwright test e2e/mvp.spec.ts`  
Expected: FAIL because the production SPA is not mounted by FastAPI.

- [ ] **Step 3: Mount assets and add scripts/docs**

At app startup, serve `frontend/dist/assets` at `/assets` and return `frontend/dist/index.html` for non-API routes, but keep API 404 responses as JSON. `smoke.ps1` and `smoke.sh` must create a temporary data directory, run Python tests excluding the real model, build frontend, start the server on localhost, call `/api/v1/health`, and terminate the child process. `benchmark.py` records platform, Python/torch versions, model load seconds, input characters, processing seconds, characters/second, and peak RSS to JSON.

Document:

- Python 3.11 and Node prerequisites.
- `uv sync --extra dev --extra model` and `npm install`.
- `typofix model download`, rules-only operation, CLI examples and `typofix serve`.
- platform user data directories and `TYPOFIX_DATA_DIR`.
- offline model directory copying.
- Windows/macOS build verification.
- Linux aarch64 wheelhouse preparation and the requirement for real-device 麒麟 validation.
- localhost-only security and the risk of binding to a LAN address without authentication.

CI must run Python tests on Windows, macOS and Ubuntu, build/test frontend on Ubuntu, and exclude real model downloads. Do not claim a 麒麟 package until the real-device smoke evidence is recorded.

- [ ] **Step 4: Run every local quality gate**

Run: `uv run pytest backend/tests cli/tests -v -m "not model" --cov=typofix_cn --cov=typofix_cli`  
Expected: PASS.

Run in `frontend`: `npm run lint`  
Expected: PASS.

Run in `frontend`: `npm test -- --run`  
Expected: PASS.

Run in `frontend`: `npm run build`  
Expected: PASS.

Run in `frontend`: `npx playwright test`  
Expected: PASS.

Run: `powershell -ExecutionPolicy Bypass -File scripts/smoke.ps1` on Windows and `bash scripts/smoke.sh` on macOS/Linux.  
Expected: both scripts print `Typofix smoke test passed` on their respective platforms.

- [ ] **Step 5: Commit the integrated MVP**

```powershell
git add backend frontend scripts README.md docs/deployment.md .github/workflows/ci.yml
git commit -m "feat: complete Typofix CN MVP"
```

## Completion audit

- [ ] Confirm `git status --short` is empty.
- [ ] Confirm every enabled subtype maps to exactly one of the five parent categories.
- [ ] Confirm normal Web and CLI output never expose subtype codes unless verbose output is requested.
- [ ] Confirm adding or deleting a term changes issue status without invoking a Corrector.
- [ ] Confirm corrupt documents are isolated inside batch results.
- [ ] Confirm report HTML opens with networking disabled and contains no remote resources.
- [ ] Confirm FastAPI binds to `127.0.0.1` by default.
- [ ] Confirm no SQLite/database package or runtime file exists.
- [ ] Record Windows and macOS CPU benchmark JSON files outside Git unless the user requests committing benchmark evidence.
- [ ] Leave 麒麟 ARM packaging marked unverified until a real target machine passes the smoke test.

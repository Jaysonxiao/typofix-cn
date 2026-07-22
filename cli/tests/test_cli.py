from docx import Document
from docx.shared import Pt
from typer.testing import CliRunner

from typofix_cli.main import app


def make_docx(directory):
    path = directory / "论文.docx"
    document = Document()
    paragraph = document.add_paragraph("正文内容。")
    paragraph.paragraph_format.first_line_indent = Pt(24)
    document.save(path)
    return path


def test_rules_only_directory_check_creates_both_reports(tmp_path) -> None:
    make_docx(tmp_path)
    result = CliRunner().invoke(app, ["check", str(tmp_path), "--rules-only", "--data-dir", str(tmp_path / "data")])
    assert result.exit_code == 0, result.stdout
    assert "JSON:" in result.stdout
    assert "HTML:" in result.stdout
    assert list((tmp_path / "data" / "jobs").glob("*/report.json"))
    assert list((tmp_path / "data" / "jobs").glob("*/report.html"))


def test_term_add_is_idempotent(tmp_path) -> None:
    runner = CliRunner()
    args = ["terms", "add", "default", "麒麟操作系统", "--data-dir", str(tmp_path)]
    assert runner.invoke(app, args).exit_code == 0
    assert runner.invoke(app, args).exit_code == 0
    assert (tmp_path / "term-libraries" / "default.txt").read_text(encoding="utf-8") == "麒麟操作系统\n"


def test_help_lists_main_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "check" in result.stdout
    assert "serve" in result.stdout
    assert "terms" in result.stdout

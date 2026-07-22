from pathlib import Path

import typer

from typofix_cn.application.analyze import AnalysisService
from typofix_cn.config import Settings
from typofix_cn.correctors.fake import FakeCorrector
from typofix_cn.correctors.macbert import MacBertCorrector
from typofix_cn.jobs.repository import JobRepository
from typofix_cn.reports.html_report import HtmlReportWriter
from typofix_cn.reports.json_report import JsonReportWriter
from typofix_cn.terms.repository import TextTermRepository

app = typer.Typer(no_args_is_help=True)
terms_app = typer.Typer(no_args_is_help=True)
model_app = typer.Typer(no_args_is_help=True)
app.add_typer(terms_app, name="terms")
app.add_typer(model_app, name="model")


def _settings(data_dir: Path | None) -> Settings:
    settings = Settings(data_dir=data_dir) if data_dir is not None else Settings()
    settings.ensure_directories()
    return settings


def _collect(paths: list[Path]) -> list[tuple[Path, str]]:
    result: list[tuple[Path, str]] = []
    for path in paths:
        if path.is_file() and path.suffix.lower() == ".docx" and not path.name.startswith("~$"):
            result.append((path, path.name))
        elif path.is_dir():
            result.extend((item, item.relative_to(path).as_posix()) for item in sorted(path.rglob("*.docx")) if not item.name.startswith("~$"))
    if not result:
        raise typer.BadParameter("没有找到 DOCX 文件")
    return result


@app.command()
def check(
    paths: list[Path] = typer.Argument(..., exists=True),
    term_lib: list[str] = typer.Option([], "--term-lib"),
    rules_only: bool = typer.Option(False, "--rules-only"),
    data_dir: Path | None = typer.Option(None, "--data-dir"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    settings = _settings(data_dir)
    selected_paths = _collect(paths)
    input_paths = [item[0] for item in selected_paths]
    relative_paths = [item[1] for item in selected_paths]
    repository = TextTermRepository(settings.term_libraries_dir)
    libraries = {name: repository.load(name).terms for name in term_lib}
    corrector = FakeCorrector({}) if rules_only else MacBertCorrector(settings.models_dir / "macbert4csc-base-chinese")
    report = AnalysisService(corrector=corrector, term_libraries=libraries, model_name=settings.model_name).analyze(input_paths, relative_paths=relative_paths, selected_libraries=term_lib, mode="rules_only" if rules_only else "full")
    job = JobRepository(settings.data_dir).create(relative_paths, mode=report.mode, libraries=term_lib)
    job_dir = JobRepository(settings.data_dir).job_dir(job.job_id)
    json_path = job_dir / "report.json"
    html_path = job_dir / "report.html"
    JsonReportWriter().write(report.model_copy(update={"job_id": job.job_id}), json_path)
    HtmlReportWriter().write(report.model_copy(update={"job_id": job.job_id}), html_path)
    typer.echo(f"JSON: {json_path}")
    typer.echo(f"HTML: {html_path}")
    if verbose:
        for issue in report.issues:
            typer.echo(f"{issue.category.value}/{issue.type_code}: {issue.message}")


@app.command()
def serve(data_dir: Path | None = typer.Option(None, "--data-dir"), host: str = "127.0.0.1", port: int = 8000) -> None:
    from uvicorn import run
    from typofix_cn.api.app import create_app

    run(create_app(_settings(data_dir)), host=host, port=port)


@terms_app.command("list")
def terms_list(data_dir: Path | None = typer.Option(None, "--data-dir")) -> None:
    settings = _settings(data_dir)
    for library in TextTermRepository(settings.term_libraries_dir).list():
        typer.echo(f"{library.name}\t{len(library.terms)}")


@terms_app.command("add")
def terms_add(name: str, term: str, data_dir: Path | None = typer.Option(None, "--data-dir")) -> None:
    settings = _settings(data_dir)
    repository = TextTermRepository(settings.term_libraries_dir)
    if not (settings.term_libraries_dir / f"{name}.txt").exists():
        repository.create(name)
    repository.add(name, term)
    typer.echo(f"已添加术语：{term}")


@model_app.command("download")
def model_download(data_dir: Path | None = typer.Option(None, "--data-dir")) -> None:
    settings = _settings(data_dir)
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise typer.BadParameter("请先安装 typofix-cn[model]") from exc
    target = settings.models_dir / "macbert4csc-base-chinese"
    snapshot_download(repo_id=settings.model_name, local_dir=target)
    typer.echo(f"模型已下载到：{target}")

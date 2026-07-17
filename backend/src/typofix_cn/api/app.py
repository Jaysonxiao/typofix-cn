import json
import re
import time
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from pathlib import PurePosixPath

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from typofix_cn.application.analyze import AnalysisService
from typofix_cn.config import Settings
from typofix_cn.correctors.fake import FakeCorrector
from typofix_cn.correctors.macbert import MacBertCorrector
from typofix_cn.domain.jobs import JobStatus
from typofix_cn.jobs.queue import JobQueue
from typofix_cn.jobs.repository import JobRepository
from typofix_cn.reports.html_report import HtmlReportWriter
from typofix_cn.reports.json_report import JsonReportWriter
from typofix_cn.terms.repository import TextTermRepository
from typofix_cn.api.routes.terms import build_terms_router


def _safe_upload_path(filename: str) -> Path:
    normalized = filename.replace("\\", "/")
    relative = PurePosixPath(normalized)
    parts = tuple(part for part in relative.parts if part not in {"", "."})
    if not parts or relative.is_absolute() or any(part == ".." or ":" in part for part in parts):
        raise HTTPException(status_code=422, detail={"code": "UNSUPPORTED_FILE", "message": "文件路径无效"})
    return Path(*parts)


def _read_text_retry(path: Path) -> str:
    for attempt in range(4):
        try:
            return path.read_text(encoding="utf-8")
        except PermissionError:
            if attempt == 3:
                raise
            time.sleep(0.01 * (attempt + 1))
    raise AssertionError("unreachable")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.ensure_directories()
    jobs = JobRepository(settings.data_dir)
    terms = TextTermRepository(settings.term_libraries_dir)

    def run_job(job_id: object) -> None:
        manifest = jobs.get(str(job_id))
        jobs.update(manifest.model_copy(update={"status": JobStatus.RUNNING, "phase": "analysis"}))
        try:
            library_data = {name: terms.load(name).terms for name in manifest.selected_libraries}
            corrector = FakeCorrector({}) if manifest.mode == "rules_only" else MacBertCorrector(settings.models_dir / "macbert4csc-base-chinese")
            input_paths = [jobs.job_dir(manifest.job_id) / "input" / Path(item) for item in manifest.input_paths]
            report = AnalysisService(corrector=corrector, term_libraries=library_data, model_name=settings.model_name).analyze(input_paths, relative_paths=manifest.input_paths, selected_libraries=manifest.selected_libraries, mode=manifest.mode, job_id=manifest.job_id)
            JsonReportWriter().write(report, jobs.job_dir(manifest.job_id) / "report.json")
            HtmlReportWriter().write(report, jobs.job_dir(manifest.job_id) / "report.html")
            status = JobStatus.COMPLETED_WITH_DOCUMENT_FAILURES if any(item.status == "failed" for item in report.documents) else JobStatus.COMPLETED
            jobs.update(manifest.model_copy(update={"status": status, "phase": "completed", "processed_documents": len(report.documents)}))
        except Exception as exc:
            jobs.update(manifest.model_copy(update={"status": JobStatus.FAILED, "phase": "failed", "error": str(exc)}))

    queue = JobQueue(worker=run_job)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        jobs.recover_interrupted()
        queue.start()
        yield
        queue.stop()

    app = FastAPI(title="Typofix CN", lifespan=lifespan)
    app.state.settings = settings
    app.state.jobs = jobs
    app.state.terms = terms
    app.include_router(build_terms_router())

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "model_name": settings.model_name}

    @app.post("/api/v1/jobs", status_code=202)
    async def create_job(
        files: list[UploadFile] = File(...),
        mode: str = Form("full"),
        term_libraries: str = Form(""),
    ):
        if mode not in {"full", "rules_only"}:
            raise HTTPException(status_code=422, detail={"code": "INVALID_MODE", "message": "校验模式无效"})
        if not files or len(files) > settings.max_batch_files:
            raise HTTPException(status_code=422, detail={"code": "FILE_COUNT_LIMIT", "message": "文件数量超出限制"})
        library_names = [item.strip() for item in re.split(r"[,\n]", term_libraries) if item.strip()]
        for name in library_names:
            try:
                terms.load(name)
            except FileNotFoundError:
                raise HTTPException(status_code=422, detail={"code": "LIBRARY_NOT_FOUND", "message": f"术语库不存在：{name}"})
        names = []
        for upload in files:
            relative_path = _safe_upload_path(upload.filename or "")
            filename = relative_path.name
            if not filename.lower().endswith(".docx") or filename.startswith("~$"):
                raise HTTPException(status_code=422, detail={"code": "UNSUPPORTED_FILE", "message": "只支持 DOCX 文件"})
            names.append(relative_path.as_posix())
        if len(set(names)) != len(names):
            raise HTTPException(status_code=422, detail={"code": "DUPLICATE_FILE", "message": "上传列表包含重复文件"})
        manifest = jobs.create(names, mode=mode, libraries=library_names)
        input_dir = jobs.job_dir(manifest.job_id) / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        try:
            for upload, filename in zip(files, names, strict=True):
                destination = input_dir / Path(filename)
                destination.parent.mkdir(parents=True, exist_ok=True)
                data = await upload.read(settings.max_file_bytes + 1)
                if len(data) > settings.max_file_bytes:
                    raise HTTPException(status_code=422, detail={"code": "FILE_SIZE_LIMIT", "message": "文件大小超出限制"})
                destination.write_bytes(data)
                if not zipfile.is_zipfile(destination):
                    raise HTTPException(status_code=422, detail={"code": "INVALID_DOCX", "message": "文件不是有效的 DOCX"})
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
            jobs.update(manifest.model_copy(update={"status": JobStatus.FAILED, "phase": "failed", "error": detail.get("message", "文件上传失败")}))
            raise
        except Exception as exc:
            jobs.update(manifest.model_copy(update={"status": JobStatus.FAILED, "phase": "failed", "error": str(exc)}))
            raise HTTPException(status_code=500, detail={"code": "UPLOAD_FAILED", "message": "文件保存失败"}) from exc
        queue.submit(manifest.job_id)
        return {"job_id": manifest.job_id, "status": manifest.status.value}

    @app.get("/api/v1/jobs")
    def list_jobs():
        return [item.model_dump(mode="json") for item in jobs.list()]

    @app.get("/api/v1/jobs/{job_id}")
    def get_job(job_id: str):
        try:
            return jobs.get(job_id).model_dump(mode="json")
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": "任务不存在"})

    @app.get("/api/v1/jobs/{job_id}/report.json")
    def get_json_report(job_id: str):
        try:
            path = jobs.existing_job_dir(job_id) / "report.json"
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": "任务不存在"})
        if not path.exists():
            raise HTTPException(status_code=404, detail={"code": "REPORT_NOT_READY", "message": "报告尚未生成"})
        return JSONResponse(json.loads(_read_text_retry(path)))

    @app.get("/api/v1/jobs/{job_id}/report.html")
    def get_html_report(job_id: str):
        try:
            path = jobs.existing_job_dir(job_id) / "report.html"
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": "任务不存在"})
        if not path.exists():
            raise HTTPException(status_code=404, detail={"code": "REPORT_NOT_READY", "message": "报告尚未生成"})
        return HTMLResponse(_read_text_retry(path))

    frontend_dir = settings.frontend_dir or (Path(__file__).resolve().parents[4] / "frontend" / "dist")
    if frontend_dir.is_dir() and (frontend_dir / "index.html").is_file():
        assets_dir = frontend_dir / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def frontend_fallback(full_path: str):
            if full_path == "api" or full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "资源不存在"})
            return FileResponse(frontend_dir / "index.html", media_type="text/html")

    return app

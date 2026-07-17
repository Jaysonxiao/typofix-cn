import json
import re
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

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
            input_paths = [jobs.job_dir(manifest.job_id) / "input" / Path(item).name for item in manifest.input_paths]
            report = AnalysisService(corrector=corrector, term_libraries=library_data, model_name=settings.model_name).analyze(input_paths, selected_libraries=manifest.selected_libraries, mode=manifest.mode, job_id=manifest.job_id)
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
            terms.load(name)
        names = []
        for upload in files:
            filename = Path(upload.filename or "").name
            if not filename.lower().endswith(".docx") or filename.startswith("~$"):
                raise HTTPException(status_code=422, detail={"code": "UNSUPPORTED_FILE", "message": "只支持 DOCX 文件"})
            names.append(filename)
        manifest = jobs.create(names, mode=mode, libraries=library_names)
        input_dir = jobs.job_dir(manifest.job_id) / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        for upload, filename in zip(files, names, strict=True):
            destination = input_dir / filename
            data = await upload.read(settings.max_file_bytes + 1)
            if len(data) > settings.max_file_bytes:
                raise HTTPException(status_code=422, detail={"code": "FILE_SIZE_LIMIT", "message": "文件大小超出限制"})
            destination.write_bytes(data)
            if not zipfile.is_zipfile(destination):
                raise HTTPException(status_code=422, detail={"code": "INVALID_DOCX", "message": "文件不是有效的 DOCX"})
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
        path = jobs.job_dir(job_id) / "report.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail={"code": "REPORT_NOT_READY", "message": "报告尚未生成"})
        return JSONResponse(json.loads(path.read_text(encoding="utf-8")))

    @app.get("/api/v1/jobs/{job_id}/report.html")
    def get_html_report(job_id: str):
        path = jobs.job_dir(job_id) / "report.html"
        if not path.exists():
            raise HTTPException(status_code=404, detail={"code": "REPORT_NOT_READY", "message": "报告尚未生成"})
        return FileResponse(path, media_type="text/html")

    return app

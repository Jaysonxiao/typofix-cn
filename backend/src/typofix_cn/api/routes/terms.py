from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from typofix_cn.application.rematch import RematchService


class LibraryCreate(BaseModel):
    name: str


class TermChange(BaseModel):
    term: str


class RematchRequest(BaseModel):
    library: str | None = None


def build_terms_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.get("/term-libraries")
    def list_libraries(request: Request):
        return [item.model_dump(mode="json") for item in request.app.state.terms.list()]

    @router.post("/term-libraries", status_code=201)
    def create_library(payload: LibraryCreate, request: Request):
        try:
            return request.app.state.terms.create(payload.name).model_dump(mode="json")
        except FileExistsError as exc:
            raise HTTPException(status_code=409, detail={"code": "LIBRARY_EXISTS", "message": str(exc)})
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"code": "INVALID_LIBRARY", "message": str(exc)})

    @router.get("/term-libraries/{name}")
    def get_library(name: str, request: Request):
        try:
            return request.app.state.terms.load(name).model_dump(mode="json")
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail={"code": "LIBRARY_NOT_FOUND", "message": "术语库不存在"})

    @router.get("/term-libraries/{name}/download")
    def download_library(name: str, request: Request):
        try:
            request.app.state.terms.load(name)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail={"code": "LIBRARY_NOT_FOUND", "message": "术语库不存在"})
        return FileResponse(request.app.state.terms.root / f"{name}.txt", media_type="text/plain", filename=f"{name}.txt")

    @router.post("/term-libraries/{name}/terms")
    def add_term(name: str, payload: TermChange, request: Request):
        try:
            return request.app.state.terms.add(name, payload.term).model_dump(mode="json")
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=422, detail={"code": "INVALID_TERM", "message": str(exc)})

    @router.delete("/term-libraries/{name}/terms")
    def delete_term(name: str, payload: TermChange, request: Request):
        try:
            return request.app.state.terms.delete(name, payload.term).model_dump(mode="json")
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=422, detail={"code": "INVALID_TERM", "message": str(exc)})

    @router.post("/jobs/{job_id}/rematch")
    def rematch(job_id: str, request: Request, payload: RematchRequest | None = None):
        jobs = request.app.state.jobs
        try:
            manifest = jobs.get(job_id)
            job_dir = jobs.existing_job_dir(job_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": "任务不存在"})
        json_path = job_dir / "report.json"
        html_path = job_dir / "report.html"
        library_names = list(manifest.selected_libraries)
        if payload and payload.library and payload.library not in library_names:
            library_names.append(payload.library)
        try:
            libraries = {name: request.app.state.terms.load(name).terms for name in library_names}
        except FileNotFoundError as exc:
            raise HTTPException(status_code=422, detail={"code": "LIBRARY_NOT_FOUND", "message": "术语库不存在"}) from exc
        if library_names != manifest.selected_libraries:
            manifest = jobs.update(manifest.model_copy(update={"selected_libraries": library_names}))
        report = RematchService().rematch(json_path, html_path, libraries)
        return {"job_id": job_id, "summary": report.summary.model_dump(mode="json")}

    return router

import json
import os
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from typofix_cn.domain.jobs import JobManifest, JobStatus


class JobRepository:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.jobs_dir = self.data_dir / "jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def create(self, input_paths: list[str], *, mode: str, libraries: list[str]) -> JobManifest:
        with self._lock:
            job_id = uuid.uuid4().hex
            manifest = JobManifest(job_id=job_id, status=JobStatus.QUEUED, mode=mode, input_paths=input_paths, selected_libraries=libraries, total_documents=len(input_paths))
            self._write(manifest)
            return manifest

    def get(self, job_id: str) -> JobManifest:
        with self._lock:
            path = self.jobs_dir / job_id / "manifest.json"
            for attempt in range(4):
                try:
                    return JobManifest.model_validate_json(path.read_text(encoding="utf-8"))
                except PermissionError:
                    if attempt == 3:
                        raise
                    time.sleep(0.01 * (attempt + 1))
        raise AssertionError("unreachable")

    def update(self, manifest: JobManifest) -> JobManifest:
        with self._lock:
            updated = manifest.model_copy(update={"updated_at": datetime.now(timezone.utc)})
            self._write(updated)
            return updated

    def list(self) -> list[JobManifest]:
        with self._lock:
            manifests = []
            for path in self.jobs_dir.glob("*/manifest.json"):
                try:
                    manifests.append(JobManifest.model_validate_json(path.read_text(encoding="utf-8")))
                except (OSError, ValueError):
                    continue
            return sorted(manifests, key=lambda item: item.created_at, reverse=True)

    def recover_interrupted(self) -> None:
        for manifest in self.list():
            if manifest.status in {JobStatus.QUEUED, JobStatus.RUNNING}:
                self.update(manifest.model_copy(update={"status": JobStatus.INTERRUPTED, "phase": "interrupted"}))

    def job_dir(self, job_id: str) -> Path:
        path = self.jobs_dir / job_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def existing_job_dir(self, job_id: str) -> Path:
        path = self.jobs_dir / job_id
        if not path.is_dir():
            raise FileNotFoundError(job_id)
        return path

    def _write(self, manifest: JobManifest) -> None:
        directory = self.job_dir(manifest.job_id)
        path = directory / "manifest.json"
        content = manifest.model_dump_json(indent=2)
        fd, temp_name = tempfile.mkstemp(prefix=".manifest.", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            for attempt in range(4):
                try:
                    os.replace(temp_name, path)
                    break
                except PermissionError:
                    if attempt == 3:
                        raise
                    time.sleep(0.01 * (attempt + 1))
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

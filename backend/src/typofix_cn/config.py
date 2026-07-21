from typing import Optional
from pathlib import Path

from platformdirs import user_data_path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TYPOFIX_", extra="ignore")

    data_dir: Path = Field(default_factory=lambda: Path(user_data_path("TypofixCN")))
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    model_name: str = "shibing624/macbert4csc-base-chinese"
    model_backend: str = "auto"
    model_threads: int = Field(default=2, ge=1, le=8)
    max_file_bytes: int = Field(default=50 * 1024 * 1024, gt=0)
    max_batch_files: int = Field(default=100, gt=0)
    max_expanded_bytes: int = Field(default=200 * 1024 * 1024, gt=0)
    frontend_dir: Optional[Path] = None

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def models_dir(self) -> Path:
        return self.data_dir / "models"

    @property
    def term_libraries_dir(self) -> Path:
        return self.data_dir / "term-libraries"

    @property
    def confusions_dir(self) -> Path:
        return self.data_dir / "confusions"

    @property
    def confusions_path(self) -> Path:
        return self.confusions_dir / "default.txt"

    def ensure_directories(self) -> None:
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.term_libraries_dir.mkdir(parents=True, exist_ok=True)
        self.confusions_dir.mkdir(parents=True, exist_ok=True)
        default_library = self.term_libraries_dir / "default.txt"
        if not default_library.exists():
            default_library.write_text("", encoding="utf-8")
        if not self.confusions_path.exists():
            self.confusions_path.write_text("新资 => 薪资\n", encoding="utf-8")

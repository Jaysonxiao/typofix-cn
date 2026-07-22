from datetime import datetime

from pydantic import BaseModel


class TermLibrary(BaseModel):
    name: str
    terms: list[str]
    modified_at: datetime
    content_sha256: str

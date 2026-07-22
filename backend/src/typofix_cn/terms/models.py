from __future__ import annotations

from typing import Dict, FrozenSet, List, Set, Tuple
from datetime import datetime

from pydantic import BaseModel


class TermLibrary(BaseModel):
    name: str
    terms: List[str]
    modified_at: datetime
    content_sha256: str

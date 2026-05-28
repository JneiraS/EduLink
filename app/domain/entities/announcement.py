from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Announcement:
    id: int | None
    title: str
    content: str
    created_by: int
    pdf_filename: str | None
    created_at: datetime | None = None

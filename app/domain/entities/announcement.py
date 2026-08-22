from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class Announcement:
    id: int | None
    title: str
    content: str
    created_by: int
    pdf_filename: str | None
    created_at: datetime | None = None
    target_channel_ids: list[int] = field(default_factory=list)

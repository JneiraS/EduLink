from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class MessageTemplate:
    id: int | None
    owner_id: int
    label: str
    content: str
    created_at: datetime | None = None
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Notification:
    id: int | None
    user_id: int
    content: str
    is_read: bool
    created_at: datetime | None = None

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Message:
    id: int | None
    channel_id: int
    sender_id: int
    content: str
    created_at: datetime | None = None
    is_pinned: bool = False

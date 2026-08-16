from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Invitation:
    id: int | None
    user_id: int
    token: str
    expires_at: datetime
    used_at: datetime | None = None
    created_at: datetime | None = None
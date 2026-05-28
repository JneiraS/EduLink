from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PushSubscription:
    id: int | None
    user_id: int
    endpoint: str
    p256dh_key: str
    auth_key: str
    created_at: datetime | None = None

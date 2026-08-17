from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Child:
    id: int | None
    parent_id: int
    full_name: str
    class_name: str
    created_at: datetime | None = None
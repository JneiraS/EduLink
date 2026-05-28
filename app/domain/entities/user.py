from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    PARENT = "PARENT"
    TEACHER = "TEACHER"
    ADMIN = "ADMIN"


@dataclass(slots=True)
class User:
    id: int | None
    full_name: str
    email: str
    role: UserRole
    password_hash: str
    is_active: bool
    created_at: datetime | None = None

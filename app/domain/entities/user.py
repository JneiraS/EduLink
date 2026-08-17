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
    password_hash: str | None
    is_active: bool
    created_at: datetime | None = None


@dataclass(slots=True)
class UserSummary:
    """Lightweight user view (id, name, role) safe for non-admin contexts.

    Never carries email or password_hash: it is the only type returned to
    member-picker / sender-resolution templates so sensitive fields never
    reach template context for non-admin roles.
    """

    id: int | None
    full_name: str
    role: UserRole

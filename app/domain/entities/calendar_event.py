from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EventType(Enum):
    DEADLINE = "deadline"
    EVENT = "event"
    HOLIDAY = "holiday"


class EventCategory(Enum):
    ADMINISTRATIVE = "administrative"
    ACADEMIC = "academic"
    MEETING = "meeting"
    OUTING = "outing"
    HOLIDAY = "holiday"


@dataclass(slots=True)
class CalendarEvent:
    id: int | None
    title: str
    type: EventType
    start_date: datetime
    end_date: datetime | None = None
    category: EventCategory = EventCategory.ACADEMIC
    class_name: str = "Tous les niveaux"
    description: str | None = None
    location: str | None = None
    priority: str = "normal"
    created_at: datetime = field(default_factory=datetime.now)

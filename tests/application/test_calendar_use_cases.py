from datetime import datetime, timedelta

import pytest

from app.application.use_cases.calendar_use_cases import (
    CreateCalendarEvent,
    DeleteCalendarEvent,
    ListCalendarEvents,
)
from app.domain.entities.calendar_event import CalendarEvent, EventCategory, EventType
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, NotFoundError, ValidationError


class InMemoryCalendar:
    def __init__(self):
        self.events = []

    def save(self, event: CalendarEvent) -> CalendarEvent:
        event.id = len(self.events) + 1
        self.events.append(event)
        return event

    def list_events(
        self,
        type_filter: str | None = None,
        class_name: str | None = None,
        category: str | None = None,
    ) -> list[CalendarEvent]:
        result = list(self.events)
        if type_filter:
            result = [e for e in result if e.type.value == type_filter]
        if class_name:
            result = [e for e in result if e.class_name == class_name]
        if category:
            result = [e for e in result if e.category.value == category]
        return sorted(result, key=lambda e: e.start_date)

    def count_total(self) -> int:
        return len(self.events)

    def delete(self, event_id: int) -> CalendarEvent | None:
        for i, event in enumerate(self.events):
            if event.id == event_id:
                return self.events.pop(i)
        return None


def _actor(role=UserRole.ADMIN, uid=1):
    return User(
        id=uid,
        full_name="Actor",
        email=f"actor{uid}@test.local",
        role=role,
        password_hash="x",
        is_active=True,
    )


def _base_event(**kwargs):
    defaults = dict(
        id=None,
        title="Réunion parents-profs",
        type=EventType.EVENT,
        start_date=datetime(2026, 9, 20, 18, 0),
    )
    defaults.update(kwargs)
    return CalendarEvent(**defaults)


# ---------------------------------------------------------------------------
# CreateCalendarEvent
# ---------------------------------------------------------------------------

def test_create_event_requires_admin_or_teacher():
    use_case = CreateCalendarEvent(events=InMemoryCalendar())
    with pytest.raises(AuthorizationError):
        use_case.execute(
            _actor(UserRole.PARENT),
            title="Réunion",
            type_value="event",
            start_date=datetime(2026, 9, 20, 18, 0),
        )


def test_create_event_valid_for_teacher_and_admin():
    repo = InMemoryCalendar()
    use_case = CreateCalendarEvent(events=repo)
    event = use_case.execute(
        _actor(UserRole.TEACHER),
        title="Date limite",
        type_value="deadline",
        start_date=datetime(2026, 9, 25, 12, 0),
        end_date=None,
        category="administrative",
        class_name="CM2",
        description="Réponse attendue",
        location="Préau",
        priority="high",
    )
    assert event.id == 1
    assert event.type is EventType.DEADLINE
    assert event.category is EventCategory.ADMINISTRATIVE
    assert event.class_name == "CM2"
    assert event.description == "Réponse attendue"
    assert event.location == "Préau"
    assert event.priority == "high"


def test_create_event_defaults_when_omitted():
    repo = InMemoryCalendar()
    use_case = CreateCalendarEvent(events=repo)
    event = use_case.execute(
        _actor(UserRole.ADMIN),
        title="Kermesse",
        type_value="event",
        start_date=datetime(2026, 9, 30, 9, 0),
    )
    assert event.category is EventCategory.ACADEMIC
    assert event.class_name == "Tous les niveaux"
    assert event.priority == "normal"
    assert event.end_date is None
    assert event.description is None
    assert event.location is None


def test_create_event_requires_title():
    use_case = CreateCalendarEvent(events=InMemoryCalendar())
    with pytest.raises(ValidationError):
        use_case.execute(
            _actor(),
            title="   ",
            type_value="event",
            start_date=datetime(2026, 9, 20),
        )


def test_create_event_rejects_oversized_title():
    use_case = CreateCalendarEvent(events=InMemoryCalendar())
    with pytest.raises(ValidationError):
        use_case.execute(
            _actor(),
            title="X" * 121,
            type_value="event",
            start_date=datetime(2026, 9, 20),
        )


def test_create_event_rejects_invalid_type():
    use_case = CreateCalendarEvent(events=InMemoryCalendar())
    with pytest.raises(ValidationError):
        use_case.execute(
            _actor(),
            title="Réunion",
            type_value="mystery",
            start_date=datetime(2026, 9, 20),
        )


def test_create_event_rejects_invalid_category():
    use_case = CreateCalendarEvent(events=InMemoryCalendar())
    with pytest.raises(ValidationError):
        use_case.execute(
            _actor(),
            title="Réunion",
            type_value="event",
            start_date=datetime(2026, 9, 20),
            category="nonsense",
        )


def test_create_event_rejects_end_before_start():
    use_case = CreateCalendarEvent(events=InMemoryCalendar())
    with pytest.raises(ValidationError):
        use_case.execute(
            _actor(),
            title="Réunion",
            type_value="event",
            start_date=datetime(2026, 9, 20, 18, 0),
            end_date=datetime(2026, 9, 20, 9, 0),
        )


def test_create_event_trims_whitespace():
    repo = InMemoryCalendar()
    use_case = CreateCalendarEvent(events=repo)
    event = use_case.execute(
        _actor(),
        title="  Kermesse  ",
        type_value="event",
        start_date=datetime(2026, 9, 30, 9, 0),
        class_name="  ",
    )
    assert event.title == "Kermesse"
    assert event.class_name == "Tous les niveaux"


def test_create_event_rejects_oversized_description():
    use_case = CreateCalendarEvent(events=InMemoryCalendar())
    with pytest.raises(ValidationError):
        use_case.execute(
            _actor(),
            title="Réunion",
            type_value="event",
            start_date=datetime(2026, 9, 20),
            description="X" * 2001,
        )


# ---------------------------------------------------------------------------
# ListCalendarEvents
# ---------------------------------------------------------------------------

def _seed(repo: InMemoryCalendar) -> None:
    repo.save(_base_event(id=None, title="Deadline A", type=EventType.DEADLINE,
                          start_date=datetime(2026, 9, 10)))
    repo.save(_base_event(id=None, title="Event B", type=EventType.EVENT,
                          start_date=datetime(2026, 9, 20), class_name="CM2"))
    repo.save(_base_event(id=None, title="Holiday C", type=EventType.HOLIDAY,
                          start_date=datetime(2026, 10, 17), class_name="Tous les niveaux"))


def test_list_events_returns_all_sorted():
    repo = InMemoryCalendar()
    _seed(repo)
    use_case = ListCalendarEvents(events=repo)
    events = use_case.execute(_actor())
    assert [e.title for e in events] == ["Deadline A", "Event B", "Holiday C"]


def test_list_events_filters_by_type():
    repo = InMemoryCalendar()
    _seed(repo)
    use_case = ListCalendarEvents(events=repo)
    events = use_case.execute(_actor(), type_filter="holiday")
    assert [e.title for e in events] == ["Holiday C"]


def test_list_events_filters_by_class():
    repo = InMemoryCalendar()
    _seed(repo)
    use_case = ListCalendarEvents(events=repo)
    events = use_case.execute(_actor(), class_name="CM2")
    assert [e.title for e in events] == ["Event B"]


def test_list_events_filters_by_category():
    repo = InMemoryCalendar()
    repo.save(_base_event(id=None, title="Meet", type=EventType.EVENT,
                          start_date=datetime(2026, 9, 15), category=EventCategory.MEETING))
    repo.save(_base_event(id=None, title="Outing", type=EventType.EVENT,
                          start_date=datetime(2026, 9, 16), category=EventCategory.OUTING))
    use_case = ListCalendarEvents(events=repo)
    events = use_case.execute(_actor(), category="meeting")
    assert [e.title for e in events] == ["Meet"]


def test_list_events_rejects_invalid_type_filter():
    use_case = ListCalendarEvents(events=InMemoryCalendar())
    with pytest.raises(ValidationError):
        use_case.execute(_actor(), type_filter="bogus")


def test_list_events_rejects_invalid_category_filter():
    use_case = ListCalendarEvents(events=InMemoryCalendar())
    with pytest.raises(ValidationError):
        use_case.execute(_actor(), category="bogus")


def test_list_events_empty():
    use_case = ListCalendarEvents(events=InMemoryCalendar())
    assert use_case.execute(_actor()) == []


# ---------------------------------------------------------------------------
# DeleteCalendarEvent
# ---------------------------------------------------------------------------

def test_delete_event_requires_admin_or_teacher():
    repo = InMemoryCalendar()
    event = repo.save(_base_event(title="Meet"))
    use_case = DeleteCalendarEvent(events=repo)
    with pytest.raises(AuthorizationError):
        use_case.execute(_actor(UserRole.PARENT), event.id)


def test_delete_event_removes_it():
    repo = InMemoryCalendar()
    event = repo.save(_base_event(title="Meet"))
    use_case = DeleteCalendarEvent(events=repo)
    use_case.execute(_actor(), event.id)
    assert repo.count_total() == 0


def test_delete_event_not_found():
    use_case = DeleteCalendarEvent(events=InMemoryCalendar())
    with pytest.raises(NotFoundError):
        use_case.execute(_actor(), 999)


def test_delete_event_twice_second_raises_not_found():
    repo = InMemoryCalendar()
    event = repo.save(_base_event(title="Meet"))
    use_case = DeleteCalendarEvent(events=repo)
    use_case.execute(_actor(), event.id)
    with pytest.raises(NotFoundError):
        use_case.execute(_actor(), event.id)
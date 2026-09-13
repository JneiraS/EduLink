from dataclasses import dataclass
from datetime import datetime

from app.domain.entities.calendar_event import CalendarEvent, EventCategory, EventType
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, NotFoundError, ValidationError
from app.domain.ports.repositories import CalendarRepositoryPort

MAX_TITLE_LENGTH = 120
MAX_DESCRIPTION_LENGTH = 2000
MAX_LOCATION_LENGTH = 255
MAX_CLASS_NAME_LENGTH = 120

_EVENT_TYPES = {item.value for item in EventType}
_EVENT_CATEGORIES = {item.value for item in EventCategory}


def _require_manage(actor: User) -> None:
    if actor.role not in (UserRole.ADMIN, UserRole.TEACHER):
        raise AuthorizationError("Accès réservé aux enseignants et à l'administration")


@dataclass(slots=True)
class CreateCalendarEvent:
    events: CalendarRepositoryPort

    def execute(
        self,
        actor: User,
        title: str,
        type_value: str,
        start_date: datetime,
        end_date: datetime | None = None,
        category: str | None = None,
        class_name: str | None = None,
        description: str | None = None,
        location: str | None = None,
        priority: str | None = None,
    ) -> CalendarEvent:
        _require_manage(actor)

        title = title.strip()
        if not title:
            raise ValidationError("Le titre est requis")
        if len(title) > MAX_TITLE_LENGTH:
            raise ValidationError(
                f"Le titre ne doit pas dépasser {MAX_TITLE_LENGTH} caractères"
            )

        if type_value not in _EVENT_TYPES:
            raise ValidationError("Type d'événement invalide")

        if category is not None and category not in _EVENT_CATEGORIES:
            raise ValidationError("Catégorie invalide")

        if description is not None:
            description = description.strip() or None
            if description and len(description) > MAX_DESCRIPTION_LENGTH:
                raise ValidationError(
                    "La description ne doit pas dépasser "
                    f"{MAX_DESCRIPTION_LENGTH} caractères"
                )

        if location is not None:
            location = location.strip() or None
            if location and len(location) > MAX_LOCATION_LENGTH:
                raise ValidationError(
                    f"Le lieu ne doit pas dépasser {MAX_LOCATION_LENGTH} caractères"
                )

        if end_date is not None and end_date < start_date:
            raise ValidationError(
                "La date de fin doit être postérieure à la date de début"
            )

        class_name = (class_name or "Tous les niveaux").strip() or "Tous les niveaux"
        if len(class_name) > MAX_CLASS_NAME_LENGTH:
            raise ValidationError(
                f"Le public concerné ne doit pas dépasser {MAX_CLASS_NAME_LENGTH} caractères"
            )

        event = CalendarEvent(
            id=None,
            title=title,
            type=EventType(type_value),
            start_date=start_date,
            end_date=end_date,
            category=EventCategory(category) if category else EventCategory.ACADEMIC,
            class_name=class_name,
            description=description,
            location=location,
            priority=(priority or "normal").strip() or "normal",
        )
        return self.events.save(event)


@dataclass(slots=True)
class ListCalendarEvents:
    events: CalendarRepositoryPort

    def execute(
        self,
        actor: User,
        type_filter: str | None = None,
        class_name: str | None = None,
        category: str | None = None,
    ) -> list[CalendarEvent]:
        type_filter = (type_filter or "all").strip() or "all"
        class_name = (class_name or "all").strip() or "all"
        category = (category or "all").strip() or "all"

        if type_filter != "all" and type_filter not in _EVENT_TYPES:
            raise ValidationError("Filtre de type invalide")
        if category != "all" and category not in _EVENT_CATEGORIES:
            raise ValidationError("Filtre de catégorie invalide")

        return self.events.list_events(
            type_filter=None if type_filter == "all" else type_filter,
            class_name=None if class_name == "all" else class_name,
            category=None if category == "all" else category,
        )


@dataclass(slots=True)
class DeleteCalendarEvent:
    events: CalendarRepositoryPort

    def execute(self, actor: User, event_id: int) -> None:
        _require_manage(actor)
        deleted = self.events.delete(event_id)
        if deleted is None:
            raise NotFoundError("Événement introuvable")
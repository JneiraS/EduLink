from app.domain.entities.calendar_event import CalendarEvent, EventCategory, EventType
from app.domain.ports.repositories import CalendarRepositoryPort
from app.extensions import db
from app.infrastructure.database.models import CalendarEventModel


class SQLAlchemyCalendarRepository(CalendarRepositoryPort):
    def save(self, event: CalendarEvent) -> CalendarEvent:
        model = CalendarEventModel(
            title=event.title,
            type=event.type.value,
            category=event.category.value,
            class_name=event.class_name,
            description=event.description,
            location=event.location,
            priority=event.priority,
            start_date=event.start_date,
            end_date=event.end_date,
        )
        db.session.add(model)
        db.session.commit()
        return self._to_entity(model)

    def list_events(
        self,
        type_filter: str | None = None,
        class_name: str | None = None,
        category: str | None = None,
    ) -> list[CalendarEvent]:
        query = CalendarEventModel.query
        if type_filter:
            query = query.filter(CalendarEventModel.type == type_filter)
        if class_name:
            query = query.filter(CalendarEventModel.class_name == class_name)
        if category:
            query = query.filter(CalendarEventModel.category == category)
        rows = query.order_by(CalendarEventModel.start_date.asc()).all()
        return [self._to_entity(row) for row in rows]

    def count_total(self) -> int:
        return CalendarEventModel.query.count()

    def delete(self, event_id: int) -> CalendarEvent | None:
        model = db.session.get(CalendarEventModel, event_id)
        if model is None:
            return None
        entity = self._to_entity(model)
        db.session.delete(model)
        db.session.commit()
        return entity

    def _to_entity(self, model: CalendarEventModel) -> CalendarEvent:
        return CalendarEvent(
            id=model.id,
            title=model.title,
            type=EventType(model.type),
            start_date=model.start_date,
            end_date=model.end_date,
            category=EventCategory(model.category),
            class_name=model.class_name,
            description=model.description,
            location=model.location,
            priority=model.priority,
            created_at=model.created_at,
        )
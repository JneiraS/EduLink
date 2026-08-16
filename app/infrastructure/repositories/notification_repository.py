from app.domain.entities.notification import Notification
from app.domain.errors import NotFoundError
from app.domain.ports.repositories import NotificationRepositoryPort
from app.extensions import db
from app.infrastructure.database.models import NotificationModel


class SQLAlchemyNotificationRepository(NotificationRepositoryPort):
    def save(self, notification: Notification) -> Notification:
        model = NotificationModel(
            user_id=notification.user_id,
            content=notification.content,
            is_read=notification.is_read,
            channel_id=notification.channel_id,
        )
        db.session.add(model)
        db.session.commit()
        return self._to_entity(model)

    def list_by_user(self, user_id: int) -> list[Notification]:
        rows = (
            NotificationModel.query.filter_by(user_id=user_id)
            .order_by(NotificationModel.created_at.desc())
            .all()
        )
        return [self._to_entity(row) for row in rows]

    def mark_as_read(self, notification_id: int, user_id: int) -> None:
        model = NotificationModel.query.filter_by(
            id=notification_id, user_id=user_id
        ).first()
        if not model:
            raise NotFoundError("Notification not found")
        model.is_read = True
        db.session.commit()

    def _to_entity(self, model: NotificationModel) -> Notification:
        return Notification(
            id=model.id,
            user_id=model.user_id,
            content=model.content,
            is_read=model.is_read,
            channel_id=model.channel_id,
            created_at=model.created_at,
        )

from dataclasses import dataclass

from app.domain.entities.user import User
from app.domain.ports.repositories import NotificationRepositoryPort


@dataclass(slots=True)
class ListNotifications:
    notifications: NotificationRepositoryPort

    def execute(self, actor: User):
        return self.notifications.list_by_user(actor.id or 0)


@dataclass(slots=True)
class MarkNotificationRead:
    notifications: NotificationRepositoryPort

    def execute(self, actor: User, notification_id: int) -> None:
        self.notifications.mark_as_read(notification_id, actor.id or 0)

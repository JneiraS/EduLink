from dataclasses import dataclass

from app.domain.entities.user import User
from app.domain.ports.repositories import (
    NotificationRepositoryPort,
    PushSubscriptionRepositoryPort,
)


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


@dataclass(slots=True)
class SubscribePushNotifications:
    push_subscriptions: PushSubscriptionRepositoryPort

    def execute(
        self,
        actor: User,
        endpoint: str,
        p256dh_key: str,
        auth_key: str,
    ):
        return self.push_subscriptions.save_for_user(
            user_id=actor.id or 0,
            endpoint=endpoint,
            p256dh_key=p256dh_key,
            auth_key=auth_key,
        )


@dataclass(slots=True)
class UnsubscribePushNotifications:
    push_subscriptions: PushSubscriptionRepositoryPort

    def execute(self, actor: User, endpoint: str) -> None:
        self.push_subscriptions.delete_for_user(actor.id or 0, endpoint)

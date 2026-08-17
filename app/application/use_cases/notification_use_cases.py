from dataclasses import dataclass

from app.application.use_cases.message_use_cases import (
    CHANNEL_NOT_FOUND,
    NOT_A_MEMBER,
    _assert_channel_access,
)
from app.domain.entities.user import User
from app.domain.ports.repositories import (
    ChannelRepositoryPort,
    NotificationPreferencesPort,
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
class GetNotificationSettings:
    preferences: NotificationPreferencesPort
    channels: ChannelRepositoryPort

    def execute(self, actor: User) -> dict:
        user_id = actor.id or 0
        channel_states = self.preferences.list_channel_states(user_id)
        user_channels = self.channels.list_for_user(user_id)
        full_states = {c.id: channel_states.get(c.id, True) for c in user_channels}
        return {
            "global_enabled": self.preferences.get_global_enabled(user_id),
            "channel_states": full_states,
        }


@dataclass(slots=True)
class SetGlobalNotifications:
    preferences: NotificationPreferencesPort

    def execute(self, actor: User, enabled: bool) -> None:
        self.preferences.set_global_enabled(actor.id or 0, enabled)


@dataclass(slots=True)
class ToggleChannelNotifications:
    preferences: NotificationPreferencesPort
    channels: ChannelRepositoryPort

    def execute(self, actor: User, channel_id: int) -> bool:
        _assert_channel_access(self.channels, actor, channel_id)
        current = self.preferences.is_channel_enabled(actor.id or 0, channel_id)
        new_state = not current
        self.preferences.set_channel_enabled(actor.id or 0, channel_id, new_state)
        return new_state


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

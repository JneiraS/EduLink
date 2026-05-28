from dataclasses import dataclass

from app.domain.entities.message import Message
from app.domain.entities.notification import Notification
from app.domain.entities.user import User
from app.domain.errors import AuthorizationError, NotFoundError, ValidationError
from app.domain.ports.repositories import (
    ChannelRepositoryPort,
    MessageRepositoryPort,
    NotificationRepositoryPort,
)
from app.domain.ports.services import RealtimeNotificationPort


@dataclass(slots=True)
class SendMessage:
    messages: MessageRepositoryPort
    channels: ChannelRepositoryPort
    notifications: NotificationRepositoryPort
    realtime: RealtimeNotificationPort

    def execute(self, actor: User, channel_id: int, content: str) -> Message:
        if not self.channels.find_by_id(channel_id):
            raise NotFoundError("Channel not found")
        if not self.channels.is_member(channel_id, actor.id or 0):
            raise AuthorizationError("User is not member of this channel")
        if not content.strip():
            raise ValidationError("Message content is required")

        message = Message(
            id=None,
            channel_id=channel_id,
            sender_id=actor.id or 0,
            content=content.strip(),
        )
        saved = self.messages.save(message)

        channel = self.channels.find_by_id(channel_id)
        member_ids = self.channels.list_member_ids(channel_id)
        for member_id in member_ids:
            if member_id == (actor.id or 0):
                continue

            created_notification = self.notifications.save(
                Notification(
                    id=None,
                    user_id=member_id,
                    content=f"Nouveau message dans le canal {channel.name}",
                    is_read=False,
                )
            )
            self.realtime.notify_user(
                member_id,
                {
                    "id": created_notification.id,
                    "content": created_notification.content,
                    "created_at": str(created_notification.created_at),
                },
            )

        self.realtime.notify_channel(
            channel_id,
            {
                "id": saved.id,
                "channel_id": channel_id,
                "sender_id": saved.sender_id,
                "content": saved.content,
                "created_at": str(saved.created_at),
            },
        )

        return saved


@dataclass(slots=True)
class ListChannelMessages:
    messages: MessageRepositoryPort
    channels: ChannelRepositoryPort

    def execute(self, actor: User, channel_id: int) -> list[Message]:
        if not self.channels.find_by_id(channel_id):
            raise NotFoundError("Channel not found")
        if not self.channels.is_member(channel_id, actor.id or 0):
            raise AuthorizationError("User is not member of this channel")
        return self.messages.list_by_channel(channel_id)


@dataclass(slots=True)
class ListUserChannels:
    channels: ChannelRepositoryPort

    def execute(self, actor: User):
        return self.channels.list_for_user(actor.id or 0)

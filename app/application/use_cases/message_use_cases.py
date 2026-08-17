from dataclasses import dataclass

from app.domain.entities.message import Message
from app.domain.entities.notification import Notification
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, NotFoundError, ValidationError
from app.domain.ports.repositories import (
    ChannelRepositoryPort,
    MessageRepositoryPort,
    NotificationRepositoryPort,
    UserRepositoryPort,
)
from app.domain.ports.services import RealtimeNotificationPort

CHANNEL_NOT_FOUND = "Channel not found"
NOT_A_MEMBER = "User is not member of this channel"
MAX_MESSAGE_LENGTH = 5000


def _assert_channel_access(
    channels: ChannelRepositoryPort, actor: User, channel_id: int
) -> None:
    if not channels.find_by_id(channel_id):
        raise NotFoundError(CHANNEL_NOT_FOUND)
    if not channels.is_member(channel_id, actor.id or 0):
        raise AuthorizationError(NOT_A_MEMBER)


@dataclass(slots=True)
class SendMessage:
    messages: MessageRepositoryPort
    channels: ChannelRepositoryPort
    notifications: NotificationRepositoryPort
    realtime: RealtimeNotificationPort

    def execute(self, actor: User, channel_id: int, content: str) -> Message:
        if not self.channels.find_by_id(channel_id):
            raise NotFoundError(CHANNEL_NOT_FOUND)
        if not self.channels.is_member(channel_id, actor.id or 0):
            raise AuthorizationError(NOT_A_MEMBER)
        if not content.strip():
            raise ValidationError("Message content is required")
        content = content.strip()
        if len(content) > MAX_MESSAGE_LENGTH:
            raise ValidationError(
                f"Message must be at most {MAX_MESSAGE_LENGTH} characters"
            )

        message = Message(
            id=None,
            channel_id=channel_id,
            sender_id=actor.id or 0,
            content=content,
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
                    channel_id=channel_id,
                )
            )
            self.realtime.notify_user(
                member_id,
                {
                    "id": created_notification.id,
                    "content": created_notification.content,
                    "channel_id": channel_id,
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

    def execute(
        self,
        actor: User,
        channel_id: int,
        limit: int = 50,
        before_id: int | None = None,
    ):
        _assert_channel_access(self.channels, actor, channel_id)
        return self.messages.list_by_channel(channel_id, limit, before_id)


@dataclass(slots=True)
class SearchChannelMessages:
    messages: MessageRepositoryPort
    channels: ChannelRepositoryPort

    def execute(
        self, actor: User, channel_id: int, query: str, limit: int = 50
    ) -> list[Message]:
        _assert_channel_access(self.channels, actor, channel_id)
        term = query.strip()
        if not term:
            raise ValidationError("Search query is required")
        if len(term) > MAX_MESSAGE_LENGTH:
            raise ValidationError(
                f"Search query must be at most {MAX_MESSAGE_LENGTH} characters"
            )
        return self.messages.search_by_channel(channel_id, term, limit)


@dataclass(slots=True)
class ListPinnedMessages:
    messages: MessageRepositoryPort
    channels: ChannelRepositoryPort

    def execute(self, actor: User, channel_id: int) -> list[Message]:
        _assert_channel_access(self.channels, actor, channel_id)
        return self.messages.list_pinned(channel_id)


@dataclass(slots=True)
class PinMessage:
    messages: MessageRepositoryPort
    channels: ChannelRepositoryPort

    def execute(
        self, actor: User, channel_id: int, message_id: int, pinned: bool
    ) -> None:
        _assert_channel_access(self.channels, actor, channel_id)
        if actor.role not in {UserRole.ADMIN, UserRole.TEACHER}:
            raise AuthorizationError(
                "Only admins and teachers can pin messages"
            )
        message = self.messages.set_pinned(message_id, pinned)
        if message is None:
            raise NotFoundError("Message not found")


@dataclass(slots=True)
class ListUserChannels:
    channels: ChannelRepositoryPort

    def execute(self, actor: User):
        return self.channels.list_for_user(actor.id or 0)


@dataclass(slots=True)
class ListChannelMembers:
    channels: ChannelRepositoryPort
    users: UserRepositoryPort

    def execute(self, actor: User, channel_id: int) -> list[User]:
        if not self.channels.find_by_id(channel_id):
            raise NotFoundError(CHANNEL_NOT_FOUND)
        if not self.channels.is_member(channel_id, actor.id or 0):
            raise AuthorizationError(NOT_A_MEMBER)

        members = []
        for user_id in self.channels.list_member_ids(channel_id):
            user = self.users.find_by_id(user_id)
            if user:
                members.append(user)
        return members

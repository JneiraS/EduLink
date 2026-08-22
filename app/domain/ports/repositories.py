from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.announcement import Announcement
from app.domain.entities.channel import Channel
from app.domain.entities.child import Child
from app.domain.entities.invitation import Invitation
from app.domain.entities.message import Message
from app.domain.entities.message_template import MessageTemplate
from app.domain.entities.notification import Notification
from app.domain.entities.push_subscription import PushSubscription
from app.domain.entities.user import User


class UserRepositoryPort(ABC):
    @abstractmethod
    def save(self, user: User) -> User:
        raise NotImplementedError

    @abstractmethod
    def find_by_email(self, email: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, user_id: int) -> User | None:
        raise NotImplementedError

    @abstractmethod
    def find_many_by_ids(self, user_ids: list[int]) -> list[User]:
        raise NotImplementedError

    @abstractmethod
    def list_users(self) -> list[User]:
        raise NotImplementedError

    @abstractmethod
    def count_total(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def count_active(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def count_by_role(self) -> dict[str, int]:
        raise NotImplementedError

    @abstractmethod
    def count_grouped_by_date(self, since: datetime) -> list[dict]:
        raise NotImplementedError


class InvitationRepositoryPort(ABC):
    @abstractmethod
    def create(self, invitation: Invitation) -> Invitation:
        raise NotImplementedError

    @abstractmethod
    def find_by_token(self, token: str) -> Invitation | None:
        raise NotImplementedError

    @abstractmethod
    def find_active_by_user(self, user_id: int) -> Invitation | None:
        raise NotImplementedError

    @abstractmethod
    def mark_used(self, invitation_id: int) -> None:
        raise NotImplementedError


class AnnouncementRepositoryPort(ABC):
    @abstractmethod
    def save(self, announcement: Announcement) -> Announcement:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, announcement_id: int) -> Announcement | None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, announcement_id: int) -> Announcement | None:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[Announcement]:
        raise NotImplementedError

    @abstractmethod
    def list_recent(self, limit: int) -> list[Announcement]:
        raise NotImplementedError

    @abstractmethod
    def find_by_pdf_filename(self, pdf_filename: str) -> Announcement | None:
        raise NotImplementedError

    @abstractmethod
    def paginate(
        self,
        page: int,
        per_page: int,
        channel_ids: list[int] | None = None,
    ) -> tuple[list[Announcement], int]:
        raise NotImplementedError

    @abstractmethod
    def mark_read(self, announcement_id: int, user_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_read(self, announcement_id: int, user_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def count_read(self, announcement_id: int) -> int:
        raise NotImplementedError

    @abstractmethod
    def count_unread_for_user(self, user_id: int) -> int:
        raise NotImplementedError


class MessageRepositoryPort(ABC):
    @abstractmethod
    def save(self, message: Message) -> Message:
        raise NotImplementedError

    @abstractmethod
    def list_by_channel(
        self, channel_id: int, limit: int, before_id: int | None = None
    ) -> tuple[list[Message], bool]:
        raise NotImplementedError

    @abstractmethod
    def search_by_channel(
        self, channel_id: int, query: str, limit: int = 50
    ) -> list[Message]:
        raise NotImplementedError

    @abstractmethod
    def list_latest_by_channels(self, channel_ids: list[int]) -> dict[int, Message]:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, message_id: int) -> Message | None:
        raise NotImplementedError

    @abstractmethod
    def set_pinned(self, message_id: int, pinned: bool) -> Message | None:
        raise NotImplementedError

    @abstractmethod
    def list_pinned(self, channel_id: int) -> list[Message]:
        raise NotImplementedError

    @abstractmethod
    def count_grouped_by_date(self, since: datetime) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def count_top_channels(self, limit: int = 5) -> list[dict]:
        raise NotImplementedError


class NotificationRepositoryPort(ABC):
    @abstractmethod
    def save(self, notification: Notification) -> Notification:
        raise NotImplementedError

    @abstractmethod
    def list_by_user(self, user_id: int) -> list[Notification]:
        raise NotImplementedError

    @abstractmethod
    def count_unread(self, user_id: int) -> int:
        raise NotImplementedError

    @abstractmethod
    def mark_as_read(self, notification_id: int, user_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def mark_channel_read(self, channel_id: int, user_id: int) -> None:
        raise NotImplementedError


class NotificationPreferencesPort(ABC):
    @abstractmethod
    def get_global_enabled(self, user_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def set_global_enabled(self, user_id: int, enabled: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_channel_enabled(self, user_id: int, channel_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def set_channel_enabled(self, user_id: int, channel_id: int, enabled: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_channel_states(self, user_id: int) -> dict[int, bool]:
        raise NotImplementedError

    @abstractmethod
    def is_enabled(self, user_id: int, channel_id: int) -> bool:
        raise NotImplementedError


class ChannelRepositoryPort(ABC):
    @abstractmethod
    def create(self, channel: Channel) -> Channel:
        raise NotImplementedError

    @abstractmethod
    def create_with_members(self, channel: Channel, member_ids: list[int]) -> Channel:
        raise NotImplementedError

    @abstractmethod
    def list_for_user(self, user_id: int) -> list[Channel]:
        raise NotImplementedError

    @abstractmethod
    def add_member(self, channel_id: int, user_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_member(self, channel_id: int, user_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, channel_id: int) -> Channel | None:
        raise NotImplementedError

    @abstractmethod
    def find_direct_between(self, user_a: int, user_b: int) -> Channel | None:
        raise NotImplementedError

    @abstractmethod
    def find_by_name(self, name: str, kind: str | None = None) -> Channel | None:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[Channel]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, channel_id: int) -> Channel | None:
        raise NotImplementedError

    @abstractmethod
    def list_member_ids(self, channel_id: int) -> list[int]:
        raise NotImplementedError


class PushSubscriptionRepositoryPort(ABC):
    @abstractmethod
    def save_for_user(
        self,
        user_id: int,
        endpoint: str,
        p256dh_key: str,
        auth_key: str,
    ) -> PushSubscription:
        raise NotImplementedError

    @abstractmethod
    def list_by_user(self, user_id: int) -> list[PushSubscription]:
        raise NotImplementedError

    @abstractmethod
    def delete_by_endpoint(self, endpoint: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_for_user(self, user_id: int, endpoint: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def count_distinct_users(self) -> int:
        raise NotImplementedError


class MessageTemplateRepositoryPort(ABC):
    @abstractmethod
    def save(self, template: MessageTemplate) -> MessageTemplate:
        raise NotImplementedError

    @abstractmethod
    def list_by_owner(self, owner_id: int) -> list[MessageTemplate]:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, template_id: int) -> MessageTemplate | None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, template_id: int) -> MessageTemplate | None:
        raise NotImplementedError

    @abstractmethod
    def update(
        self, template_id: int, label: str, content: str
    ) -> MessageTemplate | None:
        raise NotImplementedError


class ChildrenRepositoryPort(ABC):
    @abstractmethod
    def save(self, child: Child) -> Child:
        raise NotImplementedError

    @abstractmethod
    def list_by_parent(self, parent_id: int) -> list[Child]:
        raise NotImplementedError

    @abstractmethod
    def find_by_class(self, class_name: str) -> list[Child]:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, child_id: int) -> Child | None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, child_id: int) -> Child | None:
        raise NotImplementedError

    @abstractmethod
    def list_class_names(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def find_by_name_like(self, query: str, limit: int = 20) -> list[Child]:
        raise NotImplementedError

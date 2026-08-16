from abc import ABC, abstractmethod

from app.domain.entities.announcement import Announcement
from app.domain.entities.channel import Channel
from app.domain.entities.message import Message
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


class AnnouncementRepositoryPort(ABC):
    @abstractmethod
    def save(self, announcement: Announcement) -> Announcement:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[Announcement]:
        raise NotImplementedError


class MessageRepositoryPort(ABC):
    @abstractmethod
    def save(self, message: Message) -> Message:
        raise NotImplementedError

    @abstractmethod
    def list_by_channel(self, channel_id: int) -> list[Message]:
        raise NotImplementedError


class NotificationRepositoryPort(ABC):
    @abstractmethod
    def save(self, notification: Notification) -> Notification:
        raise NotImplementedError

    @abstractmethod
    def list_by_user(self, user_id: int) -> list[Notification]:
        raise NotImplementedError

    @abstractmethod
    def mark_as_read(self, notification_id: int, user_id: int) -> None:
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

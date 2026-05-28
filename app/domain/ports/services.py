from abc import ABC, abstractmethod


class PasswordHasherPort(ABC):
    @abstractmethod
    def hash_password(self, plain_password: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        raise NotImplementedError


class RealtimeNotificationPort(ABC):
    @abstractmethod
    def notify_user(self, user_id: int, payload: dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def notify_channel(self, channel_id: int, payload: dict) -> None:
        raise NotImplementedError

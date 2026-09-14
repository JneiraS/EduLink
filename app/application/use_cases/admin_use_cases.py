from dataclasses import dataclass

from app.domain.entities.announcement import Announcement
from app.domain.entities.channel import Channel
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, NotFoundError, ValidationError
from app.domain.ports.repositories import (
    AnnouncementRepositoryPort,
    ChannelRepositoryPort,
    UserRepositoryPort,
)


def _require_admin(actor: User) -> None:
    if actor.role != UserRole.ADMIN:
        raise AuthorizationError("Seul l'administrateur peut accéder au panneau d'administration")


def _active_admin_count(users: list[User]) -> int:
    return len(
        [u for u in users if u.role == UserRole.ADMIN and u.is_active]
    )


@dataclass(slots=True)
class ListUsersForAdmin:
    users: UserRepositoryPort

    def execute(self, actor: User) -> list[User]:
        _require_admin(actor)
        return self.users.list_users()


@dataclass(slots=True)
class ListAnnouncementsForAdmin:
    announcements: AnnouncementRepositoryPort

    def execute(self, actor: User) -> list[Announcement]:
        _require_admin(actor)
        return self.announcements.list_all()


@dataclass(slots=True)
class ListChannelsForAdmin:
    channels: ChannelRepositoryPort

    def execute(self, actor: User) -> list[dict]:
        _require_admin(actor)
        return [
            {
                "channel": channel,
                "member_count": len(
                    self.channels.list_member_ids(channel.id or 0)
                ),
            }
            for channel in self.channels.list_all()
        ]


@dataclass(slots=True)
class UpdateUserRole:
    users: UserRepositoryPort

    def execute(self, actor: User, user_id: int, role: str) -> User:
        _require_admin(actor)
        if user_id == (actor.id or 0):
            raise AuthorizationError("Vous ne pouvez pas modifier votre propre rôle")

        target = self.users.find_by_id(user_id)
        if target is None:
            raise NotFoundError("Utilisateur introuvable")

        try:
            role_enum = UserRole(role)
        except ValueError as exc:
            raise ValidationError("Rôle invalide") from exc

        if (
            target.role == UserRole.ADMIN
            and role_enum != UserRole.ADMIN
            and _active_admin_count(self.users.list_users()) <= 1
        ):
            raise AuthorizationError("Impossible de rétrograder le dernier administrateur actif")

        target.role = role_enum
        return self.users.save(target)


@dataclass(slots=True)
class ToggleUserActive:
    users: UserRepositoryPort

    def execute(self, actor: User, user_id: int) -> User:
        _require_admin(actor)
        if user_id == (actor.id or 0):
            raise AuthorizationError("Vous ne pouvez pas désactiver votre propre compte")

        target = self.users.find_by_id(user_id)
        if target is None:
            raise NotFoundError("Utilisateur introuvable")

        if (
            target.role == UserRole.ADMIN
            and target.is_active
            and _active_admin_count(self.users.list_users()) <= 1
        ):
            raise AuthorizationError("Impossible de désactiver le dernier administrateur actif")

        target.is_active = not target.is_active
        return self.users.save(target)


@dataclass(slots=True)
class DeleteAnnouncement:
    announcements: AnnouncementRepositoryPort

    def execute(self, actor: User, announcement_id: int) -> Announcement:
        _require_admin(actor)
        announcement = self.announcements.find_by_id(announcement_id)
        if announcement is None:
            raise NotFoundError("Annonce introuvable")
        return self.announcements.delete(announcement_id)


@dataclass(slots=True)
class DeleteChannel:
    channels: ChannelRepositoryPort

    def execute(self, actor: User, channel_id: int) -> Channel:
        _require_admin(actor)
        channel = self.channels.find_by_id(channel_id)
        if channel is None:
            raise NotFoundError("Canal introuvable")
        return self.channels.delete(channel_id)
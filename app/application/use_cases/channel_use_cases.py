from dataclasses import dataclass

from app.domain.entities.channel import Channel
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, NotFoundError, ValidationError
from app.domain.ports.repositories import ChannelRepositoryPort, UserRepositoryPort


@dataclass(slots=True)
class CreateChannel:
    channels: ChannelRepositoryPort
    users: UserRepositoryPort

    def execute(self, actor: User, name: str, members: list[int]) -> Channel:
        if actor.role not in {UserRole.ADMIN, UserRole.TEACHER}:
            raise AuthorizationError("Seuls l'administrateur et les enseignants peuvent créer des canaux")
        name = name.strip()
        if not name:
            raise ValidationError("Le nom du canal est requis")
        if len(name) > 120:
            raise ValidationError("Le nom du canal ne doit pas dépasser 120 caractères")

        member_ids = [actor.id or 0, *members]
        unique_members = sorted(set(member_ids))
        for member_id in unique_members:
            if not self.users.find_by_id(member_id):
                raise ValidationError(f"L'utilisateur {member_id} n'existe pas")

        return self.channels.create_with_members(
            Channel(id=None, name=name, created_by=actor.id or 0),
            member_ids=member_ids,
        )


@dataclass(slots=True)
class AddChannelMembers:
    channels: ChannelRepositoryPort
    users: UserRepositoryPort

    def execute(self, actor: User, channel_id: int, members: list[int]) -> None:
        if actor.role not in {UserRole.ADMIN, UserRole.TEACHER}:
            raise AuthorizationError("Seuls l'administrateur et les enseignants peuvent ajouter des membres")

        if not self.channels.find_by_id(channel_id):
            raise NotFoundError("Canal introuvable")

        channel = self.channels.find_by_id(channel_id)
        if channel.kind == "direct":
            raise ValidationError("Impossible d'ajouter des membres à une conversation directe")

        if not self.channels.is_member(channel_id, actor.id or 0):
            raise AuthorizationError("Vous n'êtes pas membre de ce canal")

        unique_members = sorted(set(members))
        if not unique_members:
            raise ValidationError("Sélectionnez au moins un membre")

        for member_id in unique_members:
            if not self.users.find_by_id(member_id):
                raise ValidationError(f"L'utilisateur {member_id} n'existe pas")
            self.channels.add_member(channel_id, member_id)


@dataclass(slots=True)
class OpenDirectConversation:
    channels: ChannelRepositoryPort
    users: UserRepositoryPort

    def execute(self, actor: User, other_user_id: int) -> Channel:
        other = self.users.find_by_id(other_user_id)
        if other is None:
            raise NotFoundError("Utilisateur introuvable")
        if other.id == (actor.id or 0):
            raise ValidationError("Impossible de démarrer une conversation avec vous-même")

        existing = self.channels.find_direct_between(actor.id or 0, other.id or 0)
        if existing is not None:
            return existing

        return self.channels.create_with_members(
            Channel(
                id=None,
                name=f"{other.full_name} - {actor.full_name}",
                created_by=actor.id or 0,
                kind="direct",
            ),
            member_ids=[actor.id or 0, other.id or 0],
        )

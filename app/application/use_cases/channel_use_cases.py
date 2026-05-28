from dataclasses import dataclass

from app.domain.entities.channel import Channel
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, NotFoundError, ValidationError
from app.domain.ports.repositories import ChannelRepositoryPort, UserRepositoryPort


@dataclass(slots=True)
class CreateChannel:
    channels: ChannelRepositoryPort

    def execute(self, actor: User, name: str, members: list[int]) -> Channel:
        if actor.role not in {UserRole.ADMIN, UserRole.TEACHER}:
            raise AuthorizationError("Only admin and teachers can create channels")
        if not name.strip():
            raise ValidationError("Channel name is required")

        channel = self.channels.create(
            Channel(id=None, name=name.strip(), created_by=actor.id or 0)
        )
        self.channels.add_member(channel.id or 0, actor.id or 0)
        for member_id in members:
            self.channels.add_member(channel.id or 0, member_id)
        return channel


@dataclass(slots=True)
class AddChannelMembers:
    channels: ChannelRepositoryPort
    users: UserRepositoryPort

    def execute(self, actor: User, channel_id: int, members: list[int]) -> None:
        if actor.role not in {UserRole.ADMIN, UserRole.TEACHER}:
            raise AuthorizationError("Only admin and teachers can add channel members")

        if not self.channels.find_by_id(channel_id):
            raise NotFoundError("Channel not found")

        if not self.channels.is_member(channel_id, actor.id or 0):
            raise AuthorizationError("User is not member of this channel")

        unique_members = sorted(set(members))
        if not unique_members:
            raise ValidationError("Select at least one member")

        for member_id in unique_members:
            if not self.users.find_by_id(member_id):
                raise ValidationError(f"User {member_id} does not exist")
            self.channels.add_member(channel_id, member_id)

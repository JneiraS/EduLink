from dataclasses import dataclass

from app.domain.entities.channel import Channel
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, ValidationError
from app.domain.ports.repositories import ChannelRepositoryPort


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

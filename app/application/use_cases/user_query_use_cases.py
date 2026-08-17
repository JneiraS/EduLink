from dataclasses import dataclass

from app.domain.entities.user import User, UserRole, UserSummary
from app.domain.ports.repositories import UserRepositoryPort


def _to_summary(user: User) -> UserSummary:
    return UserSummary(
        id=user.id,
        full_name=user.full_name,
        role=user.role,
    )


@dataclass(slots=True)
class ListAllUsers:
    users: UserRepositoryPort

    def execute(self) -> list[UserSummary]:
        return [_to_summary(user) for user in self.users.list_users()]


@dataclass(slots=True)
class FindUsersByIds:
    users: UserRepositoryPort

    def execute(self, user_ids: list[int]) -> list[UserSummary]:
        return [_to_summary(user) for user in self.users.find_many_by_ids(user_ids)]
from dataclasses import dataclass

from app.domain.entities.user import User
from app.domain.ports.repositories import UserRepositoryPort


@dataclass(slots=True)
class ListAllUsers:
    users: UserRepositoryPort

    def execute(self) -> list[User]:
        return self.users.list_users()


@dataclass(slots=True)
class FindUsersByIds:
    users: UserRepositoryPort

    def execute(self, user_ids: list[int]) -> list[User]:
        return self.users.find_many_by_ids(user_ids)
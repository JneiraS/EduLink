from app.application.use_cases.user_query_use_cases import FindUsersByIds, ListAllUsers
from app.domain.entities.user import User, UserRole


def _full_user(uid, email="a@t.local", role=UserRole.PARENT):
    return User(
        id=uid,
        full_name=f"User {uid}",
        email=email,
        role=role,
        password_hash="scrypt-secret-hash",
        is_active=True,
    )


class InMemoryUsers:
    def __init__(self, users):
        self.users = users

    def list_users(self):
        return list(self.users)

    def find_many_by_ids(self, user_ids):
        by_id = {u.id: u for u in self.users}
        return [by_id[i] for i in user_ids if i in by_id]


def test_list_all_users_returns_summaries_without_sensitive_fields():
    use_case = ListAllUsers(
        users=InMemoryUsers([_full_user(1), _full_user(2)])
    )
    result = use_case.execute()
    assert [u.id for u in result] == [1, 2]
    assert result[0].full_name == "User 1"
    assert result[0].role == UserRole.PARENT
    assert not hasattr(result[0], "email")
    assert not hasattr(result[0], "password_hash")


def test_find_users_by_ids_returns_summaries_without_sensitive_fields():
    use_case = FindUsersByIds(
        users=InMemoryUsers([_full_user(1), _full_user(2)])
    )
    result = use_case.execute([2])
    assert len(result) == 1
    assert result[0].id == 2
    assert not hasattr(result[0], "email")
    assert not hasattr(result[0], "password_hash")
import pytest

from app.application.use_cases.auth_use_cases import LoginUser, RegisterUser
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError


class InMemoryUsers:
    def __init__(self):
        self.users = []

    def save(self, user):
        user.id = len(self.users) + 1
        self.users.append(user)
        return user

    def find_by_email(self, email):
        return next((u for u in self.users if u.email == email), None)

    def find_by_id(self, user_id):
        return next((u for u in self.users if u.id == user_id), None)

    def list_users(self):
        return list(self.users)


class FakeHasher:
    def hash_password(self, plain_password):
        return f"hashed:{plain_password}"

    def verify_password(self, plain_password, password_hash):
        return password_hash == f"hashed:{plain_password}"


def test_register_user_requires_admin():
    repo = InMemoryUsers()
    hasher = FakeHasher()
    use_case = RegisterUser(users=repo, hasher=hasher)

    actor = User(
        id=1,
        full_name="Parent",
        email="parent@test.local",
        role=UserRole.PARENT,
        password_hash="x",
        is_active=True,
    )

    with pytest.raises(AuthorizationError):
        use_case.execute(actor, "Teacher", "teacher@test.local", "TEACHER", "secret")


def test_login_user_success():
    repo = InMemoryUsers()
    hasher = FakeHasher()
    stored = User(
        id=1,
        full_name="Admin",
        email="admin@test.local",
        role=UserRole.ADMIN,
        password_hash=hasher.hash_password("secret"),
        is_active=True,
    )
    repo.save(stored)

    use_case = LoginUser(users=repo, hasher=hasher)
    user = use_case.execute("admin@test.local", "secret")

    assert user.email == "admin@test.local"

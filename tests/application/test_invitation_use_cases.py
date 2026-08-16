from datetime import datetime, timedelta, timezone

import pytest

from app.application.use_cases.auth_use_cases import (
    AcceptInvitation,
    CreateInvitation,
    CreateUserWithInvitation,
    ValidateInvitation,
)
from app.domain.entities.invitation import Invitation
from app.domain.entities.user import User, UserRole
from app.domain.errors import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
)

NOW = datetime.now(timezone.utc)


class InMemoryUsers:
    def __init__(self):
        self.users = []
        self._next = 1

    def save(self, user):
        if user.id is None:
            user.id = self._next
            self._next += 1
            self.users.append(user)
        else:
            for index, existing in enumerate(self.users):
                if existing.id == user.id:
                    self.users[index] = user
                    break
        return user

    def find_by_email(self, email):
        return next((u for u in self.users if u.email == email), None)

    def find_by_id(self, user_id):
        return next((u for u in self.users if u.id == user_id), None)

    def list_users(self):
        return list(self.users)


class InMemoryInvitations:
    def __init__(self):
        self.items = []

    def create(self, invitation):
        invitation.id = len(self.items) + 1
        self.items.append(invitation)
        return invitation

    def find_by_token(self, token):
        return next((i for i in self.items if i.token == token), None)

    def find_active_by_user(self, user_id):
        active = [
            i
            for i in self.items
            if i.user_id == user_id and i.used_at is None and i.expires_at > NOW
        ]
        return max(active, key=lambda i: i.expires_at) if active else None

    def mark_used(self, invitation_id):
        for invitation in self.items:
            if invitation.id == invitation_id:
                invitation.used_at = NOW
                return


class FakeHasher:
    def hash_password(self, plain_password):
        return f"hashed:{plain_password}"

    def verify_password(self, plain_password, password_hash):
        return password_hash == f"hashed:{plain_password}"


def _admin_actor(uid=1):
    return User(
        id=uid,
        full_name="Admin",
        email="admin@test.local",
        role=UserRole.ADMIN,
        password_hash="x",
        is_active=True,
    )


def _parent_actor():
    return User(
        id=2,
        full_name="Parent",
        email="parent@test.local",
        role=UserRole.PARENT,
        password_hash="x",
        is_active=True,
    )


def _create_user_with_invitation(users=None, invitations=None):
    return CreateUserWithInvitation(
        users=users or InMemoryUsers(),
        invitations=invitations or InMemoryInvitations(),
        ttl_hours=72,
    )


def _invite_user(users, invitations, email="teacher@test.local", role="TEACHER"):
    return _create_user_with_invitation(users, invitations).execute(
        _admin_actor(), "Teacher", email, role
    )


def test_create_user_with_invitation_requires_admin():
    with pytest.raises(AuthorizationError):
        _invite_user(
            InMemoryUsers(),
            InMemoryInvitations(),
            email="t@test.local",
        ).__class__ and _create_user_with_invitation(
            InMemoryUsers(), InMemoryInvitations()
        ).execute(_parent_actor(), "Teacher", "t@test.local", "TEACHER")


def test_create_user_with_invitation_creates_user_and_token():
    users = InMemoryUsers()
    invitations = InMemoryInvitations()
    user, invitation = _invite_user(users, invitations)
    assert user.password_hash is None
    assert user.is_active is True
    assert user.email == "teacher@test.local"
    assert invitation.token
    assert invitation.user_id == user.id
    assert invitation.used_at is None
    delta = (invitation.expires_at - NOW - timedelta(hours=72)).total_seconds()
    assert abs(delta) < 60


def test_create_user_with_invitation_requires_fields():
    with pytest.raises(ValidationError):
        _create_user_with_invitation().execute(_admin_actor(), "  ", "", "TEACHER")


def test_create_user_with_invitation_rejects_invalid_email():
    with pytest.raises(ValidationError):
        _create_user_with_invitation().execute(
            _admin_actor(), "Teacher", "not-an-email", "TEACHER"
        )


def test_create_user_with_invitation_rejects_duplicate_email():
    users = InMemoryUsers()
    invitations = InMemoryInvitations()
    _invite_user(users, invitations, email="dup@test.local")
    with pytest.raises(ValidationError):
        _create_user_with_invitation(users, invitations).execute(
            _admin_actor(), "Other", "DUP@test.local", "PARENT"
        )


def test_create_user_with_invitation_rejects_invalid_role():
    with pytest.raises(ValidationError):
        _create_user_with_invitation().execute(_admin_actor(), "Teacher", "t@test.local", "SUPERADMIN")


def test_validate_invitation_returns_user():
    users = InMemoryUsers()
    invitations = InMemoryInvitations()
    user, invitation = _invite_user(users, invitations)
    result = ValidateInvitation(users=users, invitations=invitations).execute(invitation.token)
    assert result.id == user.id


def test_validate_invitation_unknown_token():
    with pytest.raises(AuthenticationError):
        ValidateInvitation(users=InMemoryUsers(), invitations=InMemoryInvitations()).execute("nope")


def test_validate_invitation_expired():
    users = InMemoryUsers()
    invitations = InMemoryInvitations()
    user, _ = _invite_user(users, invitations)
    invitations.create(
        Invitation(
            id=None,
            user_id=user.id,
            token="expired-token",
            expires_at=NOW - timedelta(hours=1),
        )
    )
    with pytest.raises(AuthenticationError):
        ValidateInvitation(users=users, invitations=invitations).execute("expired-token")


def test_validate_invitation_used():
    users = InMemoryUsers()
    invitations = InMemoryInvitations()
    user, invitation = _invite_user(users, invitations)
    invitations.mark_used(invitation.id)
    with pytest.raises(AuthenticationError):
        ValidateInvitation(users=users, invitations=invitations).execute(invitation.token)


def test_accept_invitation_sets_password_and_marks_used():
    users = InMemoryUsers()
    invitations = InMemoryInvitations()
    user, invitation = _invite_user(users, invitations)
    hasher = FakeHasher()
    accepted = AcceptInvitation(users=users, invitations=invitations, hasher=hasher).execute(
        invitation.token, "newpass123"
    )
    assert accepted.password_hash == "hashed:newpass123"
    assert invitations.find_by_token(invitation.token).used_at is not None


def test_accept_invitation_is_one_time():
    users = InMemoryUsers()
    invitations = InMemoryInvitations()
    _, invitation = _invite_user(users, invitations)
    accept = AcceptInvitation(users=users, invitations=invitations, hasher=FakeHasher())
    accept.execute(invitation.token, "newpass123")
    with pytest.raises(AuthenticationError):
        accept.execute(invitation.token, "another123")


def test_accept_invitation_rejects_short_password():
    users = InMemoryUsers()
    invitations = InMemoryInvitations()
    _, invitation = _invite_user(users, invitations)
    with pytest.raises(ValidationError):
        AcceptInvitation(users=users, invitations=invitations, hasher=FakeHasher()).execute(
            invitation.token, "short"
        )


def test_accept_invitation_rejects_unknown_token():
    with pytest.raises(AuthenticationError):
        AcceptInvitation(
            users=InMemoryUsers(), invitations=InMemoryInvitations(), hasher=FakeHasher()
        ).execute("nope", "newpass123")


def test_accept_invitation_rejects_expired():
    users = InMemoryUsers()
    invitations = InMemoryInvitations()
    user, _ = _invite_user(users, invitations)
    invitations.create(
        Invitation(
            id=None, user_id=user.id, token="expired", expires_at=NOW - timedelta(hours=1)
        )
    )
    with pytest.raises(AuthenticationError):
        AcceptInvitation(users=users, invitations=invitations, hasher=FakeHasher()).execute(
            "expired", "newpass123"
        )


def test_accept_invitation_rejects_user_with_password():
    users = InMemoryUsers()
    invitations = InMemoryInvitations()
    user, invitation = _invite_user(users, invitations)
    user.password_hash = "hashed:oldpass"
    users.save(user)
    with pytest.raises(ValidationError):
        AcceptInvitation(users=users, invitations=invitations, hasher=FakeHasher()).execute(
            invitation.token, "newpass123"
        )


def test_accept_invitation_rejects_disabled_account():
    users = InMemoryUsers()
    invitations = InMemoryInvitations()
    user, invitation = _invite_user(users, invitations)
    user.is_active = False
    users.save(user)
    with pytest.raises(ValidationError):
        AcceptInvitation(users=users, invitations=invitations, hasher=FakeHasher()).execute(
            invitation.token, "newpass123"
        )


def test_create_invitation_requires_admin():
    with pytest.raises(AuthorizationError):
        CreateInvitation(users=InMemoryUsers(), invitations=InMemoryInvitations()).execute(
            _parent_actor(), 1
        )


def test_create_invitation_generates_fresh_token():
    users = InMemoryUsers()
    invitations = InMemoryInvitations()
    user, first = _invite_user(users, invitations)
    fresh = CreateInvitation(users=users, invitations=invitations, ttl_hours=72).execute(
        _admin_actor(), user.id
    )
    assert fresh.token != first.token
    assert invitations.find_by_token(fresh.token).user_id == user.id


def test_create_invitation_rejects_user_with_password():
    users = InMemoryUsers()
    invitations = InMemoryInvitations()
    user, _ = _invite_user(users, invitations)
    user.password_hash = "hashed:x"
    users.save(user)
    with pytest.raises(ValidationError):
        CreateInvitation(users=users, invitations=invitations).execute(_admin_actor(), user.id)


def test_create_invitation_user_not_found():
    with pytest.raises(ValidationError):
        CreateInvitation(users=InMemoryUsers(), invitations=InMemoryInvitations()).execute(
            _admin_actor(), 999
        )
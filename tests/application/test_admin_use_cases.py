import pytest

from app.application.use_cases.admin_use_cases import (
    DeleteAnnouncement,
    DeleteChannel,
    ListAnnouncementsForAdmin,
    ListChannelsForAdmin,
    ListUsersForAdmin,
    ToggleUserActive,
    UpdateUserRole,
)
from app.domain.entities.announcement import Announcement
from app.domain.entities.channel import Channel
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, NotFoundError, ValidationError


class InMemoryUsers:
    def __init__(self, users=None):
        self.users = users or []

    def list_users(self):
        return self.users

    def find_by_id(self, user_id):
        return next((u for u in self.users if u.id == user_id), None)

    def save(self, user):
        if user.id is None:
            user.id = len(self.users) + 1
            self.users.append(user)
        else:
            for index, existing in enumerate(self.users):
                if existing.id == user.id:
                    self.users[index] = user
                    break
        return user


class InMemoryAnnouncements:
    def __init__(self):
        self.items = []

    def list_all(self):
        return list(self.items)

    def find_by_id(self, announcement_id):
        return next((a for a in self.items if a.id == announcement_id), None)

    def delete(self, announcement_id):
        item = self.find_by_id(announcement_id)
        if item:
            self.items.remove(item)
        return item


class InMemoryChannels:
    def __init__(self):
        self.items = []
        self.members = {}

    def find_by_id(self, channel_id):
        return next((c for c in self.items if c.id == channel_id), None)

    def list_all(self):
        return list(self.items)

    def list_member_ids(self, channel_id):
        return list(self.members.get(channel_id, []))

    def delete(self, channel_id):
        item = self.find_by_id(channel_id)
        if item:
            self.items.remove(item)
            self.members.pop(channel_id, None)
        return item


def _user(role, uid, active=True):
    return User(
        id=uid, full_name="A", email=f"{uid}@t.local", role=role,
        password_hash="x", is_active=active,
    )


def _admin(uid=1):
    return _user(UserRole.ADMIN, uid)


# ---------------------------------------------------------------------------
# ListUsersForAdmin
# ---------------------------------------------------------------------------

def test_list_users_for_admin_rejects_non_admin():
    use_case = ListUsersForAdmin(users=InMemoryUsers())
    with pytest.raises(AuthorizationError):
        use_case.execute(_user(UserRole.PARENT, 1))


def test_list_users_for_admin_returns_all_users():
    users = [_admin(1), _user(UserRole.TEACHER, 2), _user(UserRole.PARENT, 3)]
    use_case = ListUsersForAdmin(users=InMemoryUsers(users))
    assert use_case.execute(_admin(1)) == users


# ---------------------------------------------------------------------------
# UpdateUserRole
# ---------------------------------------------------------------------------

def test_update_user_role_requires_admin():
    use_case = UpdateUserRole(users=InMemoryUsers())
    with pytest.raises(AuthorizationError):
        use_case.execute(_user(UserRole.TEACHER, 1), 2, "PARENT")


def test_update_user_role_unknown_user():
    use_case = UpdateUserRole(users=InMemoryUsers())
    with pytest.raises(NotFoundError):
        use_case.execute(_admin(1), 999, "PARENT")


def test_update_user_role_invalid_role():
    users = [_admin(1), _user(UserRole.PARENT, 2)]
    use_case = UpdateUserRole(users=InMemoryUsers(users))
    with pytest.raises(ValidationError):
        use_case.execute(_admin(1), 2, "PRESIDENT")


def test_update_user_role_success_preserves_password():
    users = [_admin(1), _user(UserRole.PARENT, 2)]
    use_case = UpdateUserRole(users=InMemoryUsers(users))
    updated = use_case.execute(_admin(1), 2, "TEACHER")
    assert updated.role == UserRole.TEACHER
    assert updated.password_hash == "x"
    assert users[1].role == UserRole.TEACHER


def test_update_user_role_rejects_self_demotion():
    users = [_admin(1), _user(UserRole.PARENT, 2)]
    use_case = UpdateUserRole(users=InMemoryUsers(users))
    with pytest.raises(AuthorizationError):
        use_case.execute(_admin(1), 1, "PARENT")


def test_update_user_role_rejects_demoting_last_active_admin():
    users = [_admin(1)]
    use_case = UpdateUserRole(users=InMemoryUsers(users))
    with pytest.raises(AuthorizationError):
        use_case.execute(_admin(1), 1, "TEACHER")


def test_update_user_role_allows_demoting_non_last_admin():
    users = [_admin(1), _admin(2), _user(UserRole.PARENT, 3)]
    use_case = UpdateUserRole(users=InMemoryUsers(users))
    updated = use_case.execute(_admin(1), 2, "TEACHER")
    assert updated.role == UserRole.TEACHER


# ---------------------------------------------------------------------------
# ToggleUserActive
# ---------------------------------------------------------------------------

def test_toggle_user_active_requires_admin():
    use_case = ToggleUserActive(users=InMemoryUsers())
    with pytest.raises(AuthorizationError):
        use_case.execute(_user(UserRole.TEACHER, 1), 2)


def test_toggle_user_active_unknown_user():
    use_case = ToggleUserActive(users=InMemoryUsers())
    with pytest.raises(NotFoundError):
        use_case.execute(_admin(1), 999)


def test_toggle_user_active_deactivates_and_reactivates():
    users = [_admin(1), _user(UserRole.TEACHER, 2)]
    use_case = ToggleUserActive(users=InMemoryUsers(users))
    disabled = use_case.execute(_admin(1), 2)
    assert disabled.is_active is False
    assert users[1].is_active is False
    reenabled = use_case.execute(_admin(1), 2)
    assert reenabled.is_active is True


def test_toggle_user_active_rejects_self_deactivation():
    users = [_admin(1), _user(UserRole.TEACHER, 2)]
    use_case = ToggleUserActive(users=InMemoryUsers(users))
    with pytest.raises(AuthorizationError):
        use_case.execute(_admin(1), 1)


def test_toggle_user_active_rejects_deactivating_last_active_admin():
    users = [_admin(1)]
    use_case = ToggleUserActive(users=InMemoryUsers(users))
    with pytest.raises(AuthorizationError):
        use_case.execute(_admin(1), 1)


# ---------------------------------------------------------------------------
# DeleteAnnouncement
# ---------------------------------------------------------------------------

def test_delete_announcement_requires_admin():
    use_case = DeleteAnnouncement(announcements=InMemoryAnnouncements())
    with pytest.raises(AuthorizationError):
        use_case.execute(_user(UserRole.TEACHER, 1), 1)


def test_delete_announcement_unknown():
    use_case = DeleteAnnouncement(announcements=InMemoryAnnouncements())
    with pytest.raises(NotFoundError):
        use_case.execute(_admin(1), 999)


def test_delete_announcement_removes_and_returns():
    repo = InMemoryAnnouncements()
    repo.items.append(
        Announcement(id=1, title="T", content="C", created_by=2, pdf_filename="f.pdf")
    )
    use_case = DeleteAnnouncement(announcements=repo)
    deleted = use_case.execute(_admin(1), 1)
    assert deleted.pdf_filename == "f.pdf"
    assert repo.items == []


def test_list_announcements_for_admin_rejects_non_admin():
    use_case = ListAnnouncementsForAdmin(announcements=InMemoryAnnouncements())
    with pytest.raises(AuthorizationError):
        use_case.execute(_user(UserRole.TEACHER, 1))


def test_list_announcements_for_admin_returns_all():
    repo = InMemoryAnnouncements()
    repo.items.append(
        Announcement(id=1, title="A", content="C", created_by=2, pdf_filename=None)
    )
    repo.items.append(
        Announcement(id=2, title="B", content="C", created_by=3, pdf_filename=None)
    )
    use_case = ListAnnouncementsForAdmin(announcements=repo)
    assert len(use_case.execute(_admin(1))) == 2


# ---------------------------------------------------------------------------
# DeleteChannel
# ---------------------------------------------------------------------------

def test_delete_channel_requires_admin():
    use_case = DeleteChannel(channels=InMemoryChannels())
    with pytest.raises(AuthorizationError):
        use_case.execute(_user(UserRole.TEACHER, 1), 1)


def test_delete_channel_unknown():
    use_case = DeleteChannel(channels=InMemoryChannels())
    with pytest.raises(NotFoundError):
        use_case.execute(_admin(1), 999)


def test_delete_channel_removes_and_returns():
    repo = InMemoryChannels()
    repo.items.append(Channel(id=1, name="C", created_by=2))
    repo.members[1] = [1, 2]
    use_case = DeleteChannel(channels=repo)
    deleted = use_case.execute(_admin(1), 1)
    assert deleted.name == "C"
    assert repo.items == []
    assert repo.members == {}


# ---------------------------------------------------------------------------
# ListChannelsForAdmin
# ---------------------------------------------------------------------------

def test_list_channels_for_admin_rejects_non_admin():
    use_case = ListChannelsForAdmin(channels=InMemoryChannels())
    with pytest.raises(AuthorizationError):
        use_case.execute(_user(UserRole.TEACHER, 1))


def test_list_channels_for_admin_returns_member_counts():
    repo = InMemoryChannels()
    repo.items.append(Channel(id=1, name="Alpha", created_by=2))
    repo.items.append(Channel(id=2, name="Bravo", created_by=3))
    repo.members[1] = [1, 2, 3]
    repo.members[2] = [1]
    use_case = ListChannelsForAdmin(channels=repo)
    rows = use_case.execute(_admin(1))
    assert len(rows) == 2
    counts = {row["channel"].name: row["member_count"] for row in rows}
    assert counts == {"Alpha": 3, "Bravo": 1}
import pytest

from app.application.use_cases.announcement_use_cases import (
    CreateAnnouncement,
    ListAnnouncements,
)
from app.domain.entities.announcement import Announcement
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, ValidationError


class InMemoryAnnouncements:
    def __init__(self):
        self.items = []

    def save(self, announcement):
        announcement.id = len(self.items) + 1
        self.items.append(announcement)
        return announcement

    def list_all(self):
        return list(self.items)

    def paginate(self, page, per_page):
        start = (page - 1) * per_page
        return self.items[start : start + per_page], len(self.items)


class InMemoryNotifications:
    def __init__(self):
        self.items = []

    def save(self, notification):
        notification.id = len(self.items) + 1
        self.items.append(notification)
        return notification


class InMemoryUsers:
    def __init__(self, users):
        self.users = users

    def list_users(self):
        return self.users


class FakeRealtime:
    def notify_user(self, user_id, payload):
        pass

    def notify_channel(self, channel_id, payload):
        pass


def _user(role, uid):
    return User(
        id=uid, full_name="A", email=f"{uid}@t.local", role=role,
        password_hash="x", is_active=True,
    )


def _make_use_case(users):
    return CreateAnnouncement(
        announcements=InMemoryAnnouncements(),
        notifications=InMemoryNotifications(),
        users=InMemoryUsers(users),
        realtime=FakeRealtime(),
    )


def test_create_announcement_requires_admin_or_teacher():
    use_case = _make_use_case([_user(UserRole.PARENT, 1)])
    with pytest.raises(AuthorizationError):
        use_case.execute(_user(UserRole.PARENT, 1), "T", "C")


def test_create_announcement_requires_title_and_content():
    use_case = _make_use_case([_user(UserRole.TEACHER, 1)])
    with pytest.raises(ValidationError):
        use_case.execute(_user(UserRole.TEACHER, 1), "", "C")


def test_create_announcement_rejects_oversized_title():
    use_case = _make_use_case([_user(UserRole.TEACHER, 1)])
    with pytest.raises(ValidationError):
        use_case.execute(_user(UserRole.TEACHER, 1), "x" * 256, "C")


def test_create_announcement_rejects_oversized_content():
    use_case = _make_use_case([_user(UserRole.TEACHER, 1)])
    with pytest.raises(ValidationError):
        use_case.execute(_user(UserRole.TEACHER, 1), "T", "x" * 5001)


def test_create_announcement_creates_notifications_for_all_users():
    users = [_user(UserRole.TEACHER, 1), _user(UserRole.PARENT, 2)]
    use_case = _make_use_case(users)
    announcement = use_case.execute(_user(UserRole.TEACHER, 1), "Titre", "Contenu")
    assert announcement.id == 1
    assert len(use_case.notifications.items) == 2


def test_list_announcements_paginates():
    repo = InMemoryAnnouncements()
    for i in range(12):
        repo.save(Announcement(id=None, title=f"A{i}", content="c", created_by=1, pdf_filename=None))
    use_case = ListAnnouncements(announcements=repo)
    page1, total = use_case.execute(page=1)
    assert len(page1) == 10
    assert total == 12
    page2, _ = use_case.execute(page=2)
    assert len(page2) == 2
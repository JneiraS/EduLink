import pytest

from app.application.use_cases.announcement_use_cases import (
    ConfirmAnnouncementRead,
    CreateAnnouncement,
    GetAnnouncementReadStatus,
    ListAnnouncements,
)
from app.domain.entities.announcement import Announcement
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, NotFoundError, ValidationError


class InMemoryAnnouncements:
    def __init__(self):
        self.items = []
        self.reads = {}

    def save(self, announcement):
        announcement.id = len(self.items) + 1
        self.items.append(announcement)
        return announcement

    def list_all(self):
        return list(self.items)

    def paginate(self, page, per_page):
        start = (page - 1) * per_page
        return self.items[start : start + per_page], len(self.items)

    def find_by_id(self, announcement_id):
        return next((a for a in self.items if a.id == announcement_id), None)

    def mark_read(self, announcement_id, user_id):
        self.reads.setdefault(announcement_id, set()).add(user_id)

    def is_read(self, announcement_id, user_id):
        return user_id in self.reads.get(announcement_id, set())

    def count_read(self, announcement_id):
        return len(self.reads.get(announcement_id, set()))


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


class InMemoryChannels:
    def __init__(self):
        self.channels = {}
        self.members = {}

    def find_by_id(self, channel_id):
        return channel_id in self.channels

    def add_channel(self, channel_id):
        self.channels[channel_id] = True

    def add_member(self, channel_id, user_id):
        self.members.setdefault(channel_id, set()).add(user_id)

    def list_member_ids(self, channel_id):
        return list(self.members.get(channel_id, set()))


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


def _make_use_case(users, channels=None):
    return CreateAnnouncement(
        announcements=InMemoryAnnouncements(),
        notifications=InMemoryNotifications(),
        users=InMemoryUsers(users),
        channels=channels or InMemoryChannels(),
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
    assert announcement.target_channel_ids == []


def test_create_announcement_targets_only_channel_members():
    users = [
        _user(UserRole.TEACHER, 1),
        _user(UserRole.PARENT, 2),
        _user(UserRole.PARENT, 3),
    ]
    channels = InMemoryChannels()
    channels.add_channel(10)
    channels.add_member(10, 1)
    channels.add_member(10, 2)
    use_case = _make_use_case(users, channels)
    announcement = use_case.execute(
        _user(UserRole.TEACHER, 1), "Titre", "Contenu", target_channel_ids=[10]
    )
    assert len(use_case.notifications.items) == 2
    assert announcement.target_channel_ids == [10]


def test_create_announcement_targets_union_of_channels():
    users = [
        _user(UserRole.TEACHER, 1),
        _user(UserRole.PARENT, 2),
        _user(UserRole.PARENT, 3),
    ]
    channels = InMemoryChannels()
    channels.add_channel(10)
    channels.add_member(10, 1)
    channels.add_member(10, 2)
    channels.add_channel(11)
    channels.add_member(11, 2)
    channels.add_member(11, 3)
    use_case = _make_use_case(users, channels)
    use_case.execute(
        _user(UserRole.TEACHER, 1), "Titre", "Contenu", target_channel_ids=[10, 11]
    )
    assert len(use_case.notifications.items) == 3


def test_create_announcement_rejects_unknown_channel():
    use_case = _make_use_case([_user(UserRole.TEACHER, 1)])
    with pytest.raises(NotFoundError):
        use_case.execute(
            _user(UserRole.TEACHER, 1), "Titre", "Contenu", target_channel_ids=[99]
        )


def test_confirm_announcement_read_marks_as_read():
    repo = InMemoryAnnouncements()
    announcement = repo.save(
        Announcement(id=None, title="T", content="C", created_by=1, pdf_filename=None)
    )
    use_case = ConfirmAnnouncementRead(announcements=repo)
    result = use_case.execute(_user(UserRole.PARENT, 2), announcement.id)
    assert repo.is_read(announcement.id, 2) is True
    assert repo.count_read(announcement.id) == 1
    assert result.id == announcement.id


def test_confirm_announcement_read_is_idempotent():
    repo = InMemoryAnnouncements()
    announcement = repo.save(
        Announcement(id=None, title="T", content="C", created_by=1, pdf_filename=None)
    )
    use_case = ConfirmAnnouncementRead(announcements=repo)
    use_case.execute(_user(UserRole.PARENT, 2), announcement.id)
    use_case.execute(_user(UserRole.PARENT, 2), announcement.id)
    assert repo.count_read(announcement.id) == 1


def test_confirm_announcement_read_rejects_missing():
    repo = InMemoryAnnouncements()
    use_case = ConfirmAnnouncementRead(announcements=repo)
    with pytest.raises(NotFoundError):
        use_case.execute(_user(UserRole.PARENT, 2), 999)


def test_get_announcement_read_status_uses_channel_audience():
    users = [
        _user(UserRole.TEACHER, 1),
        _user(UserRole.PARENT, 2),
        _user(UserRole.PARENT, 3),
    ]
    channels = InMemoryChannels()
    channels.add_channel(10)
    channels.add_member(10, 1)
    channels.add_member(10, 2)
    repo = InMemoryAnnouncements()
    announcement = repo.save(
        Announcement(
            id=None,
            title="T",
            content="C",
            created_by=1,
            pdf_filename=None,
            target_channel_ids=[10],
        )
    )
    repo.mark_read(announcement.id, 2)
    use_case = GetAnnouncementReadStatus(
        announcements=repo, channels=channels, users=InMemoryUsers(users)
    )
    status = use_case.execute(_user(UserRole.TEACHER, 1), [announcement])
    read_count, audience_size, is_read = status[announcement.id]
    assert read_count == 1
    assert audience_size == 2
    assert is_read is False


def test_get_announcement_read_status_uses_global_audience():
    users = [
        _user(UserRole.TEACHER, 1),
        _user(UserRole.PARENT, 2),
        _user(UserRole.PARENT, 3),
    ]
    repo = InMemoryAnnouncements()
    announcement = repo.save(
        Announcement(id=None, title="T", content="C", created_by=1, pdf_filename=None)
    )
    repo.mark_read(announcement.id, 2)
    use_case = GetAnnouncementReadStatus(
        announcements=repo,
        channels=InMemoryChannels(),
        users=InMemoryUsers(users),
    )
    status = use_case.execute(_user(UserRole.PARENT, 2), [announcement])
    read_count, audience_size, is_read = status[announcement.id]
    assert read_count == 1
    assert audience_size == 3
    assert is_read is True


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
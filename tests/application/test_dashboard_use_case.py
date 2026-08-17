from datetime import datetime

from app.application.use_cases.dashboard_use_case import GetDashboard
from app.domain.entities.announcement import Announcement
from app.domain.entities.channel import Channel
from app.domain.entities.child import Child
from app.domain.entities.message import Message
from app.domain.entities.notification import Notification
from app.domain.entities.user import User, UserRole


class InMemoryAnnouncements:
    def __init__(self, announcements=None):
        self.announcements = announcements or []
        self.read = set()

    def list_all(self):
        return list(self.announcements)

    def is_read(self, announcement_id, user_id):
        return (announcement_id, user_id) in self.read

    def count_unread_for_user(self, user_id):
        return sum(
            1
            for a in self.announcements
            if (a.id, user_id) not in self.read
        )


class InMemoryNotifications:
    def __init__(self, notifications=None):
        self.notifications = notifications or []

    def list_by_user(self, user_id):
        return [n for n in self.notifications if n.user_id == user_id]

    def count_unread(self, user_id):
        return sum(
            1
            for n in self.notifications
            if n.user_id == user_id and not n.is_read
        )


class InMemoryChannels:
    def __init__(self, channels=None, members=None):
        self.channels = channels or []
        self.members = members or {}

    def list_for_user(self, user_id):
        return [
            c
            for c in self.channels
            if user_id in self.members.get(c.id, [])
        ]

    def list_all(self):
        return list(self.channels)


class InMemoryMessages:
    def __init__(self, messages=None):
        self.messages = messages or []

    def list_latest_by_channels(self, channel_ids):
        latest = {}
        for channel_id in channel_ids:
            channel_messages = [
                m for m in self.messages if m.channel_id == channel_id
            ]
            if channel_messages:
                latest[channel_id] = max(
                    channel_messages, key=lambda m: m.id or 0
                )
        return latest


class InMemoryChildren:
    def __init__(self, children=None):
        self.children = children or []

    def list_by_parent(self, parent_id):
        return [c for c in self.children if c.parent_id == parent_id]


class InMemoryUsers:
    def __init__(self, users=None):
        self.users = users or []

    def list_users(self):
        return list(self.users)


def _user(uid, role):
    return User(
        id=uid,
        full_name=f"User {uid}",
        email=f"u{uid}@t.local",
        role=role,
        password_hash="x",
        is_active=True,
        created_at=datetime(2024, 1, 1),
    )


def _announcement(aid, title="Annonce"):
    return Announcement(
        id=aid,
        title=title,
        content="content",
        created_by=1,
        pdf_filename=None,
        created_at=datetime(2024, 1, 1),
    )


def _channel(cid, name="Canal"):
    return Channel(id=cid, name=name, created_by=1)


def _message(mid, channel_id, sender_id=1, content="bonjour"):
    return Message(
        id=mid,
        channel_id=channel_id,
        sender_id=sender_id,
        content=content,
        created_at=datetime(2024, 1, 2),
    )


def _notification(nid, user_id, channel_id=None, is_read=False):
    return Notification(
        id=nid,
        user_id=user_id,
        content="Nouveau message",
        is_read=is_read,
        channel_id=channel_id,
        created_at=datetime(2024, 1, 2),
    )


def _child(cid, parent_id):
    return Child(
        id=cid,
        parent_id=parent_id,
        full_name="Enfant",
        class_name="CM2",
    )


def _make_dashboard(
    announcements=None,
    notifications=None,
    channels=None,
    messages=None,
    children=None,
    users=None,
):
    members = {c.id: [1] for c in (channels or [])}
    return GetDashboard(
        announcements=InMemoryAnnouncements(announcements),
        notifications=InMemoryNotifications(notifications),
        channels=InMemoryChannels(channels, members),
        messages=InMemoryMessages(messages),
        children=InMemoryChildren(children),
        users=InMemoryUsers(users),
    )


def test_role_message_matches_actor_role():
    for role, expected in [
        (UserRole.ADMIN, "Espace administration"),
        (UserRole.TEACHER, "Espace enseignant"),
        (UserRole.PARENT, "Espace parent"),
    ]:
        data = _make_dashboard().execute(_user(1, role))
        assert data["role_message"] == expected


def test_stats_include_unread_notifications_and_channels_and_unread_announcements():
    dashboard = _make_dashboard(
        announcements=[_announcement(1), _announcement(2)],
        notifications=[
            _notification(1, 1, channel_id=10),
            _notification(2, 1, channel_id=10, is_read=True),
            _notification(3, 1, channel_id=11),
        ],
        channels=[_channel(10), _channel(11)],
    )
    data = dashboard.execute(_user(1, UserRole.TEACHER))
    assert data["stats"]["unread_notifications"] == 2
    assert data["stats"]["conversations_count"] == 2
    assert data["stats"]["unread_announcements"] == 2

    dashboard.announcements.read.add((2, 1))
    data = dashboard.execute(_user(1, UserRole.TEACHER))
    assert data["stats"]["unread_announcements"] == 1


def test_conversations_carry_latest_message():
    dashboard = _make_dashboard(
        channels=[_channel(10), _channel(11)],
        messages=[
            _message(1, 10, content="vieux"),
            _message(2, 10, content="recent"),
            _message(3, 11, content="seul"),
        ],
    )
    data = dashboard.execute(_user(1, UserRole.TEACHER))
    by_id = {c["channel"].id: c for c in data["conversations"]}
    assert by_id[10]["last_message"].content == "recent"
    assert by_id[11]["last_message"].content == "seul"


def test_conversation_without_messages_has_no_last_message():
    dashboard = _make_dashboard(channels=[_channel(10)])
    data = dashboard.execute(_user(1, UserRole.TEACHER))
    assert data["conversations"][0]["last_message"] is None


def test_latest_announcements_carry_read_status():
    dashboard = _make_dashboard(
        announcements=[_announcement(1), _announcement(2)]
    )
    dashboard.announcements.read.add((1, 1))
    data = dashboard.execute(_user(1, UserRole.TEACHER))
    by_id = {a["announcement"].id: a for a in data["latest_announcements"]}
    assert by_id[1]["is_read"] is True
    assert by_id[2]["is_read"] is False


def test_parent_gets_children():
    dashboard = _make_dashboard(children=[_child(1, 1), _child(2, 1)])
    data = dashboard.execute(_user(1, UserRole.PARENT))
    assert len(data["children"]) == 2
    assert data["children"][0].class_name == "CM2"


def test_teacher_does_not_get_children_or_admin_stats():
    data = _make_dashboard().execute(_user(1, UserRole.TEACHER))
    assert "children" not in data
    assert "user_counts" not in data


def test_admin_gets_platform_stats_and_recent_users():
    admin = _user(1, UserRole.ADMIN)
    teacher = _user(2, UserRole.TEACHER)
    parent = _user(3, UserRole.PARENT)
    dashboard = _make_dashboard(
        channels=[_channel(10)],
        announcements=[_announcement(1)],
        users=[admin, teacher, parent],
    )
    data = dashboard.execute(admin)
    assert data["user_counts"] == {
        UserRole.ADMIN: 1,
        UserRole.TEACHER: 1,
        UserRole.PARENT: 1,
    }
    assert data["channel_count"] == 1
    assert data["announcement_count"] == 1
    assert data["recent_users"] == [admin, teacher, parent]
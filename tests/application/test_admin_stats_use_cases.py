from datetime import datetime, timedelta, timezone

import pytest

from app.application.use_cases.admin_stats_use_case import GetAdminStats
from app.domain.entities.announcement import Announcement
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError

NOW = datetime.now(timezone.utc)


class FakeUsers:
    def __init__(self, users):
        self.users = users

    def list_users(self):
        return list(self.users)

    def count_total(self):
        return len(self.users)

    def count_active(self):
        return sum(1 for u in self.users if u.is_active)

    def count_by_role(self):
        counts = {}
        for u in self.users:
            role = u.role.value
            counts[role] = counts.get(role, 0) + 1
        return counts

    def count_grouped_by_date(self, since):
        counts = {}
        for u in self.users:
            if u.created_at and u.created_at >= since:
                counts[u.created_at.date()] = counts.get(u.created_at.date(), 0) + 1
        return [{"date": d, "count": c} for d, c in sorted(counts.items())]


class FakeMessages:
    def __init__(self, messages):
        self.messages = messages

    def count_grouped_by_date(self, since):
        counts = {}
        for m in self.messages:
            if m["created_at"] and m["created_at"] >= since:
                counts[m["created_at"].date()] = (
                    counts.get(m["created_at"].date(), 0) + 1
                )
        return [{"date": d, "count": c} for d, c in sorted(counts.items())]

    def count_top_channels(self, limit):
        by_channel = {}
        for m in self.messages:
            cid = m["channel_id"]
            by_channel[cid] = by_channel.get(cid, 0) + 1
        ordered = sorted(by_channel.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        return [
            {"channel_id": cid, "channel_name": f"C{cid}", "count": n}
            for cid, n in ordered
        ]


class FakeChannels:
    def __init__(self, members=None):
        self.members = members or {}

    def list_member_ids(self, channel_id):
        return list(self.members.get(channel_id, []))


class FakeAnnouncements:
    def __init__(self, announcements, reads=None):
        self.announcements = announcements
        self.reads = reads or {}

    def list_all(self):
        return list(self.announcements)

    def list_recent(self, limit):
        ordered = sorted(
            self.announcements,
            key=lambda a: a.created_at or NOW,
            reverse=True,
        )
        return list(ordered[:limit])

    def count_read(self, announcement_id):
        return len(self.reads.get(announcement_id, []))


class FakePushSubscriptions:
    def __init__(self, user_ids):
        self.user_ids = user_ids

    def count_distinct_users(self):
        return len(set(self.user_ids))


def _user(uid, role, created_at=None, active=True):
    return User(
        id=uid,
        full_name=f"User {uid}",
        email=f"u{uid}@t.local",
        role=role,
        password_hash="x",
        is_active=active,
        created_at=created_at or NOW,
    )


def _announcement(aid, title="Annonce", target_channel_ids=None, created_at=None):
    return Announcement(
        id=aid,
        title=title,
        content="content",
        created_by=1,
        pdf_filename=None,
        created_at=created_at or NOW,
        target_channel_ids=target_channel_ids or [],
    )


def _make_stats(
    users=None,
    messages=None,
    announcements=None,
    reads=None,
    channel_members=None,
    push_user_ids=None,
):
    return GetAdminStats(
        users=FakeUsers(users or []),
        messages=FakeMessages(messages or []),
        announcements=FakeAnnouncements(announcements or [], reads or {}),
        channels=FakeChannels(channel_members or {}),
        push_subscriptions=FakePushSubscriptions(push_user_ids or []),
    )


def test_requires_admin():
    with pytest.raises(AuthorizationError):
        _make_stats().execute(_user(1, UserRole.PARENT))


def test_returns_all_six_sections():
    stats = _make_stats(users=[_user(1, UserRole.ADMIN)])
    data = stats.execute(_user(1, UserRole.ADMIN))
    assert set(data) == {
        "registrations_by_week",
        "users_by_role",
        "messages_by_day",
        "top_channels",
        "announcement_read_rates",
        "push_adoption",
    }


def test_users_by_role_counts():
    users = [
        _user(1, UserRole.ADMIN),
        _user(2, UserRole.TEACHER),
        _user(3, UserRole.PARENT),
        _user(4, UserRole.PARENT),
    ]
    data = _make_stats(users=users).execute(_user(1, UserRole.ADMIN))
    assert data["users_by_role"] == {
        "ADMIN": 1,
        "TEACHER": 1,
        "PARENT": 2,
    }


def test_messages_by_day_pads_last_14_days():
    messages = [
        {"channel_id": 10, "created_at": NOW - timedelta(days=2)},
        {"channel_id": 10, "created_at": NOW - timedelta(days=2)},
        {"channel_id": 11, "created_at": NOW},
    ]
    data = _make_stats(messages=messages).execute(_user(1, UserRole.ADMIN))
    assert len(data["messages_by_day"]) == 14
    assert sum(day["count"] for day in data["messages_by_day"]) == 3


def test_registrations_bucketed_by_week():
    users = [
        _user(1, UserRole.ADMIN, created_at=NOW - timedelta(days=10)),
        _user(2, UserRole.PARENT, created_at=NOW - timedelta(days=10)),
        _user(3, UserRole.PARENT, created_at=NOW - timedelta(days=3)),
    ]
    data = _make_stats(users=users).execute(_user(1, UserRole.ADMIN))
    weeks = data["registrations_by_week"]
    assert sum(week["count"] for week in weeks) == 3
    assert max(week["count"] for week in weeks) == 2
    assert all(week["label"] for week in weeks)


def test_top_channels_limited_and_ordered():
    messages = []
    for _ in range(30):
        messages.append({"channel_id": 10, "created_at": NOW})
    for _ in range(20):
        messages.append({"channel_id": 11, "created_at": NOW})
    for _ in range(5):
        messages.append({"channel_id": 12, "created_at": NOW})
    data = _make_stats(messages=messages).execute(_user(1, UserRole.ADMIN))
    top = data["top_channels"]
    assert len(top) == 3
    assert [t["count"] for t in top] == [30, 20, 5]
    assert top[0]["channel_name"] == "C10"


def test_announcement_read_rates_global_uses_total_users():
    users = [_user(1, UserRole.ADMIN), _user(2, UserRole.PARENT), _user(3, UserRole.PARENT)]
    announcements = [_announcement(1, title="Rentree")]
    reads = {1: [1, 2]}
    data = _make_stats(
        users=users, announcements=announcements, reads=reads
    ).execute(_user(1, UserRole.ADMIN))
    assert data["announcement_read_rates"] == [
        {"title": "Rentree", "read": 2, "unread": 1}
    ]


def test_announcement_read_rates_targeted_uses_channel_members():
    users = [_user(1, UserRole.ADMIN)]
    announcements = [_announcement(1, title="Classe", target_channel_ids=[10])]
    reads = {1: [2]}
    channel_members = {10: [1, 2, 3]}
    data = _make_stats(
        users=users,
        announcements=announcements,
        reads=reads,
        channel_members=channel_members,
    ).execute(_user(1, UserRole.ADMIN))
    assert data["announcement_read_rates"] == [
        {"title": "Classe", "read": 1, "unread": 2}
    ]


def test_announcement_read_rates_limited_to_recent():
    users = [_user(1, UserRole.ADMIN)]
    announcements = [
        _announcement(aid, title=f"A{aid}", created_at=NOW - timedelta(days=aid))
        for aid in range(7, 0, -1)
    ]
    reads = {aid: [1] for aid in range(1, 8)}
    data = _make_stats(
        users=users, announcements=announcements, reads=reads
    ).execute(_user(1, UserRole.ADMIN))
    titles = [rate["title"] for rate in data["announcement_read_rates"]]
    assert titles == ["A1", "A2", "A3", "A4", "A5"]
    assert len(titles) == 5


def test_push_adoption_counts_distinct_subscribers():
    data = _make_stats(
        users=[_user(1, UserRole.ADMIN), _user(2, UserRole.PARENT)],
        push_user_ids=[1, 2, 2],
    ).execute(_user(1, UserRole.ADMIN))
    assert data["push_adoption"] == {"subscribers": 2, "total_users": 2}


def test_empty_database_returns_zeroed_sections():
    data = _make_stats().execute(_user(1, UserRole.ADMIN))
    assert data["users_by_role"] == {}
    assert data["top_channels"] == []
    assert data["announcement_read_rates"] == []
    assert data["push_adoption"] == {"subscribers": 0, "total_users": 0}
    assert len(data["messages_by_day"]) == 14
    assert all(day["count"] == 0 for day in data["messages_by_day"])
    assert data["registrations_by_week"]
    assert all(week["count"] == 0 for week in data["registrations_by_week"])
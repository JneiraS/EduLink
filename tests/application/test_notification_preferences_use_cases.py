import pytest

from app.application.use_cases.notification_use_cases import (
    GetNotificationSettings,
    MarkChannelNotificationsRead,
    SetGlobalNotifications,
    ToggleChannelNotifications,
)
from app.domain.entities.channel import Channel
from app.domain.entities.notification import Notification
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, NotFoundError


class InMemoryPrefs:
    def __init__(self):
        self.global_enabled = {}
        self.channel_states = {}

    def get_global_enabled(self, user_id):
        return self.global_enabled.get(user_id, True)

    def set_global_enabled(self, user_id, enabled):
        self.global_enabled[user_id] = enabled

    def is_channel_enabled(self, user_id, channel_id):
        return self.channel_states.get((user_id, channel_id), True)

    def set_channel_enabled(self, user_id, channel_id, enabled):
        self.channel_states[(user_id, channel_id)] = enabled

    def list_channel_states(self, user_id):
        return {
            cid: state
            for (uid, cid), state in self.channel_states.items()
            if uid == user_id
        }

    def is_enabled(self, user_id, channel_id):
        return self.get_global_enabled(user_id) and self.is_channel_enabled(
            user_id, channel_id
        )


class InMemoryChannelsForPrefs:
    def __init__(self, channels):
        self.channels = channels
        self.members = {c.id: [1] for c in channels}

    def list_for_user(self, user_id):
        return [c for c in self.channels if user_id in self.members.get(c.id, [])]

    def find_by_id(self, channel_id):
        return next((c for c in self.channels if c.id == channel_id), None)

    def is_member(self, channel_id, user_id):
        return user_id in self.members.get(channel_id, [])


def _actor(uid=1, role=UserRole.PARENT):
    return User(
        id=uid,
        full_name="A",
        email=f"{uid}@t.local",
        role=role,
        password_hash="x",
        is_active=True,
    )


def test_get_settings_default_all_enabled():
    channels = InMemoryChannelsForPrefs(
        [Channel(id=1, name="C1", created_by=2), Channel(id=2, name="C2", created_by=2)]
    )
    settings = GetNotificationSettings(
        preferences=InMemoryPrefs(), channels=channels
    ).execute(_actor())
    assert settings["global_enabled"] is True
    assert settings["channel_states"] == {1: True, 2: True}


def test_get_settings_reflects_disabled_channel_and_global():
    prefs = InMemoryPrefs()
    prefs.set_global_enabled(1, False)
    prefs.set_channel_enabled(1, 2, False)
    channels = InMemoryChannelsForPrefs(
        [Channel(id=1, name="C1", created_by=2), Channel(id=2, name="C2", created_by=2)]
    )
    settings = GetNotificationSettings(
        preferences=prefs, channels=channels
    ).execute(_actor())
    assert settings["global_enabled"] is False
    assert settings["channel_states"] == {1: True, 2: False}


def test_set_global_notifications_persists():
    prefs = InMemoryPrefs()
    SetGlobalNotifications(preferences=prefs).execute(_actor(), enabled=False)
    assert prefs.get_global_enabled(1) is False
    SetGlobalNotifications(preferences=prefs).execute(_actor(), enabled=True)
    assert prefs.get_global_enabled(1) is True


def test_toggle_channel_notifications_flips_state():
    prefs = InMemoryPrefs()
    channels = InMemoryChannelsForPrefs([Channel(id=1, name="C1", created_by=2)])
    use_case = ToggleChannelNotifications(preferences=prefs, channels=channels)
    assert use_case.execute(_actor(), channel_id=1) is False
    assert prefs.is_channel_enabled(1, 1) is False
    assert use_case.execute(_actor(), channel_id=1) is True
    assert prefs.is_channel_enabled(1, 1) is True


def test_toggle_channel_notifications_requires_membership():
    channels = InMemoryChannelsForPrefs([Channel(id=1, name="C1", created_by=2)])
    use_case = ToggleChannelNotifications(
        preferences=InMemoryPrefs(), channels=channels
    )
    with pytest.raises(AuthorizationError):
        use_case.execute(_actor(uid=9), channel_id=1)


def test_toggle_channel_notifications_missing_channel():
    channels = InMemoryChannelsForPrefs([Channel(id=1, name="C1", created_by=2)])
    use_case = ToggleChannelNotifications(
        preferences=InMemoryPrefs(), channels=channels
    )
    with pytest.raises(NotFoundError):
        use_case.execute(_actor(), channel_id=999)


class InMemoryNotifications:
    def __init__(self):
        self.channels_read = []

    def mark_channel_read(self, channel_id, user_id):
        self.channels_read.append((channel_id, user_id))


def test_mark_channel_read_marks_notifications_of_channel():
    notifications = InMemoryNotifications()
    channels = InMemoryChannelsForPrefs([Channel(id=1, name="C1", created_by=2)])
    use_case = MarkChannelNotificationsRead(
        notifications=notifications, channels=channels
    )
    use_case.execute(_actor(), channel_id=1)
    assert (1, 1) in notifications.channels_read


def test_mark_channel_read_requires_membership():
    notifications = InMemoryNotifications()
    channels = InMemoryChannelsForPrefs([Channel(id=1, name="C1", created_by=2)])
    use_case = MarkChannelNotificationsRead(
        notifications=notifications, channels=channels
    )
    with pytest.raises(AuthorizationError):
        use_case.execute(_actor(uid=9), channel_id=1)


def test_mark_channel_read_missing_channel():
    notifications = InMemoryNotifications()
    channels = InMemoryChannelsForPrefs([Channel(id=1, name="C1", created_by=2)])
    use_case = MarkChannelNotificationsRead(
        notifications=notifications, channels=channels
    )
    with pytest.raises(NotFoundError):
        use_case.execute(_actor(), channel_id=999)
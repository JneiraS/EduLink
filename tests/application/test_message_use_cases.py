import pytest

from app.application.use_cases.message_use_cases import (
    ListChannelMessages,
    ListPinnedMessages,
    PinMessage,
    SearchChannelMessages,
    SendMessage,
)
from app.domain.entities.channel import Channel
from app.domain.entities.message import Message
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, NotFoundError, ValidationError


class InMemoryMessages:
    def __init__(self):
        self.items = []

    def save(self, message):
        message.id = len(self.items) + 1
        self.items.append(message)
        return message

    def list_by_channel(self, channel_id, limit, before_id=None):
        rows = [m for m in self.items if m.channel_id == channel_id]
        if before_id is not None:
            rows = [m for m in rows if m.id < before_id]
        rows.sort(key=lambda m: m.id, reverse=True)
        has_more = len(rows) > limit
        rows = rows[:limit]
        rows.reverse()
        return rows, has_more

    def search_by_channel(self, channel_id, query, limit=50):
        term = query.strip().lower()
        rows = [
            m for m in self.items
            if m.channel_id == channel_id and term in m.content.lower()
        ]
        rows.sort(key=lambda m: m.id, reverse=True)
        rows = rows[:limit]
        rows.reverse()
        return rows

    def set_pinned(self, message_id, pinned):
        for m in self.items:
            if m.id == message_id:
                m.is_pinned = pinned
                return m
        return None

    def list_pinned(self, channel_id):
        rows = [m for m in self.items if m.channel_id == channel_id and m.is_pinned]
        rows.sort(key=lambda m: m.id, reverse=True)
        rows.reverse()
        return rows


class InMemoryNotifications:
    def __init__(self):
        self.items = []

    def save(self, notification):
        notification.id = len(self.items) + 1
        self.items.append(notification)
        return notification


class FakeRealtime:
    def notify_user(self, user_id, payload):
        pass

    def notify_channel(self, channel_id, payload):
        pass


class InMemoryChannels:
    def __init__(self, members=(1,)):
        self.channel = Channel(id=1, name="C", created_by=1)
        self.members = list(members)

    def find_by_id(self, channel_id):
        return self.channel if channel_id == 1 else None

    def is_member(self, channel_id, user_id):
        return channel_id == 1 and user_id in self.members


def _actor(uid=1, role=UserRole.TEACHER):
    return User(
        id=uid, full_name="A", email=f"{uid}@t.local", role=role,
        password_hash="x", is_active=True,
    )


class _AllEnabledPrefs:
    def get_global_enabled(self, user_id):
        return True

    def set_global_enabled(self, user_id, enabled):
        pass

    def is_channel_enabled(self, user_id, channel_id):
        return True

    def set_channel_enabled(self, user_id, channel_id, enabled):
        pass

    def list_channel_states(self, user_id):
        return {}

    def is_enabled(self, user_id, channel_id):
        return True


def _all_enabled_prefs():
    return _AllEnabledPrefs()


def test_list_messages_raises_not_found():
    use_case = ListChannelMessages(
        messages=InMemoryMessages(), channels=InMemoryChannels()
    )
    with pytest.raises(NotFoundError):
        use_case.execute(_actor(), channel_id=999)


def test_list_messages_requires_membership():
    use_case = ListChannelMessages(
        messages=InMemoryMessages(), channels=InMemoryChannels(members=(1,))
    )
    with pytest.raises(AuthorizationError):
        use_case.execute(_actor(uid=2), channel_id=1)


def test_list_messages_paginates_with_has_more():
    messages = InMemoryMessages()
    for i in range(25):
        messages.save(
            Message(id=None, channel_id=1, sender_id=1, content=f"m{i}")
        )
    use_case = ListChannelMessages(
        messages=messages, channels=InMemoryChannels()
    )
    page1, has_more = use_case.execute(_actor(), channel_id=1, limit=20)
    assert len(page1) == 20
    assert has_more is True
    oldest = page1[0].id
    page2, has_more2 = use_case.execute(
        _actor(), channel_id=1, limit=20, before_id=oldest
    )
    assert len(page2) == 5
    assert has_more2 is False


def test_send_message_rejects_oversized_content():
    use_case = SendMessage(
        messages=InMemoryMessages(),
        channels=InMemoryChannels(members=(1,)),
        notifications=InMemoryNotifications(),
        realtime=FakeRealtime(),
        preferences=_all_enabled_prefs(),
    )
    with pytest.raises(ValidationError):
        use_case.execute(_actor(), channel_id=1, content="x" * 5001)


def _make_search_messages(messages, saved):
    for i, c in enumerate(messages):
        saved.save(Message(id=None, channel_id=1, sender_id=1, content=c))


def test_search_messages_not_found():
    use_case = SearchChannelMessages(
        messages=InMemoryMessages(), channels=InMemoryChannels()
    )
    with pytest.raises(NotFoundError):
        use_case.execute(_actor(), channel_id=999, query="hello")


def test_search_messages_requires_membership():
    use_case = SearchChannelMessages(
        messages=InMemoryMessages(), channels=InMemoryChannels(members=(1,))
    )
    with pytest.raises(AuthorizationError):
        use_case.execute(_actor(uid=2), channel_id=1, query="hello")


def test_search_messages_returns_matching_only():
    messages = InMemoryMessages()
    _make_search_messages(
        ["Hello world", "Bonjour le monde", "hello there"], messages
    )
    use_case = SearchChannelMessages(
        messages=messages, channels=InMemoryChannels(members=(1,))
    )
    results = use_case.execute(_actor(), channel_id=1, query="hello")
    assert [m.content for m in results] == ["Hello world", "hello there"]


def test_search_messages_rejects_empty_query():
    use_case = SearchChannelMessages(
        messages=InMemoryMessages(), channels=InMemoryChannels()
    )
    with pytest.raises(ValidationError):
        use_case.execute(_actor(), channel_id=1, query="   ")


def _add_message(repo, content, channel_id=1):
    return repo.save(
        Message(id=None, channel_id=channel_id, sender_id=1, content=content)
    )


def test_list_pinned_requires_membership():
    use_case = ListPinnedMessages(
        messages=InMemoryMessages(), channels=InMemoryChannels(members=(1,))
    )
    with pytest.raises(AuthorizationError):
        use_case.execute(_actor(uid=2), channel_id=1)


def test_list_pinned_returns_only_pinned():
    repo = InMemoryMessages()
    _add_message(repo, "a")
    pinned = _add_message(repo, "b")
    _add_message(repo, "c")
    repo.set_pinned(pinned.id, True)
    use_case = ListPinnedMessages(
        messages=repo, channels=InMemoryChannels(members=(1,))
    )
    results = use_case.execute(_actor(), channel_id=1)
    assert [m.id for m in results] == [pinned.id]


def test_pin_requires_teacher_or_admin():
    repo = InMemoryMessages()
    msg = _add_message(repo, "a")
    use_case = PinMessage(
        messages=repo, channels=InMemoryChannels(members=(1,))
    )
    with pytest.raises(AuthorizationError):
        use_case.execute(
            _actor(role=UserRole.PARENT), channel_id=1, message_id=msg.id, pinned=True
        )


def test_pin_toggles_state():
    repo = InMemoryMessages()
    msg = _add_message(repo, "a")
    use_case = PinMessage(
        messages=repo, channels=InMemoryChannels(members=(1,))
    )
    use_case.execute(_actor(), channel_id=1, message_id=msg.id, pinned=True)
    assert repo.items[0].is_pinned is True
    use_case.execute(_actor(), channel_id=1, message_id=msg.id, pinned=False)
    assert repo.items[0].is_pinned is False


def test_pin_message_not_found():
    use_case = PinMessage(
        messages=InMemoryMessages(), channels=InMemoryChannels(members=(1,))
    )
    with pytest.raises(NotFoundError):
        use_case.execute(_actor(), channel_id=1, message_id=999, pinned=True)


def test_pin_requires_membership():
    use_case = PinMessage(
        messages=InMemoryMessages(), channels=InMemoryChannels(members=(1,))
    )
    with pytest.raises(AuthorizationError):
        use_case.execute(_actor(uid=2), channel_id=1, message_id=1, pinned=True)
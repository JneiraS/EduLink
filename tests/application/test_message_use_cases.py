import pytest

from app.application.use_cases.message_use_cases import ListChannelMessages
from app.domain.entities.channel import Channel
from app.domain.entities.message import Message
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, NotFoundError


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
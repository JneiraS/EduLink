import pytest

from app.application.use_cases.channel_use_cases import (
    AddChannelMembers,
    CreateChannel,
    OpenDirectConversation,
)
from app.domain.entities.channel import Channel
from app.domain.entities.user import User, UserRole
from app.domain.errors import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)


class InMemoryChannels:
    def __init__(self):
        self.channels = []
        self.members = {}

    def create_with_members(self, channel, member_ids):
        channel.id = len(self.channels) + 1
        self.channels.append(channel)
        self.members[channel.id] = list(member_ids)
        return channel

    def find_by_id(self, channel_id):
        return next((c for c in self.channels if c.id == channel_id), None)

    def find_direct_between(self, user_a, user_b):
        for channel in self.channels:
            if channel.kind != "direct":
                continue
            if set(self.members.get(channel.id, [])) == {user_a, user_b}:
                return channel
        return None

    def _ensure_channel(self, channel_id):
        if not any(c.id == channel_id for c in self.channels):
            self.channels.append(Channel(id=channel_id, name=f"C{channel_id}", created_by=1))

    def is_member(self, channel_id, user_id):
        return user_id in self.members.get(channel_id, [])

    def add_member(self, channel_id, user_id):
        self.members.setdefault(channel_id, []).append(user_id)

    def list_member_ids(self, channel_id):
        return list(self.members.get(channel_id, []))


class InMemoryUsers:
    def __init__(self):
        self.users = []

    def find_by_id(self, user_id):
        return next((u for u in self.users if u.id == user_id), None)


def _actor(role=UserRole.TEACHER, uid=1):
    return User(
        id=uid, full_name="A", email="a@t.local", role=role,
        password_hash="x", is_active=True,
    )


def test_create_channel_requires_admin_or_teacher():
    use_case = CreateChannel(channels=InMemoryChannels())
    with pytest.raises(AuthorizationError):
        use_case.execute(_actor(UserRole.PARENT, 1), "C", [2])


def test_create_channel_requires_name():
    use_case = CreateChannel(channels=InMemoryChannels())
    with pytest.raises(ValidationError):
        use_case.execute(_actor(), "   ", [2])


def test_create_channel_rejects_oversized_name():
    use_case = CreateChannel(channels=InMemoryChannels())
    with pytest.raises(ValidationError):
        use_case.execute(_actor(), "x" * 121, [2])


def test_create_channel_adds_creator_and_members():
    channels = InMemoryChannels()
    use_case = CreateChannel(channels=channels)
    channel = use_case.execute(_actor(UserRole.TEACHER, 1), "Classe", [2, 3])
    assert channels.members[channel.id] == [1, 2, 3]


def test_add_channel_members_requires_manager():
    use_case = AddChannelMembers(channels=InMemoryChannels(), users=InMemoryUsers())
    with pytest.raises(AuthorizationError):
        use_case.execute(_actor(UserRole.PARENT, 1), 1, [2])


def test_add_channel_members_requires_membership():
    channels = InMemoryChannels()
    channels._ensure_channel(1)
    channels.members[1] = []
    use_case = AddChannelMembers(channels=channels, users=InMemoryUsers())
    with pytest.raises(AuthorizationError):
        use_case.execute(_actor(UserRole.ADMIN, 9), 1, [2])


def test_add_channel_members_rejects_unknown_user():
    channels = InMemoryChannels()
    channels._ensure_channel(1)
    channels.members[1] = [1]
    users = InMemoryUsers()
    users.users.append(_actor(UserRole.TEACHER, 2))
    use_case = AddChannelMembers(channels=channels, users=users)
    with pytest.raises(ValidationError):
        use_case.execute(_actor(UserRole.ADMIN, 1), 1, [999])


def test_add_channel_members_rejects_empty():
    channels = InMemoryChannels()
    channels._ensure_channel(1)
    channels.members[1] = [1]
    use_case = AddChannelMembers(channels=channels, users=InMemoryUsers())
    with pytest.raises(ValidationError):
        use_case.execute(_actor(UserRole.ADMIN, 1), 1, [])


def test_add_channel_members_rejects_direct_conversation():
    channels = InMemoryChannels()
    channels.channels.append(Channel(id=5, name="Parent", created_by=1, kind="direct"))
    channels.members[5] = [1, 2]
    use_case = AddChannelMembers(channels=channels, users=InMemoryUsers())
    with pytest.raises(ValidationError):
        use_case.execute(_actor(UserRole.ADMIN, 1), 5, [3])


def test_open_direct_conversation_creates():
    users = InMemoryUsers()
    users.users.append(_actor(UserRole.PARENT, 2))
    channels = InMemoryChannels()
    use_case = OpenDirectConversation(channels=channels, users=users)
    channel = use_case.execute(_actor(UserRole.TEACHER, 1), 2)
    assert channel.kind == "direct"
    assert channel.name == "A - A"
    assert set(channels.members[channel.id]) == {1, 2}


def test_open_direct_conversation_reuses_existing():
    users = InMemoryUsers()
    users.users.append(_actor(UserRole.PARENT, 2))
    channels = InMemoryChannels()
    existing = Channel(id=7, name="Parent", created_by=1, kind="direct")
    channels.channels.append(existing)
    channels.members[7] = [1, 2]
    use_case = OpenDirectConversation(channels=channels, users=users)
    channel = use_case.execute(_actor(UserRole.TEACHER, 1), 2)
    assert channel.id == 7


def test_open_direct_conversation_rejects_missing_user():
    use_case = OpenDirectConversation(
        channels=InMemoryChannels(), users=InMemoryUsers()
    )
    with pytest.raises(NotFoundError):
        use_case.execute(_actor(UserRole.TEACHER, 1), 999)


def test_open_direct_conversation_rejects_self():
    users = InMemoryUsers()
    users.users.append(_actor(UserRole.TEACHER, 1))
    use_case = OpenDirectConversation(channels=InMemoryChannels(), users=users)
    with pytest.raises(ValidationError):
        use_case.execute(_actor(UserRole.TEACHER, 1), 1)

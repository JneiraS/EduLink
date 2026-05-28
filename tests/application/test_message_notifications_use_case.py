from datetime import datetime

from app.application.use_cases.message_use_cases import SendMessage
from app.domain.entities.channel import Channel
from app.domain.entities.user import User, UserRole


class InMemoryMessageRepo:
    def __init__(self):
        self.items = []

    def save(self, message):
        message.id = len(self.items) + 1
        message.created_at = datetime.utcnow()
        self.items.append(message)
        return message

    def list_by_channel(self, channel_id):
        return [m for m in self.items if m.channel_id == channel_id]


class InMemoryChannelRepo:
    def __init__(self):
        self.channel = Channel(id=1, name="Classe A", created_by=1)
        self.members = [1, 2, 3]

    def create(self, channel):
        return self.channel

    def list_for_user(self, user_id):
        if user_id in self.members:
            return [self.channel]
        return []

    def add_member(self, channel_id, user_id):
        if user_id not in self.members:
            self.members.append(user_id)

    def is_member(self, channel_id, user_id):
        return channel_id == 1 and user_id in self.members

    def find_by_id(self, channel_id):
        return self.channel if channel_id == 1 else None

    def list_member_ids(self, channel_id):
        return list(self.members) if channel_id == 1 else []


class InMemoryNotificationRepo:
    def __init__(self):
        self.items = []

    def save(self, notification):
        notification.id = len(self.items) + 1
        notification.created_at = datetime.utcnow()
        self.items.append(notification)
        return notification

    def list_by_user(self, user_id):
        return [n for n in self.items if n.user_id == user_id]

    def mark_as_read(self, notification_id, user_id):
        for item in self.items:
            if item.id == notification_id and item.user_id == user_id:
                item.is_read = True
                return


class FakeRealtime:
    def __init__(self):
        self.user_events = []
        self.channel_events = []

    def notify_user(self, user_id, payload):
        self.user_events.append((user_id, payload))

    def notify_channel(self, channel_id, payload):
        self.channel_events.append((channel_id, payload))


def test_send_message_creates_notifications_for_other_members():
    use_case = SendMessage(
        messages=InMemoryMessageRepo(),
        channels=InMemoryChannelRepo(),
        notifications=InMemoryNotificationRepo(),
        realtime=FakeRealtime(),
    )

    actor = User(
        id=1,
        full_name="Teacher",
        email="teacher@test.local",
        role=UserRole.TEACHER,
        password_hash="hash",
        is_active=True,
    )

    message = use_case.execute(actor=actor, channel_id=1, content="Bonjour la classe")

    assert message.id == 1
    assert len(use_case.notifications.items) == 2
    assert sorted([n.user_id for n in use_case.notifications.items]) == [2, 3]
    assert len(use_case.realtime.user_events) == 2
    assert len(use_case.realtime.channel_events) == 1

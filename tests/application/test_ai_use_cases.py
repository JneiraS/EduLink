import pytest

from app.application.use_cases.ai_use_cases import (
    RephraseDraft,
    SummarizeChannelMessages,
)
from app.domain.entities.channel import Channel
from app.domain.entities.message import Message
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, NotFoundError, ValidationError


class InMemoryMessages:
    def __init__(self, items=()):
        self.items = list(items)

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


class FakeAssistant:
    def __init__(self, reply="Resume du fil", rephrase_reply="Version reformulee"):
        self.calls = []
        self.rephrase_calls = []
        self.reply = reply
        self.rephrase_reply = rephrase_reply

    def summarize(self, texts):
        self.calls.append(list(texts))
        return self.reply

    def rephrase(self, text):
        self.rephrase_calls.append(text)
        return self.rephrase_reply


def _actor(uid=1, role=UserRole.TEACHER):
    return User(
        id=uid,
        full_name="A",
        email=f"{uid}@t.local",
        role=role,
        password_hash="x",
        is_active=True,
    )


def _message(mid, content, channel_id=1, sender_id=1):
    return Message(
        id=mid, channel_id=channel_id, sender_id=sender_id, content=content
    )


def test_summary_requires_membership():
    use_case = SummarizeChannelMessages(
        messages=InMemoryMessages([_message(1, "Bonjour")]),
        channels=InMemoryChannels(members=(1,)),
        assistant=FakeAssistant(),
    )
    with pytest.raises(AuthorizationError):
        use_case.execute(_actor(uid=2), channel_id=1)


def test_summary_unknown_channel_raises_not_found():
    use_case = SummarizeChannelMessages(
        messages=InMemoryMessages(),
        channels=InMemoryChannels(),
        assistant=FakeAssistant(),
    )
    with pytest.raises(NotFoundError):
        use_case.execute(_actor(), channel_id=99)


def test_summary_empty_channel_raises_validation_error():
    use_case = SummarizeChannelMessages(
        messages=InMemoryMessages(),
        channels=InMemoryChannels(),
        assistant=FakeAssistant(),
    )
    with pytest.raises(ValidationError):
        use_case.execute(_actor(), channel_id=1)


def test_summary_returns_assistant_reply_with_message_contents():
    messages = InMemoryMessages(
        [_message(1, "Bonjour"), _message(2, "Reunion lundi")]
    )
    assistant = FakeAssistant(reply="- Reunion lundi")
    use_case = SummarizeChannelMessages(
        messages=messages, channels=InMemoryChannels(), assistant=assistant
    )

    result = use_case.execute(_actor(), channel_id=1)

    assert result == "- Reunion lundi"
    assert assistant.calls == [["Bonjour", "Reunion lundi"]]


def test_summary_limits_messages_sent_to_assistant():
    items = [_message(i, f"Message {i}") for i in range(1, 61)]
    assistant = FakeAssistant()
    use_case = SummarizeChannelMessages(
        messages=InMemoryMessages(items),
        channels=InMemoryChannels(),
        assistant=assistant,
    )

    use_case.execute(_actor(), channel_id=1)

    assert len(assistant.calls[0]) == 50


def test_rephrase_returns_assistant_suggestion():
    assistant = FakeAssistant(rephrase_reply="Bonjour, pourrions-nous en discuter ?")
    use_case = RephraseDraft(assistant=assistant)

    result = use_case.execute(content="  Donnez-moi reponse vite  ")

    assert result == "Bonjour, pourrions-nous en discuter ?"
    assert assistant.rephrase_calls == ["Donnez-moi reponse vite"]


def test_rephrase_empty_content_raises_validation_error():
    use_case = RephraseDraft(assistant=FakeAssistant())
    with pytest.raises(ValidationError):
        use_case.execute(content="   ")


def test_rephrase_too_long_content_raises_validation_error():
    use_case = RephraseDraft(assistant=FakeAssistant())
    with pytest.raises(ValidationError):
        use_case.execute(content="a" * 5001)

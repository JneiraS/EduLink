from dataclasses import dataclass

from app.application.use_cases.message_use_cases import (
    MAX_MESSAGE_LENGTH,
    _assert_channel_access,
)
from app.domain.entities.user import User
from app.domain.errors import ValidationError
from app.domain.ports.repositories import (
    ChannelRepositoryPort,
    MessageRepositoryPort,
)
from app.domain.ports.services import TextAssistantPort

SUMMARY_LIMIT = 50


@dataclass(slots=True)
class SummarizeChannelMessages:
    messages: MessageRepositoryPort
    channels: ChannelRepositoryPort
    assistant: TextAssistantPort

    def execute(
        self, actor: User, channel_id: int, limit: int = SUMMARY_LIMIT
    ) -> str:
        _assert_channel_access(self.channels, actor, channel_id)
        messages, _ = self.messages.list_by_channel(channel_id, limit)
        if not messages:
            raise ValidationError("Aucun message à résumer")
        return self.assistant.summarize([m.content for m in messages])


@dataclass(slots=True)
class RephraseDraft:
    assistant: TextAssistantPort

    def execute(self, content: str) -> str:
        content = content.strip()
        if not content:
            raise ValidationError("Le contenu du message est requis")
        if len(content) > MAX_MESSAGE_LENGTH:
            raise ValidationError(
                f"Le message ne doit pas dépasser {MAX_MESSAGE_LENGTH} caractères"
            )
        return self.assistant.rephrase(content)

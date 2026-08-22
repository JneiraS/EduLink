from dataclasses import dataclass

from app.domain.entities.message_template import MessageTemplate
from app.domain.entities.user import User
from app.domain.errors import AuthorizationError, ValidationError
from app.domain.ports.repositories import MessageTemplateRepositoryPort

MAX_LABEL_LENGTH = 80
MAX_TEMPLATE_CONTENT_LENGTH = 5000


@dataclass(slots=True)
class ListMessageTemplates:
    templates: MessageTemplateRepositoryPort

    def execute(self, actor: User) -> list[MessageTemplate]:
        return self.templates.list_by_owner(actor.id or 0)


@dataclass(slots=True)
class CreateMessageTemplate:
    templates: MessageTemplateRepositoryPort

    def execute(self, actor: User, label: str, content: str) -> MessageTemplate:
        label = label.strip()
        content = content.strip()
        if not label:
            raise ValidationError("Label is required")
        if len(label) > MAX_LABEL_LENGTH:
            raise ValidationError(
                f"Label must be at most {MAX_LABEL_LENGTH} characters"
            )
        if not content:
            raise ValidationError("Content is required")
        if len(content) > MAX_TEMPLATE_CONTENT_LENGTH:
            raise ValidationError(
                f"Content must be at most {MAX_TEMPLATE_CONTENT_LENGTH} characters"
            )
        return self.templates.save(
            MessageTemplate(
                id=None,
                owner_id=actor.id or 0,
                label=label,
                content=content,
            )
        )


@dataclass(slots=True)
class DeleteMessageTemplate:
    templates: MessageTemplateRepositoryPort

    def execute(self, actor: User, template_id: int) -> None:
        template = self.templates.find_by_id(template_id)
        if template is None:
            return
        if template.owner_id != (actor.id or 0):
            raise AuthorizationError("Only the owner can delete this template")
        self.templates.delete(template_id)


@dataclass(slots=True)
class UpdateMessageTemplate:
    templates: MessageTemplateRepositoryPort

    def execute(
        self, actor: User, template_id: int, label: str, content: str
    ) -> MessageTemplate:
        label = label.strip()
        content = content.strip()
        if not label:
            raise ValidationError("Label is required")
        if len(label) > MAX_LABEL_LENGTH:
            raise ValidationError(
                f"Label must be at most {MAX_LABEL_LENGTH} characters"
            )
        if not content:
            raise ValidationError("Content is required")
        if len(content) > MAX_TEMPLATE_CONTENT_LENGTH:
            raise ValidationError(
                f"Content must be at most {MAX_TEMPLATE_CONTENT_LENGTH} characters"
            )
        template = self.templates.find_by_id(template_id)
        if template is None:
            raise ValidationError("Template not found")
        if template.owner_id != (actor.id or 0):
            raise AuthorizationError("Only the owner can edit this template")
        return self.templates.update(template_id, label, content)
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
            raise ValidationError("Le libellé est requis")
        if len(label) > MAX_LABEL_LENGTH:
            raise ValidationError(
                f"Le libellé ne doit pas dépasser {MAX_LABEL_LENGTH} caractères"
            )
        if not content:
            raise ValidationError("Le contenu est requis")
        if len(content) > MAX_TEMPLATE_CONTENT_LENGTH:
            raise ValidationError(
                f"Le contenu ne doit pas dépasser {MAX_TEMPLATE_CONTENT_LENGTH} caractères"
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
            raise AuthorizationError("Seul le propriétaire peut supprimer ce modèle")
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
            raise ValidationError("Le libellé est requis")
        if len(label) > MAX_LABEL_LENGTH:
            raise ValidationError(
                f"Le libellé ne doit pas dépasser {MAX_LABEL_LENGTH} caractères"
            )
        if not content:
            raise ValidationError("Le contenu est requis")
        if len(content) > MAX_TEMPLATE_CONTENT_LENGTH:
            raise ValidationError(
                f"Le contenu ne doit pas dépasser {MAX_TEMPLATE_CONTENT_LENGTH} caractères"
            )
        template = self.templates.find_by_id(template_id)
        if template is None:
            raise ValidationError("Modèle introuvable")
        if template.owner_id != (actor.id or 0):
            raise AuthorizationError("Seul le propriétaire peut modifier ce modèle")
        return self.templates.update(template_id, label, content)
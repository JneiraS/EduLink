from app.domain.entities.message_template import MessageTemplate
from app.domain.ports.repositories import MessageTemplateRepositoryPort
from app.extensions import db
from app.infrastructure.database.models import MessageTemplateModel


class SQLAlchemyMessageTemplateRepository(MessageTemplateRepositoryPort):
    def save(self, template: MessageTemplate) -> MessageTemplate:
        model = MessageTemplateModel(
            owner_id=template.owner_id,
            label=template.label,
            content=template.content,
        )
        db.session.add(model)
        db.session.commit()
        return self._to_entity(model)

    def list_by_owner(self, owner_id: int) -> list[MessageTemplate]:
        rows = (
            MessageTemplateModel.query.filter_by(owner_id=owner_id)
            .order_by(MessageTemplateModel.created_at.desc())
            .all()
        )
        return [self._to_entity(row) for row in rows]

    def find_by_id(self, template_id: int) -> MessageTemplate | None:
        row = db.session.get(MessageTemplateModel, template_id)
        return self._to_entity(row) if row else None

    def delete(self, template_id: int) -> MessageTemplate | None:
        row = db.session.get(MessageTemplateModel, template_id)
        if row is None:
            return None
        entity = self._to_entity(row)
        db.session.delete(row)
        db.session.commit()
        return entity

    def _to_entity(self, row: MessageTemplateModel) -> MessageTemplate:
        return MessageTemplate(
            id=row.id,
            owner_id=row.owner_id,
            label=row.label,
            content=row.content,
            created_at=row.created_at,
        )
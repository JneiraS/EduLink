from app.domain.entities.message import Message
from app.domain.ports.repositories import MessageRepositoryPort
from app.extensions import db
from app.infrastructure.database.models import MessageModel


class SQLAlchemyMessageRepository(MessageRepositoryPort):
    def save(self, message: Message) -> Message:
        model = MessageModel(
            channel_id=message.channel_id,
            sender_id=message.sender_id,
            content=message.content,
        )
        db.session.add(model)
        db.session.commit()
        return self._to_entity(model)

    def list_by_channel(self, channel_id: int) -> list[Message]:
        rows = (
            MessageModel.query.filter_by(channel_id=channel_id)
            .order_by(MessageModel.created_at.asc())
            .all()
        )
        return [self._to_entity(row) for row in rows]

    def _to_entity(self, model: MessageModel) -> Message:
        return Message(
            id=model.id,
            channel_id=model.channel_id,
            sender_id=model.sender_id,
            content=model.content,
            created_at=model.created_at,
        )

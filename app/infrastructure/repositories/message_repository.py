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

    def list_by_channel(
        self, channel_id: int, limit: int, before_id: int | None = None
    ) -> tuple[list[Message], bool]:
        query = MessageModel.query.filter_by(channel_id=channel_id)
        if before_id is not None:
            query = query.filter(MessageModel.id < before_id)
        rows = query.order_by(MessageModel.id.desc()).limit(limit + 1).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        # Newest first for stable page slices; re-sort ascending for display.
        rows.reverse()
        return [self._to_entity(row) for row in rows], has_more

    def search_by_channel(
        self, channel_id: int, query: str, limit: int = 50
    ) -> list[Message]:
        pattern = f"%{query}%"
        rows = (
            MessageModel.query.filter_by(channel_id=channel_id)
            .filter(MessageModel.content.ilike(pattern))
            .order_by(MessageModel.id.desc())
            .limit(limit)
            .all()
        )
        rows.reverse()
        return [self._to_entity(row) for row in rows]

    def _to_entity(self, model: MessageModel) -> Message:
        return Message(
            id=model.id,
            channel_id=model.channel_id,
            sender_id=model.sender_id,
            content=model.content,
            created_at=model.created_at,
        )

from app.domain.entities.message import Message
from app.domain.ports.repositories import MessageRepositoryPort
from app.extensions import db
from app.infrastructure.database.models import ChannelModel, MessageModel
from app.infrastructure.repositories._date_utils import parse_date


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
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        rows = (
            MessageModel.query.filter_by(channel_id=channel_id)
            .filter(MessageModel.content.ilike(pattern, escape="\\"))
            .order_by(MessageModel.id.desc())
            .limit(limit)
            .all()
        )
        rows.reverse()
        return [self._to_entity(row) for row in rows]

    def find_by_id(self, message_id: int) -> Message | None:
        model = db.session.get(MessageModel, message_id)
        return self._to_entity(model) if model else None

    def set_pinned(self, message_id: int, pinned: bool) -> Message | None:
        model = db.session.get(MessageModel, message_id)
        if model is None:
            return None
        model.is_pinned = pinned
        db.session.commit()
        return self._to_entity(model)

    def list_pinned(self, channel_id: int) -> list[Message]:
        rows = (
            MessageModel.query.filter_by(channel_id=channel_id, is_pinned=True)
            .order_by(MessageModel.created_at.desc())
            .all()
        )
        rows.reverse()
        return [self._to_entity(row) for row in rows]

    def list_latest_by_channels(self, channel_ids: list[int]) -> dict[int, Message]:
        if not channel_ids:
            return {}
        latest_ids = (
            db.session.query(MessageModel.channel_id, db.func.max(MessageModel.id))
            .filter(MessageModel.channel_id.in_(channel_ids))
            .group_by(MessageModel.channel_id)
            .all()
        )
        rows = (
            MessageModel.query.filter(
                MessageModel.id.in_([message_id for _, message_id in latest_ids])
            )
            .all()
        )
        by_id = {row.id: self._to_entity(row) for row in rows}
        return {
            channel_id: by_id[message_id]
            for channel_id, message_id in latest_ids
            if message_id in by_id
        }

    def count_grouped_by_date(self, since: datetime) -> list[dict]:
        rows = (
            db.session.query(
                db.func.date(MessageModel.created_at).label("day"),
                db.func.count(MessageModel.id),
            )
            .filter(MessageModel.created_at >= since)
            .group_by(db.func.date(MessageModel.created_at))
            .all()
        )
        return [
            {"date": parse_date(row[0]), "count": row[1]} for row in rows
        ]

    def count_top_channels(self, limit: int = 5) -> list[dict]:
        rows = (
            db.session.query(
                MessageModel.channel_id,
                ChannelModel.name,
                db.func.count(MessageModel.id),
            )
            .join(ChannelModel, ChannelModel.id == MessageModel.channel_id)
            .group_by(MessageModel.channel_id, ChannelModel.name)
            .order_by(db.func.count(MessageModel.id).desc())
            .limit(limit)
            .all()
        )
        return [
            {"channel_id": channel_id, "channel_name": name, "count": count}
            for channel_id, name, count in rows
        ]

    def _to_entity(self, model: MessageModel) -> Message:
        return Message(
            id=model.id,
            channel_id=model.channel_id,
            sender_id=model.sender_id,
            content=model.content,
            created_at=model.created_at,
            is_pinned=model.is_pinned,
        )

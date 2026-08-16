from sqlalchemy import delete, select

from app.domain.entities.channel import Channel
from app.domain.ports.repositories import ChannelRepositoryPort
from app.extensions import db
from app.infrastructure.database.models import (
    ChannelModel,
    MessageModel,
    NotificationModel,
    channel_members,
)


class SQLAlchemyChannelRepository(ChannelRepositoryPort):
    def create(self, channel: Channel) -> Channel:
        model = ChannelModel(name=channel.name, created_by=channel.created_by)
        db.session.add(model)
        db.session.commit()
        return Channel(id=model.id, name=model.name, created_by=model.created_by)

    def create_with_members(
        self, channel: Channel, member_ids: list[int]
    ) -> Channel:
        model = ChannelModel(name=channel.name, created_by=channel.created_by)
        db.session.add(model)
        db.session.flush()
        for member_id in dict.fromkeys(member_ids):
            db.session.execute(
                channel_members.insert().values(
                    channel_id=model.id, user_id=member_id
                )
            )
        db.session.commit()
        return Channel(id=model.id, name=model.name, created_by=model.created_by)

    def list_for_user(self, user_id: int) -> list[Channel]:
        rows = (
            db.session.query(ChannelModel)
            .join(channel_members, ChannelModel.id == channel_members.c.channel_id)
            .filter(channel_members.c.user_id == user_id)
            .order_by(ChannelModel.name.asc())
            .all()
        )
        return [Channel(id=r.id, name=r.name, created_by=r.created_by) for r in rows]

    def add_member(self, channel_id: int, user_id: int) -> None:
        exists_stmt = (
            select(channel_members.c.channel_id)
            .where(channel_members.c.channel_id == channel_id)
            .where(channel_members.c.user_id == user_id)
        )
        existing = db.session.execute(exists_stmt).first()
        if existing:
            return

        db.session.execute(
            channel_members.insert().values(channel_id=channel_id, user_id=user_id)
        )
        db.session.commit()

    def is_member(self, channel_id: int, user_id: int) -> bool:
        stmt = (
            select(channel_members.c.channel_id)
            .where(channel_members.c.channel_id == channel_id)
            .where(channel_members.c.user_id == user_id)
        )
        return db.session.execute(stmt).first() is not None

    def find_by_id(self, channel_id: int) -> Channel | None:
        row = db.session.get(ChannelModel, channel_id)
        if not row:
            return None
        return Channel(id=row.id, name=row.name, created_by=row.created_by)

    def list_all(self) -> list[Channel]:
        rows = ChannelModel.query.order_by(ChannelModel.created_at.desc()).all()
        return [Channel(id=r.id, name=r.name, created_by=r.created_by) for r in rows]

    def delete(self, channel_id: int) -> Channel | None:
        row = db.session.get(ChannelModel, channel_id)
        if row is None:
            return None
        entity = Channel(id=row.id, name=row.name, created_by=row.created_by)

        db.session.execute(
            delete(channel_members).where(channel_members.c.channel_id == channel_id)
        )
        db.session.execute(
            delete(MessageModel).where(MessageModel.channel_id == channel_id)
        )
        db.session.execute(
            delete(NotificationModel).where(
                NotificationModel.channel_id == channel_id
            )
        )
        db.session.delete(row)
        db.session.commit()
        return entity

    def list_member_ids(self, channel_id: int) -> list[int]:
        stmt = select(channel_members.c.user_id).where(
            channel_members.c.channel_id == channel_id
        )
        rows = db.session.execute(stmt).all()
        return [row[0] for row in rows]

from sqlalchemy import delete as sa_delete
from sqlalchemy import select

from app.domain.entities.announcement import Announcement
from app.domain.ports.repositories import AnnouncementRepositoryPort
from app.extensions import db
from app.infrastructure.database.models import (
    AnnouncementModel,
    AnnouncementReadModel,
    announcement_channels,
)


class SQLAlchemyAnnouncementRepository(AnnouncementRepositoryPort):
    def save(self, announcement: Announcement) -> Announcement:
        model = AnnouncementModel(
            title=announcement.title,
            content=announcement.content,
            created_by=announcement.created_by,
            pdf_filename=announcement.pdf_filename,
        )
        db.session.add(model)
        db.session.flush()
        for channel_id in announcement.target_channel_ids:
            db.session.execute(
                announcement_channels.insert().values(
                    announcement_id=model.id, channel_id=channel_id
                )
            )
        db.session.commit()
        return self._to_entity(model)

    def find_by_id(self, announcement_id: int) -> Announcement | None:
        model = db.session.get(AnnouncementModel, announcement_id)
        return self._to_entity(model) if model else None

    def delete(self, announcement_id: int) -> Announcement | None:
        model = db.session.get(AnnouncementModel, announcement_id)
        if model is None:
            return None
        entity = self._to_entity(model)
        db.session.execute(
            sa_delete(AnnouncementReadModel).where(
                AnnouncementReadModel.announcement_id == announcement_id
            )
        )
        db.session.execute(
            sa_delete(announcement_channels).where(
                announcement_channels.c.announcement_id == announcement_id
            )
        )
        db.session.delete(model)
        db.session.commit()
        return entity

    def list_all(self) -> list[Announcement]:
        rows = AnnouncementModel.query.order_by(
            AnnouncementModel.created_at.desc()
        ).all()
        return [self._to_entity(row) for row in rows]

    def paginate(self, page: int, per_page: int) -> tuple[list[Announcement], int]:
        total = AnnouncementModel.query.count()
        rows = (
            AnnouncementModel.query.order_by(AnnouncementModel.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return [self._to_entity(row) for row in rows], total

    def _target_channel_ids(self, announcement_id: int) -> list[int]:
        stmt = (
            select(announcement_channels.c.channel_id)
            .where(announcement_channels.c.announcement_id == announcement_id)
            .order_by(announcement_channels.c.channel_id)
        )
        return [row[0] for row in db.session.execute(stmt).all()]

    def mark_read(self, announcement_id: int, user_id: int) -> None:
        existing = db.session.get(AnnouncementReadModel, (announcement_id, user_id))
        if existing:
            return
        db.session.add(
            AnnouncementReadModel(announcement_id=announcement_id, user_id=user_id)
        )
        db.session.commit()

    def is_read(self, announcement_id: int, user_id: int) -> bool:
        return (
            db.session.get(AnnouncementReadModel, (announcement_id, user_id))
            is not None
        )

    def count_read(self, announcement_id: int) -> int:
        return AnnouncementReadModel.query.filter_by(
            announcement_id=announcement_id
        ).count()

    def _to_entity(self, model: AnnouncementModel) -> Announcement:
        return Announcement(
            id=model.id,
            title=model.title,
            content=model.content,
            created_by=model.created_by,
            pdf_filename=model.pdf_filename,
            created_at=model.created_at,
            target_channel_ids=self._target_channel_ids(model.id),
        )

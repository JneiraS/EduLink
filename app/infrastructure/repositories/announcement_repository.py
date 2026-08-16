from app.domain.entities.announcement import Announcement
from app.domain.ports.repositories import AnnouncementRepositoryPort
from app.extensions import db
from app.infrastructure.database.models import AnnouncementModel


class SQLAlchemyAnnouncementRepository(AnnouncementRepositoryPort):
    def save(self, announcement: Announcement) -> Announcement:
        model = AnnouncementModel(
            title=announcement.title,
            content=announcement.content,
            created_by=announcement.created_by,
            pdf_filename=announcement.pdf_filename,
        )
        db.session.add(model)
        db.session.commit()
        return self._to_entity(model)

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

    def _to_entity(self, model: AnnouncementModel) -> Announcement:
        return Announcement(
            id=model.id,
            title=model.title,
            content=model.content,
            created_by=model.created_by,
            pdf_filename=model.pdf_filename,
            created_at=model.created_at,
        )

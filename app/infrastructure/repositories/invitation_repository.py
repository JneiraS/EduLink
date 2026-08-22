from app.domain.entities.invitation import Invitation
from app.domain.ports.repositories import InvitationRepositoryPort
from app.extensions import db
from app.infrastructure.database.models import InvitationModel, utc_now


class SQLAlchemyInvitationRepository(InvitationRepositoryPort):
    def create(self, invitation: Invitation) -> Invitation:
        model = InvitationModel(
            user_id=invitation.user_id,
            token=invitation.token,
            expires_at=invitation.expires_at,
            used_at=invitation.used_at,
        )
        db.session.add(model)
        db.session.commit()
        return self._to_entity(model)

    def find_by_token(self, token: str) -> Invitation | None:
        row = InvitationModel.query.filter_by(token=token).first()
        return self._to_entity(row) if row else None

    def find_active_by_user(self, user_id: int) -> Invitation | None:
        now = utc_now()
        row = (
            InvitationModel.query.filter(
                InvitationModel.user_id == user_id,
                InvitationModel.used_at.is_(None),
                InvitationModel.expires_at > now,
            )
            .order_by(InvitationModel.expires_at.desc())
            .first()
        )
        return self._to_entity(row) if row else None

    def mark_used(self, invitation_id: int) -> None:
        row = db.session.get(InvitationModel, invitation_id)
        if row is not None and row.used_at is None:
            row.used_at = utc_now()
            db.session.commit()

    def _to_entity(self, row: InvitationModel) -> Invitation:
        return Invitation(
            id=row.id,
            user_id=row.user_id,
            token=row.token,
            expires_at=row.expires_at,
            used_at=row.used_at,
            created_at=row.created_at,
        )
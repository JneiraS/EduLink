from app.domain.entities.push_subscription import PushSubscription
from app.domain.ports.repositories import PushSubscriptionRepositoryPort
from app.extensions import db
from app.infrastructure.database.models import PushSubscriptionModel


class SQLAlchemyPushSubscriptionRepository(PushSubscriptionRepositoryPort):
    def save_for_user(
        self,
        user_id: int,
        endpoint: str,
        p256dh_key: str,
        auth_key: str,
    ) -> PushSubscription:
        model = PushSubscriptionModel.query.filter_by(endpoint=endpoint).first()
        if model:
            model.user_id = user_id
            model.p256dh_key = p256dh_key
            model.auth_key = auth_key
        else:
            model = PushSubscriptionModel(
                user_id=user_id,
                endpoint=endpoint,
                p256dh_key=p256dh_key,
                auth_key=auth_key,
            )
            db.session.add(model)

        db.session.commit()
        return self._to_entity(model)

    def list_by_user(self, user_id: int) -> list[PushSubscription]:
        rows = PushSubscriptionModel.query.filter_by(user_id=user_id).all()
        return [self._to_entity(row) for row in rows]

    def delete_by_endpoint(self, endpoint: str) -> None:
        model = PushSubscriptionModel.query.filter_by(endpoint=endpoint).first()
        if not model:
            return
        db.session.delete(model)
        db.session.commit()

    def delete_for_user(self, user_id: int, endpoint: str) -> None:
        model = PushSubscriptionModel.query.filter_by(
            user_id=user_id, endpoint=endpoint
        ).first()
        if not model:
            return
        db.session.delete(model)
        db.session.commit()

    def count_distinct_users(self) -> int:
        return (
            db.session.query(PushSubscriptionModel.user_id)
            .distinct()
            .count()
        )

    def _to_entity(self, model: PushSubscriptionModel) -> PushSubscription:
        return PushSubscription(
            id=model.id,
            user_id=model.user_id,
            endpoint=model.endpoint,
            p256dh_key=model.p256dh_key,
            auth_key=model.auth_key,
            created_at=model.created_at,
        )

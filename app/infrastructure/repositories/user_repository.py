from app.domain.entities.user import User, UserRole
from app.domain.ports.repositories import UserRepositoryPort
from app.extensions import db
from app.infrastructure.database.models import UserModel


class SQLAlchemyUserRepository(UserRepositoryPort):
    def save(self, user: User) -> User:
        if user.id is None:
            model = UserModel(
                full_name=user.full_name,
                email=user.email,
                role=user.role.value,
                password_hash=user.password_hash,
                is_active=user.is_active,
            )
            db.session.add(model)
        else:
            model = db.session.get(UserModel, user.id)
            model.full_name = user.full_name
            model.email = user.email
            model.role = user.role.value
            model.password_hash = user.password_hash
            model.is_active = user.is_active

        db.session.commit()
        return self._to_entity(model)

    def find_by_email(self, email: str) -> User | None:
        model = UserModel.query.filter_by(email=email).first()
        return self._to_entity(model) if model else None

    def find_by_id(self, user_id: int) -> User | None:
        model = db.session.get(UserModel, user_id)
        return self._to_entity(model) if model else None

    def find_many_by_ids(self, user_ids: list[int]) -> list[User]:
        models = UserModel.query.filter(UserModel.id.in_(user_ids)).all()
        return [self._to_entity(model) for model in models]

    def list_users(self) -> list[User]:
        return [
            self._to_entity(model)
            for model in UserModel.query.order_by(UserModel.created_at.desc()).all()
        ]

    def get_auth_model(self, user_id: int) -> UserModel:
        # Adapter-specific Flask-Login handoff: login_user() needs the ORM
        # UserMixin instance, so the concrete repo exposes it here (not on the
        # abstract port, keeping the domain layer free of ORM types).
        return db.session.get(UserModel, user_id)

    def _to_entity(self, model: UserModel) -> User:
        return User(
            id=model.id,
            full_name=model.full_name,
            email=model.email,
            role=UserRole(model.role),
            password_hash=model.password_hash,
            is_active=model.is_active,
            created_at=model.created_at,
        )

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

    def list_users(self) -> list[User]:
        return [
            self._to_entity(model)
            for model in UserModel.query.order_by(UserModel.created_at.desc()).all()
        ]

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

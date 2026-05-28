from app import create_app
from app.domain.entities.user import User, UserRole
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository


def test_user_repository_save_and_find():
    app = create_app(testing=True)

    with app.app_context():
        repo = SQLAlchemyUserRepository()
        saved = repo.save(
            User(
                id=None,
                full_name="Test User",
                email="test.user@edulink.local",
                role=UserRole.PARENT,
                password_hash="hashed",
                is_active=True,
            )
        )

        found = repo.find_by_email("test.user@edulink.local")

        assert saved.id is not None
        assert found is not None
        assert found.full_name == "Test User"

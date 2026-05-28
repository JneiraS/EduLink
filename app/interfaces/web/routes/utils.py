from flask import current_app
from flask_login import current_user

from app.application.container import UseCaseContainer
from app.domain.entities.user import User, UserRole


def get_use_cases() -> UseCaseContainer:
    return current_app.extensions["use_cases"]


def current_actor() -> User:
    return User(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
        role=UserRole(current_user.role),
        password_hash=current_user.password_hash,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )

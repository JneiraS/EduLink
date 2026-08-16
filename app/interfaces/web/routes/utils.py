from flask import current_app
from flask_login import current_user

from app.application.container import UseCaseContainer
from app.domain.entities.user import User


def get_use_cases() -> UseCaseContainer:
    return current_app.extensions["use_cases"]


def get_services() -> dict:
    return current_app.extensions["services"]


def current_actor() -> User:
    return get_services()["users"].find_by_id(current_user.id)

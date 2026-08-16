import re
from dataclasses import dataclass

from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthenticationError, AuthorizationError, ValidationError
from app.domain.ports.repositories import UserRepositoryPort
from app.domain.ports.services import PasswordHasherPort

MAX_FULL_NAME_LENGTH = 120
MAX_EMAIL_LENGTH = 254
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(slots=True)
class RegisterUser:
    users: UserRepositoryPort
    hasher: PasswordHasherPort

    def execute(
        self,
        actor: User,
        full_name: str,
        email: str,
        role: str,
        plain_password: str,
    ) -> User:
        if actor.role != UserRole.ADMIN:
            raise AuthorizationError("Only admin can create accounts")
        if not full_name.strip() or not email.strip() or not plain_password.strip():
            raise ValidationError("All fields are required")

        full_name = full_name.strip()
        email = email.strip()
        if len(full_name) > MAX_FULL_NAME_LENGTH:
            raise ValidationError(
                f"Full name must be at most {MAX_FULL_NAME_LENGTH} characters"
            )
        if len(email) > MAX_EMAIL_LENGTH:
            raise ValidationError("Email is too long")
        if not _EMAIL_RE.match(email):
            raise ValidationError("Invalid email address")
        if not (MIN_PASSWORD_LENGTH <= len(plain_password) <= MAX_PASSWORD_LENGTH):
            raise ValidationError(
                f"Password must be between {MIN_PASSWORD_LENGTH} and "
                f"{MAX_PASSWORD_LENGTH} characters"
            )
        if self.users.find_by_email(email.lower()):
            raise ValidationError("Email already exists")

        try:
            role_enum = UserRole(role)
        except ValueError as exc:
            raise ValidationError("Invalid role") from exc

        password_hash = self.hasher.hash_password(plain_password)
        user = User(
            id=None,
            full_name=full_name,
            email=email.lower(),
            role=role_enum,
            password_hash=password_hash,
            is_active=True,
        )
        return self.users.save(user)


@dataclass(slots=True)
class LoginUser:
    users: UserRepositoryPort
    hasher: PasswordHasherPort

    def execute(self, email: str, plain_password: str) -> User:
        user = self.users.find_by_email(email.strip().lower())
        if user is None:
            raise AuthenticationError("Invalid credentials")
        if not self.hasher.verify_password(plain_password, user.password_hash):
            raise AuthenticationError("Invalid credentials")
        if not user.is_active:
            raise AuthenticationError("Account disabled")
        return user

from dataclasses import dataclass

from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthenticationError, AuthorizationError, ValidationError
from app.domain.ports.repositories import UserRepositoryPort
from app.domain.ports.services import PasswordHasherPort


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
        if self.users.find_by_email(email):
            raise ValidationError("Email already exists")

        try:
            role_enum = UserRole(role)
        except ValueError as exc:
            raise ValidationError("Invalid role") from exc

        password_hash = self.hasher.hash_password(plain_password)
        user = User(
            id=None,
            full_name=full_name.strip(),
            email=email.strip().lower(),
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

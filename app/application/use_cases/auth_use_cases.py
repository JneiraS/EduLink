import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.domain.entities.invitation import Invitation
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthenticationError, AuthorizationError, ValidationError
from app.domain.ports.repositories import InvitationRepositoryPort, UserRepositoryPort
from app.domain.ports.services import PasswordHasherPort

MAX_FULL_NAME_LENGTH = 120
MAX_EMAIL_LENGTH = 254
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
DEFAULT_INVITATION_TTL_HOURS = 72

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _now() -> datetime:
    utc_zone = getattr(datetime, "UTC", timezone.utc)
    return datetime.now(utc_zone)


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _validate_profile(full_name: str, email: str, role: str) -> tuple[str, str, UserRole]:
    if not full_name.strip() or not email.strip():
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

    try:
        role_enum = UserRole(role)
    except ValueError as exc:
        raise ValidationError("Invalid role") from exc

    return full_name, email.lower(), role_enum


def _validate_password(plain_password: str) -> str:
    plain_password = plain_password.strip()
    if not plain_password:
        raise ValidationError("All fields are required")
    if not (MIN_PASSWORD_LENGTH <= len(plain_password) <= MAX_PASSWORD_LENGTH):
        raise ValidationError(
            f"Password must be between {MIN_PASSWORD_LENGTH} and "
            f"{MAX_PASSWORD_LENGTH} characters"
        )
    return plain_password


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

        full_name, email, role_enum = _validate_profile(full_name, email, role)
        plain_password = _validate_password(plain_password)
        if self.users.find_by_email(email):
            raise ValidationError("Email already exists")

        password_hash = self.hasher.hash_password(plain_password)
        user = User(
            id=None,
            full_name=full_name,
            email=email,
            role=role_enum,
            password_hash=password_hash,
            is_active=True,
        )
        return self.users.save(user)


@dataclass(slots=True)
class CreateUserWithInvitation:
    users: UserRepositoryPort
    invitations: InvitationRepositoryPort
    ttl_hours: int = DEFAULT_INVITATION_TTL_HOURS

    def execute(
        self, actor: User, full_name: str, email: str, role: str
    ) -> tuple[User, Invitation]:
        if actor.role != UserRole.ADMIN:
            raise AuthorizationError("Only admin can create accounts")

        full_name, email, role_enum = _validate_profile(full_name, email, role)
        if self.users.find_by_email(email):
            raise ValidationError("Email already exists")

        user = self.users.save(
            User(
                id=None,
                full_name=full_name,
                email=email,
                role=role_enum,
                password_hash=None,
                is_active=True,
            )
        )
        invitation = self.invitations.create(
            Invitation(
                id=None,
                user_id=user.id or 0,
                token=secrets.token_urlsafe(32),
                expires_at=_now() + timedelta(hours=self.ttl_hours),
            )
        )
        return user, invitation


@dataclass(slots=True)
class CreateInvitation:
    users: UserRepositoryPort
    invitations: InvitationRepositoryPort
    ttl_hours: int = DEFAULT_INVITATION_TTL_HOURS

    def execute(self, actor: User, user_id: int) -> Invitation:
        if actor.role != UserRole.ADMIN:
            raise AuthorizationError("Only admin can create invitations")
        user = self.users.find_by_id(user_id)
        if user is None:
            raise ValidationError("User not found")
        if user.password_hash is not None:
            raise ValidationError("This account already has a password")
        return self.invitations.create(
            Invitation(
                id=None,
                user_id=user_id,
                token=secrets.token_urlsafe(32),
                expires_at=_now() + timedelta(hours=self.ttl_hours),
            )
        )


@dataclass(slots=True)
class ValidateInvitation:
    users: UserRepositoryPort
    invitations: InvitationRepositoryPort

    def execute(self, token: str) -> User:
        invitation = self.invitations.find_by_token(token)
        if invitation is None:
            raise AuthenticationError("Invalid or expired invitation link")
        if invitation.used_at is not None:
            raise AuthenticationError("This invitation has already been used")
        if _ensure_aware(invitation.expires_at) <= _now():
            raise AuthenticationError("This invitation has expired")
        user = self.users.find_by_id(invitation.user_id)
        if user is None:
            raise AuthenticationError("Invalid or expired invitation link")
        return user


@dataclass(slots=True)
class AcceptInvitation:
    users: UserRepositoryPort
    invitations: InvitationRepositoryPort
    hasher: PasswordHasherPort

    def execute(self, token: str, plain_password: str) -> User:
        invitation = self.invitations.find_by_token(token)
        if invitation is None:
            raise AuthenticationError("Invalid or expired invitation link")
        if invitation.used_at is not None:
            raise AuthenticationError("This invitation has already been used")
        if _ensure_aware(invitation.expires_at) <= _now():
            raise AuthenticationError("This invitation has expired")

        plain_password = _validate_password(plain_password)

        user = self.users.find_by_id(invitation.user_id)
        if user is None:
            raise AuthenticationError("Invalid or expired invitation link")
        if not user.is_active:
            raise ValidationError("Account disabled")
        if user.password_hash is not None:
            raise ValidationError("This account already has a password")

        user.password_hash = self.hasher.hash_password(plain_password)
        updated = self.users.save(user)
        self.invitations.mark_used(invitation.id)
        return updated


@dataclass(slots=True)
class LoginUser:
    users: UserRepositoryPort
    hasher: PasswordHasherPort

    def execute(self, email: str, plain_password: str) -> User:
        user = self.users.find_by_email(email.strip().lower())
        if user is None:
            raise AuthenticationError("Invalid credentials")
        if user.password_hash is None:
            raise AuthenticationError("Account has no password; use the invitation link")
        if not self.hasher.verify_password(plain_password, user.password_hash):
            raise AuthenticationError("Invalid credentials")
        if not user.is_active:
            raise AuthenticationError("Account disabled")
        return user
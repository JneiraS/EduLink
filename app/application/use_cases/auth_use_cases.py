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
        raise ValidationError("Tous les champs sont requis")

    full_name = full_name.strip()
    email = email.strip()
    if len(full_name) > MAX_FULL_NAME_LENGTH:
        raise ValidationError(
            f"Le nom complet ne doit pas dépasser {MAX_FULL_NAME_LENGTH} caractères"
        )
    if len(email) > MAX_EMAIL_LENGTH:
        raise ValidationError("Adresse email trop longue")
    if not _EMAIL_RE.match(email):
        raise ValidationError("Adresse email invalide")

    try:
        role_enum = UserRole(role)
    except ValueError as exc:
        raise ValidationError("Rôle invalide") from exc

    return full_name, email.lower(), role_enum


def _validate_password(plain_password: str) -> str:
    plain_password = plain_password.strip()
    if not plain_password:
        raise ValidationError("Tous les champs sont requis")
    if not (MIN_PASSWORD_LENGTH <= len(plain_password) <= MAX_PASSWORD_LENGTH):
        raise ValidationError(
            f"Le mot de passe doit contenir entre {MIN_PASSWORD_LENGTH} and "
            f"{MAX_PASSWORD_LENGTH} caractères"
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
            raise AuthorizationError("Seul l'administrateur peut créer des comptes")

        full_name, email, role_enum = _validate_profile(full_name, email, role)
        plain_password = _validate_password(plain_password)
        if self.users.find_by_email(email):
            raise ValidationError("Cette adresse email existe déjà")

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
            raise AuthorizationError("Seul l'administrateur peut créer des comptes")

        full_name, email, role_enum = _validate_profile(full_name, email, role)
        if self.users.find_by_email(email):
            raise ValidationError("Cette adresse email existe déjà")

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
            raise AuthorizationError("Seul l'administrateur peut créer des invitations")
        user = self.users.find_by_id(user_id)
        if user is None:
            raise ValidationError("Utilisateur introuvable")
        if user.password_hash is not None:
            raise ValidationError("Ce compte possède déjà un mot de passe")
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
            raise AuthenticationError("Lien d'invitation invalide ou expiré")
        if invitation.used_at is not None:
            raise AuthenticationError("Cette invitation a déjà été utilisée")
        if _ensure_aware(invitation.expires_at) <= _now():
            raise AuthenticationError("Cette invitation a expiré")
        user = self.users.find_by_id(invitation.user_id)
        if user is None:
            raise AuthenticationError("Lien d'invitation invalide ou expiré")
        return user


@dataclass(slots=True)
class AcceptInvitation:
    users: UserRepositoryPort
    invitations: InvitationRepositoryPort
    hasher: PasswordHasherPort

    def execute(self, token: str, plain_password: str) -> User:
        invitation = self.invitations.find_by_token(token)
        if invitation is None:
            raise AuthenticationError("Lien d'invitation invalide ou expiré")
        if invitation.used_at is not None:
            raise AuthenticationError("Cette invitation a déjà été utilisée")
        if _ensure_aware(invitation.expires_at) <= _now():
            raise AuthenticationError("Cette invitation a expiré")

        plain_password = _validate_password(plain_password)

        user = self.users.find_by_id(invitation.user_id)
        if user is None:
            raise AuthenticationError("Lien d'invitation invalide ou expiré")
        if not user.is_active:
            raise ValidationError("Compte désactivé")
        if user.password_hash is not None:
            raise ValidationError("Ce compte possède déjà un mot de passe")

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
            raise AuthenticationError("Invalid credentials")
        if not self.hasher.verify_password(plain_password, user.password_hash):
            raise AuthenticationError("Invalid credentials")
        if not user.is_active:
            raise AuthenticationError("Invalid credentials")
        return user
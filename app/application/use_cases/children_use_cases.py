from dataclasses import dataclass

from app.domain.entities.channel import Channel
from app.domain.entities.child import Child, ParentSearchResult
from app.domain.entities.user import User, UserRole, UserSummary
from app.domain.errors import AuthorizationError, NotFoundError, ValidationError
from app.domain.ports.repositories import (
    ChannelRepositoryPort,
    ChildrenRepositoryPort,
    UserRepositoryPort,
)

MAX_CHILD_NAME_LENGTH = 120
MAX_CLASS_NAME_LENGTH = 120


def _validate_child_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValidationError("Le nom de l'enfant est requis")
    if len(name) > MAX_CHILD_NAME_LENGTH:
        raise ValidationError(
            f"Le nom de l'enfant ne doit pas dépasser {MAX_CHILD_NAME_LENGTH} caractères"
        )
    return name


def _validate_class_name(class_name: str) -> str:
    class_name = class_name.strip()
    if not class_name:
        raise ValidationError("La classe est requise")
    if len(class_name) > MAX_CLASS_NAME_LENGTH:
        raise ValidationError(
            f"Le nom de la classe ne doit pas dépasser {MAX_CLASS_NAME_LENGTH} caractères"
        )
    return class_name


def _require_admin(actor: User) -> None:
    if actor.role != UserRole.ADMIN:
        raise AuthorizationError("Accès réservé à l'administration")


def _link_child_to_class_channels(
    channels: ChannelRepositoryPort,
    child: Child,
    created_by: int,
) -> None:
    channel = channels.find_by_name(child.class_name, kind="group")
    if channel is None:
        channel = channels.create(
            Channel(
                id=None,
                name=child.class_name,
                kind="group",
                created_by=created_by,
            )
        )

    if child.parent_id not in channels.list_member_ids(channel.id):
        channels.add_member(channel.id, child.parent_id)


@dataclass(slots=True)
class CreateChild:
    children: ChildrenRepositoryPort
    users: UserRepositoryPort
    channels: ChannelRepositoryPort

    def execute(self, actor: User, full_name: str, class_name: str, parent_id: int | None = None) -> Child:
        _require_admin(actor)
        full_name = _validate_child_name(full_name)
        class_name = _validate_class_name(class_name)

        if parent_id is None:
            raise ValidationError("Un parent doit être sélectionné")

        parent = self.users.find_by_id(parent_id)
        if parent is None or parent.role.value != "PARENT":
            raise ValidationError("Parent invalide")

        child = Child(
            id=None,
            parent_id=parent_id,
            full_name=full_name,
            class_name=class_name,
        )
        child = self.children.save(child)
        _link_child_to_class_channels(self.channels, child, actor.id)
        return child


@dataclass(slots=True)
class ListChildren:
    children: ChildrenRepositoryPort

    def execute(self, actor: User) -> list[Child]:
        return self.children.list_by_parent(actor.id)


@dataclass(slots=True)
class ListClassNames:
    children: ChildrenRepositoryPort

    def execute(self) -> list[str]:
        return self.children.list_class_names()


@dataclass(slots=True)
class DeleteChild:
    children: ChildrenRepositoryPort

    def execute(self, actor: User, child_id: int) -> None:
        _require_admin(actor)
        child = self.children.find_by_id(child_id)
        if child is None:
            raise NotFoundError("Enfant introuvable")
        self.children.delete(child_id)


@dataclass(slots=True)
class LinkChildToClassChannels:
    children: ChildrenRepositoryPort
    channels: ChannelRepositoryPort

    def execute(self, actor: User, child_id: int) -> None:
        _require_admin(actor)
        child = self.children.find_by_id(child_id)
        if child is None:
            raise NotFoundError("Enfant introuvable")
        _link_child_to_class_channels(self.channels, child, actor.id)


@dataclass(slots=True)
class FindParentsByChild:
    children: ChildrenRepositoryPort
    users: UserRepositoryPort

    def execute(self, actor: User, query: str) -> list[ParentSearchResult]:
        if actor.role not in (UserRole.ADMIN, UserRole.TEACHER):
            raise AuthorizationError("Accès réservé aux enseignants")
        query = query.strip()
        if not query:
            raise ValidationError("Le terme de recherche est requis")

        matched_children = self.children.find_by_name_like(query)
        parent_ids = list({c.parent_id for c in matched_children})
        parents = {p.id: p for p in self.users.find_many_by_ids(parent_ids)}

        results = []
        for child in matched_children:
            parent = parents.get(child.parent_id)
            if parent:
                results.append(
                    ParentSearchResult(
                        child=child,
                        parent=UserSummary(
                            id=parent.id,
                            full_name=parent.full_name,
                            role=parent.role,
                        ),
                    )
                )
        return results
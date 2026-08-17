import pytest

from app.application.use_cases.children_use_cases import (
    CreateChild,
    DeleteChild,
    ListChildren,
    LinkChildToClassChannels,
)
from app.domain.entities.child import Child
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, NotFoundError, ValidationError


class InMemoryChildren:
    def __init__(self):
        self.children = []

    def save(self, child: Child) -> Child:
        child.id = len(self.children) + 1
        self.children.append(child)
        return child

    def list_by_parent(self, parent_id: int) -> list[Child]:
        return [c for c in self.children if c.parent_id == parent_id]

    def find_by_class(self, class_name: str) -> list[Child]:
        return [c for c in self.children if c.class_name == class_name]

    def find_by_id(self, child_id: int) -> Child | None:
        return next((c for c in self.children if c.id == child_id), None)

    def delete(self, child_id: int) -> Child | None:
        for i, child in enumerate(self.children):
            if child.id == child_id:
                return self.children.pop(i)
        return None


class InMemoryUsers:
    def __init__(self):
        self.users = []

    def find_by_id(self, user_id: int):
        return next((u for u in self.users if u.id == user_id), None)

    def save(self, user):
        if user.id is None:
            user.id = len(self.users) + 1
            self.users.append(user)
        return user


class InMemoryChannels:
    def __init__(self):
        self.channels = []
        self.members = {}

    def find_by_name(self, name: str, kind: str | None = None):
        for c in self.channels:
            if c.name == name and (kind is None or c.kind == kind):
                return c
        return None

    def create(self, channel):
        channel.id = len(self.channels) + 1
        self.channels.append(channel)
        return channel

    def add_member(self, channel_id: int, user_id: int) -> None:
        self.members.setdefault(channel_id, []).append(user_id)

    def list_member_ids(self, channel_id: int) -> list[int]:
        return self.members.get(channel_id, [])


def _parent_actor(role=UserRole.PARENT, uid=1):
    return User(
        id=uid,
        full_name="Parent",
        email=f"parent{uid}@test.local",
        role=role,
        password_hash="x",
        is_active=True,
    )


def _child(user_id=1, name="Élève", class_name="CM1"):
    return Child(id=None, parent_id=user_id, full_name=name, class_name=class_name)


# ---------------------------------------------------------------------------
# CreateChild
# ---------------------------------------------------------------------------

def test_create_child_requires_admin():
    children_repo = InMemoryChildren()
    users_repo = InMemoryUsers()
    admin = _parent_actor(UserRole.ADMIN, uid=1)
    users_repo.users.append(admin)
    use_case = CreateChild(children=children_repo, users=users_repo)
    with pytest.raises(AuthorizationError):
        use_case.execute(_parent_actor(UserRole.PARENT, uid=2), "Élève", "CM1")


def test_create_child_valid():
    children_repo = InMemoryChildren()
    users_repo = InMemoryUsers()
    admin = _parent_actor(UserRole.ADMIN, uid=1)
    parent = _parent_actor(UserRole.PARENT, uid=2)
    users_repo.users.append(admin)
    users_repo.users.append(parent)
    use_case = CreateChild(children=children_repo, users=users_repo)
    child = use_case.execute(admin, "Élève", "CM1", parent_id=parent.id)
    assert child.full_name == "Élève"
    assert child.class_name == "CM1"
    assert child.parent_id == parent.id
    assert child.id == 1


def test_create_child_requires_name():
    children_repo = InMemoryChildren()
    users_repo = InMemoryUsers()
    admin = _parent_actor(UserRole.ADMIN, uid=1)
    parent = _parent_actor(UserRole.PARENT, uid=2)
    users_repo.users.append(admin)
    users_repo.users.append(parent)
    use_case = CreateChild(children=children_repo, users=users_repo)
    with pytest.raises(ValidationError):
        use_case.execute(admin, "  ", "CM1", parent_id=parent.id)


def test_create_child_rejects_oversized_name():
    children_repo = InMemoryChildren()
    users_repo = InMemoryUsers()
    admin = _parent_actor(UserRole.ADMIN, uid=1)
    parent = _parent_actor(UserRole.PARENT, uid=2)
    users_repo.users.append(admin)
    users_repo.users.append(parent)
    use_case = CreateChild(children=children_repo, users=users_repo)
    with pytest.raises(ValidationError):
        use_case.execute(admin, "X" * 121, "CM1", parent_id=parent.id)


def test_create_child_requires_class():
    children_repo = InMemoryChildren()
    users_repo = InMemoryUsers()
    admin = _parent_actor(UserRole.ADMIN, uid=1)
    parent = _parent_actor(UserRole.PARENT, uid=2)
    users_repo.users.append(admin)
    users_repo.users.append(parent)
    use_case = CreateChild(children=children_repo, users=users_repo)
    with pytest.raises(ValidationError):
        use_case.execute(admin, "Élève", "", parent_id=parent.id)


def test_create_child_rejects_oversized_class():
    children_repo = InMemoryChildren()
    users_repo = InMemoryUsers()
    admin = _parent_actor(UserRole.ADMIN)
    parent = _parent_actor(UserRole.PARENT)
    users_repo.users.append(admin)
    users_repo.users.append(parent)
    use_case = CreateChild(children=children_repo, users=users_repo)
    with pytest.raises(ValidationError):
        use_case.execute(admin, "Élève", "X" * 121, parent_id=parent.id)


def test_create_child_invalid_parent():
    children_repo = InMemoryChildren()
    users_repo = InMemoryUsers()
    admin = _parent_actor(UserRole.ADMIN)
    parent = _parent_actor(UserRole.PARENT)
    users_repo.users.append(admin)
    users_repo.users.append(parent)
    use_case = CreateChild(children=children_repo, users=users_repo)
    with pytest.raises(ValidationError):
        use_case.execute(admin, "Élève", "CM1", parent_id=999)


def test_create_child_requires_parent_id():
    children_repo = InMemoryChildren()
    users_repo = InMemoryUsers()
    admin = _parent_actor(UserRole.ADMIN, uid=1)
    users_repo.users.append(admin)
    use_case = CreateChild(children=children_repo, users=users_repo)
    with pytest.raises(ValidationError):
        use_case.execute(admin, "Élève", "CM1", parent_id=None)


# ---------------------------------------------------------------------------
# ListChildren
# ---------------------------------------------------------------------------

def test_list_children_returns_parent_children():
    repo = InMemoryChildren()
    repo.save(_child(1, "Élève A", "CM1"))
    repo.save(_child(1, "Élève B", "CM2"))
    repo.save(_child(2, "Élève C", "CM1"))
    use_case = ListChildren(children=repo)
    children = use_case.execute(_parent_actor(UserRole.PARENT))
    assert len(children) == 2
    assert [c.full_name for c in children] == ["Élève A", "Élève B"]


def test_list_children_empty():
    use_case = ListChildren(children=InMemoryChildren())
    children = use_case.execute(_parent_actor(UserRole.PARENT))
    assert children == []


# ---------------------------------------------------------------------------
# DeleteChild
# ---------------------------------------------------------------------------

def test_delete_child_requires_admin():
    repo = InMemoryChildren()
    child = repo.save(_child(1, "Élève", "CM1"))
    use_case = DeleteChild(children=repo)
    with pytest.raises(AuthorizationError):
        use_case.execute(_parent_actor(UserRole.PARENT), child.id)


def test_delete_child_owner_only():
    repo = InMemoryChildren()
    child = repo.save(_child(1, "Élève", "CM1"))
    use_case = DeleteChild(children=repo)
    use_case.execute(_parent_actor(UserRole.ADMIN), child.id)
    assert repo.find_by_id(child.id) is None


def test_delete_child_non_existent_raises_not_found():
    repo = InMemoryChildren()
    use_case = DeleteChild(children=repo)
    with pytest.raises(NotFoundError):
        use_case.execute(_parent_actor(UserRole.ADMIN), 999)


def test_delete_child_twice_second_raises_not_found():
    repo = InMemoryChildren()
    child = repo.save(_child(1, "Élève", "CM1"))
    use_case = DeleteChild(children=repo)
    use_case.execute(_parent_actor(UserRole.ADMIN), child.id)
    with pytest.raises(NotFoundError):
        use_case.execute(_parent_actor(UserRole.ADMIN), child.id)


# ---------------------------------------------------------------------------
# LinkChildToClassChannels
# ---------------------------------------------------------------------------

def test_link_child_to_class_channels_requires_admin():
    children_repo = InMemoryChildren()
    channels_repo = InMemoryChannels()
    use_case = LinkChildToClassChannels(children=children_repo, channels=channels_repo)
    with pytest.raises(AuthorizationError):
        use_case.execute(_parent_actor(UserRole.PARENT), 1)


def test_link_child_to_class_channels_creates_channel_if_missing():
    children_repo = InMemoryChildren()
    child = children_repo.save(_child(1, "Élève", "CM2"))
    channels_repo = InMemoryChannels()
    use_case = LinkChildToClassChannels(children=children_repo, channels=channels_repo)
    use_case.execute(_parent_actor(UserRole.ADMIN), child.id)
    channel = channels_repo.find_by_name("CM2")
    assert channel is not None
    assert channels_repo.list_member_ids(channel.id) == [1]


def test_link_child_to_class_channels_uses_existing_channel():
    children_repo = InMemoryChildren()
    child = children_repo.save(_child(1, "Élève", "CM2"))
    channels_repo = InMemoryChannels()
    existing = type("Channel", (), {"id": 1, "name": "CM2", "created_by": 1, "kind": "group"})()
    channels_repo.channels.append(existing)
    use_case = LinkChildToClassChannels(children=children_repo, channels=channels_repo)
    use_case.execute(_parent_actor(UserRole.ADMIN), child.id)
    assert len(channels_repo.channels) == 1
    assert channels_repo.list_member_ids(1) == [1]


def test_link_child_to_class_channels_does_not_reuse_direct_channel():
    children_repo = InMemoryChildren()
    child = children_repo.save(_child(1, "Élève", "CM2"))
    channels_repo = InMemoryChannels()
    direct = type("Channel", (), {"id": 5, "name": "CM2", "created_by": 1, "kind": "direct"})()
    channels_repo.channels.append(direct)
    use_case = LinkChildToClassChannels(children=children_repo, channels=channels_repo)
    use_case.execute(_parent_actor(UserRole.ADMIN), child.id)
    group = channels_repo.find_by_name("CM2", kind="group")
    assert group is not None
    assert group.id != 5
    assert channels_repo.list_member_ids(group.id) == [1]
    assert 1 not in channels_repo.list_member_ids(5)


def test_link_child_to_class_channels_child_not_found():
    children_repo = InMemoryChildren()
    channels_repo = InMemoryChannels()
    use_case = LinkChildToClassChannels(children=children_repo, channels=channels_repo)
    with pytest.raises(NotFoundError):
        use_case.execute(_parent_actor(UserRole.ADMIN), 999)
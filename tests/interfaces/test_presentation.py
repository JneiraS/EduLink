from app.domain.entities.user import User, UserRole
from app.interfaces.web.routes.presentation import group_users_by_role


def _user(uid, name, role):
    return User(
        id=uid,
        full_name=name,
        email=f"u{uid}@test.local",
        role=role,
        password_hash="x",
        is_active=True,
    )


def test_group_users_by_role_orders_groups_admin_teacher_parent():
    teacher = _user(1, "Alice", UserRole.TEACHER)
    admin = _user(2, "Bob", UserRole.ADMIN)
    parent = _user(3, "Charlie", UserRole.PARENT)
    groups = group_users_by_role([teacher, admin, parent])
    assert [role for role, _label, _users in groups] == [
        UserRole.ADMIN,
        UserRole.TEACHER,
        UserRole.PARENT,
    ]


def test_group_users_by_role_buckets_members_by_role():
    teacher = _user(1, "Alice", UserRole.TEACHER)
    admin = _user(2, "Bob", UserRole.ADMIN)
    parent = _user(3, "Charlie", UserRole.PARENT)
    groups = {
        role: users for role, _label, users in group_users_by_role([teacher, admin, parent])
    }
    assert [u.id for u in groups[UserRole.ADMIN]] == [2]
    assert [u.id for u in groups[UserRole.TEACHER]] == [1]
    assert [u.id for u in groups[UserRole.PARENT]] == [3]


def test_group_users_by_role_preserves_input_order_within_group():
    parent_a = _user(1, "Alice Parent", UserRole.PARENT)
    parent_b = _user(2, "Bob Parent", UserRole.PARENT)
    groups = {
        role: users for role, _label, users in group_users_by_role([parent_b, parent_a])
    }
    assert [u.id for u in groups[UserRole.PARENT]] == [2, 1]


def test_group_users_by_role_returns_french_labels():
    groups = group_users_by_role([])
    labels = {role: label for role, label, _users in groups}
    assert labels == {
        UserRole.ADMIN: "Administrateurs",
        UserRole.TEACHER: "Enseignants",
        UserRole.PARENT: "Parents",
    }
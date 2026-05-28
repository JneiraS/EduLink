from app.domain.entities.user import UserRole


def test_user_role_values():
    assert UserRole.ADMIN.value == "ADMIN"
    assert UserRole.TEACHER.value == "TEACHER"
    assert UserRole.PARENT.value == "PARENT"

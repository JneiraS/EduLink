from tests.helpers import create_user, login


def test_login_success_redirects_to_dashboard(client, app):
    user_id = create_user(app, role="ADMIN", email="admin@t.local")
    response = client.post(
        "/auth/login", data={"email": "admin@t.local", "password": "secret"}
    )
    assert response.status_code == 302
    assert "/" in response.headers["Location"]

    with client.session_transaction() as sess:
        assert sess["_user_id"] == str(user_id)
        assert sess.permanent is True


def test_login_invalid_credentials_rerenders(client, app):
    create_user(app, role="ADMIN", email="admin@t.local")
    response = client.post(
        "/auth/login", data={"email": "admin@t.local", "password": "wrong"}
    )
    assert response.status_code == 200
    assert b"Invalid credentials" in response.data


def test_login_already_authenticated_redirects(client, app):
    user_id = create_user(app, role="ADMIN", email="a@t.local")
    login(client, user_id)
    response = client.get("/auth/login")
    assert response.status_code == 302


def test_create_user_requires_admin(client, app):
    parent_id = create_user(app, role="PARENT", email="p@t.local")
    login(client, parent_id)
    response = client.get("/auth/users/new", follow_redirects=True)
    assert b"Acces reserve" in response.data


def test_create_user_admin_success(client, app):
    admin_id = create_user(app, role="ADMIN", email="a@t.local")
    login(client, admin_id)
    response = client.post(
        "/auth/users/new",
        data={
            "full_name": "New Teacher",
            "email": "teacher@t.local",
            "role": "TEACHER",
        },
    )
    assert response.status_code == 200
    assert b"Compte cree" in response.data
    assert b"Invitation creee" in response.data
    assert b"/auth/invite/" in response.data


def test_create_user_validation_error(client, app):
    admin_id = create_user(app, role="ADMIN", email="a2@t.local")
    login(client, admin_id)
    response = client.post(
        "/auth/users/new",
        data={"full_name": "", "email": "", "role": "TEACHER"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"All fields are required" in response.data
from datetime import datetime, timedelta, timezone

from tests.helpers import create_user, login

NOW = datetime.now(timezone.utc)


def _make_invited_user(app, email="invited@t.local", expires_at=None, used_at=None):
    from app.extensions import db
    from app.infrastructure.database.models import InvitationModel, UserModel

    with app.app_context():
        user = UserModel(
            full_name="Invited User",
            email=email,
            role="PARENT",
            password_hash=None,
            is_active=True,
        )
        db.session.add(user)
        db.session.flush()
        invitation = InvitationModel(
            user_id=user.id,
            token=f"tok-{email}",
            expires_at=expires_at or (NOW + timedelta(hours=72)),
            used_at=used_at,
        )
        db.session.add(invitation)
        db.session.commit()
        return user.id, invitation.token


def test_create_user_shows_invitation_link(client, app):
    admin_id = create_user(app, role="ADMIN", email="inv-admin@t.local")
    login(client, admin_id)
    response = client.post(
        "/auth/users/new",
        data={"full_name": "New Teacher", "email": "inv-teacher@t.local", "role": "TEACHER"},
    )
    assert response.status_code == 200
    assert b"Invitation creee" in response.data
    assert b"/auth/invite/" in response.data


def test_create_user_does_not_set_password(client, app):
    admin_id = create_user(app, role="ADMIN", email="inv-admin2@t.local")
    login(client, admin_id)
    client.post(
        "/auth/users/new",
        data={"full_name": "New Teacher", "email": "inv-teacher2@t.local", "role": "TEACHER"},
    )
    with app.app_context():
        from app.extensions import db
        from app.infrastructure.database.models import UserModel

        user = UserModel.query.filter_by(email="inv-teacher2@t.local").first()
        assert user.password_hash is None


def test_invite_get_renders_form(client, app):
    user_id, token = _make_invited_user(app)
    response = client.get(f"/auth/invite/{token}")
    assert response.status_code == 200
    assert b"D\xc3\xa9finissez votre mot de passe" in response.data
    assert b"Invited User" in response.data


def test_invite_invalid_token_redirects(client, app):
    response = client.get("/auth/invite/unknown-token", follow_redirects=True)
    assert b"Invalid or expired invitation link" in response.data


def test_invite_expired_rejected(client, app):
    _, token = _make_invited_user(app, email="expired@t.local", expires_at=NOW - timedelta(hours=1))
    response = client.get(f"/auth/invite/{token}", follow_redirects=True)
    assert b"has expired" in response.data


def test_invite_used_rejected(client, app):
    _, token = _make_invited_user(app, email="used@t.local", used_at=NOW)
    response = client.get(f"/auth/invite/{token}", follow_redirects=True)
    assert b"already been used" in response.data


def test_invite_post_sets_password_and_logs_in(client, app):
    user_id, token = _make_invited_user(app, email="accept@t.local")
    response = client.post(
        f"/auth/invite/{token}",
        data={"password": "newpass123", "confirm": "newpass123"},
    )
    assert response.status_code == 302
    assert "/" in response.headers["Location"]
    with client.session_transaction() as sess:
        assert sess["_user_id"] == str(user_id)


def test_invite_token_is_one_time(client, app):
    _, token = _make_invited_user(app, email="onetime@t.local")
    client.post(f"/auth/invite/{token}", data={"password": "newpass123", "confirm": "newpass123"})
    with client.session_transaction() as sess:
        sess.clear()
    from flask_login import logout_user

    logout_user()
    response = client.get(f"/auth/invite/{token}", follow_redirects=True)
    assert b"already been used" in response.data


def test_invite_post_password_mismatch(client, app):
    _, token = _make_invited_user(app, email="mismatch@t.local")
    response = client.post(
        f"/auth/invite/{token}",
        data={"password": "newpass123", "confirm": "different"},
    )
    assert response.status_code == 200
    assert b"Passwords do not match" in response.data


def test_invite_post_short_password(client, app):
    _, token = _make_invited_user(app, email="short@t.local")
    response = client.post(
        f"/auth/invite/{token}",
        data={"password": "short", "confirm": "short"},
    )
    assert response.status_code == 200
    assert b"Password must be between" in response.data


def test_login_without_password_rejected(client, app):
    _make_invited_user(app, email="nopass@t.local")
    response = client.post(
        "/auth/login", data={"email": "nopass@t.local", "password": "whatever"}
    )
    assert response.status_code == 200
    assert b"Invalid credentials" in response.data


def test_login_works_after_acceptance(client, app):
    user_id, token = _make_invited_user(app, email="final@t.local")
    client.post(f"/auth/invite/{token}", data={"password": "newpass123", "confirm": "newpass123"})
    with client.session_transaction() as sess:
        sess.clear()
    from flask_login import logout_user

    logout_user()
    response = client.post(
        "/auth/login", data={"email": "final@t.local", "password": "newpass123"}
    )
    assert response.status_code == 302
    assert "/" in response.headers["Location"]
    with client.session_transaction() as sess:
        assert sess["_user_id"] == str(user_id)


def test_admin_regenerates_invitation(client, app):
    admin_id = create_user(app, role="ADMIN", email="inv-admin3@t.local")
    user_id, token = _make_invited_user(app, email="regen@t.local")
    login(client, admin_id)
    response = client.post(f"/admin/members/{user_id}/invite", follow_redirects=True)
    assert response.status_code == 200
    assert b"Lien invitation" in response.data
    with app.app_context():
        from app.extensions import db
        from app.infrastructure.database.models import InvitationModel

        tokens = [i.token for i in InvitationModel.query.filter_by(user_id=user_id).all()]
        assert len(tokens) == 2
        assert token in tokens


def test_admin_regenerate_rejects_user_with_password(client, app):
    admin_id = create_user(app, role="ADMIN", email="inv-admin4@t.local")
    user_id = create_user(app, role="PARENT", email="haspass@t.local", password="secret123")
    login(client, admin_id)
    response = client.post(f"/admin/members/{user_id}/invite", follow_redirects=True)
    assert b"already has a password" in response.data


def test_admin_regenerate_requires_admin(client, app):
    parent_id = create_user(app, role="PARENT", email="inv-parent@t.local")
    _, user_id = None, parent_id
    user_id2, _ = _make_invited_user(app, email="inv-target@t.local")
    login(client, parent_id)
    response = client.post(f"/admin/members/{user_id2}/invite", follow_redirects=True)
    assert b"Acces reserve" in response.data


def test_invite_post_rate_limited(client, app):
    from app.extensions import limiter

    app.config["RATE_LIMIT_ENABLED"] = True
    limiter.enabled = True
    limiter.reset()
    _, token = _make_invited_user(app, email="rl-invite@t.local")
    for _ in range(10):
        client.post(
            f"/auth/invite/{token}",
            data={"password": "newpass123", "confirm": "newpass123"},
        )
    response = client.post(
        f"/auth/invite/{token}",
        data={"password": "newpass123", "confirm": "newpass123"},
    )
    assert response.status_code == 429
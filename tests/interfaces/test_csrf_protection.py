import re

from tests.helpers import create_user, login

PUSH_ENDPOINT = "https://fcm.googleapis.com/fcm/send/e1"
P256DH = "BP0GtYpE8H4UjLm5kR8H8xk1Wq1F5Bt3jPyXN1g1a6EeK0mQ4nQrR7S0yYg2cVdWjv7I2X9zWfQbKpO9uU8V"
AUTH = "kL5mN3pR8sT2vW6xY9zB0dF4gH1jJ7aQ"


def _enable_csrf(app):
    app.config["WTF_CSRF_ENABLED"] = True
    return app


def _csrf_token(client):
    page = client.get("/").data
    token = re.search(rb'name="csrf_token" value="([^"]+)"', page)
    if token is None:
        token = re.search(rb'name="csrf_token" value="([^"]+)"', client.get("/auth/login").data)
    return token.group(1).decode()


def test_login_post_without_csrf_token_rejected(app, client):
    _enable_csrf(app)
    create_user(app, role="ADMIN", email="a@t.local")
    response = client.post(
        "/auth/login", data={"email": "a@t.local", "password": "secret"}
    )
    assert response.status_code == 400


def test_login_post_with_csrf_token_succeeds(app, client):
    _enable_csrf(app)
    create_user(app, role="ADMIN", email="a@t.local")
    token = _csrf_token(client)
    response = client.post(
        "/auth/login",
        data={"email": "a@t.local", "password": "secret", "csrf_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Plateforme de communication scolaire centralisee" in response.data


def test_push_subscribe_without_csrf_header_rejected(app, client):
    _enable_csrf(app)
    user_id = create_user(app, role="PARENT", email="p@t.local")
    login(client, user_id)
    response = client.post(
        "/push/subscribe",
        json={"endpoint": PUSH_ENDPOINT, "keys": {"p256dh": P256DH, "auth": AUTH}},
    )
    assert response.status_code == 400


def test_push_subscribe_with_csrf_header_succeeds(app, client):
    _enable_csrf(app)
    user_id = create_user(app, role="PARENT", email="p2@t.local")
    login(client, user_id)
    token = _csrf_token(client)
    response = client.post(
        "/push/subscribe",
        json={"endpoint": PUSH_ENDPOINT, "keys": {"p256dh": P256DH, "auth": AUTH}},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200
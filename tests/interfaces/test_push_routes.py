from tests.helpers import create_user, login

ENDPOINT = "https://fcm.googleapis.com/fcm/send/e1"
P256DH = "BP0GtYpE8H4UjLm5kR8H8xk1Wq1F5Bt3jPyXN1g1a6EeK0mQ4nQrR7S0yYg2cVdWjv7I2X9zWfQbKpO9uU8V"
AUTH = "kL5mN3pR8sT2vW6xY9zB0dF4gH1jJ7aQ"


def test_public_key_requires_login(client):
    response = client.get("/push/public-key")
    assert response.status_code == 302


def test_public_key_returns_empty_when_unset(client, app):
    user_id = create_user(app, role="PARENT", email="p@t.local")
    login(client, user_id)
    response = client.get("/push/public-key")
    assert response.status_code == 200
    assert response.json["publicKey"] == ""


def test_subscribe_success(client, app):
    user_id = create_user(app, role="PARENT", email="p2@t.local")
    login(client, user_id)
    response = client.post(
        "/push/subscribe",
        json={"endpoint": ENDPOINT, "keys": {"p256dh": P256DH, "auth": AUTH}},
    )
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_subscribe_invalid_payload(client, app):
    user_id = create_user(app, role="PARENT", email="p3@t.local")
    login(client, user_id)
    response = client.post("/push/subscribe", json={"endpoint": "only"})
    assert response.status_code == 400


def test_subscribe_rejects_non_https(client, app):
    user_id = create_user(app, role="PARENT", email="p6@t.local")
    login(client, user_id)
    response = client.post(
        "/push/subscribe",
        json={"endpoint": "http://fcm.googleapis.com/e", "keys": {"p256dh": P256DH, "auth": AUTH}},
    )
    assert response.status_code == 400


def test_subscribe_rejects_private_ip(client, app):
    user_id = create_user(app, role="PARENT", email="p7@t.local")
    login(client, user_id)
    response = client.post(
        "/push/subscribe",
        json={
            "endpoint": "https://192.168.1.10/fcm/send/e",
            "keys": {"p256dh": P256DH, "auth": AUTH},
        },
    )
    assert response.status_code == 400


def test_subscribe_rejects_unknown_host(client, app):
    user_id = create_user(app, role="PARENT", email="p8@t.local")
    login(client, user_id)
    response = client.post(
        "/push/subscribe",
        json={
            "endpoint": "https://evil.example.com/e",
            "keys": {"p256dh": P256DH, "auth": AUTH},
        },
    )
    assert response.status_code == 400


def test_subscribe_rejects_short_keys(client, app):
    user_id = create_user(app, role="PARENT", email="p9@t.local")
    login(client, user_id)
    response = client.post(
        "/push/subscribe",
        json={"endpoint": ENDPOINT, "keys": {"p256dh": "a", "auth": "b"}},
    )
    assert response.status_code == 400


def test_unsubscribe_success(client, app):
    user_id = create_user(app, role="PARENT", email="p4@t.local")
    login(client, user_id)
    client.post(
        "/push/subscribe",
        json={"endpoint": ENDPOINT, "keys": {"p256dh": P256DH, "auth": AUTH}},
    )
    response = client.post("/push/unsubscribe", json={"endpoint": ENDPOINT})
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_unsubscribe_missing_endpoint(client, app):
    user_id = create_user(app, role="PARENT", email="p5@t.local")
    login(client, user_id)
    response = client.post("/push/unsubscribe", json={})
    assert response.status_code == 400
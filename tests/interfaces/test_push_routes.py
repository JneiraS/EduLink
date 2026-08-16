from tests.helpers import create_user, login


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
        json={
            "endpoint": "https://push.example.com/e1",
            "keys": {"p256dh": "k1", "auth": "k2"},
        },
    )
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_subscribe_invalid_payload(client, app):
    user_id = create_user(app, role="PARENT", email="p3@t.local")
    login(client, user_id)
    response = client.post("/push/subscribe", json={"endpoint": "only"})
    assert response.status_code == 400


def test_unsubscribe_success(client, app):
    user_id = create_user(app, role="PARENT", email="p4@t.local")
    login(client, user_id)
    client.post(
        "/push/subscribe",
        json={"endpoint": "https://push.example.com/e2", "keys": {"p256dh": "a", "auth": "b"}},
    )
    response = client.post(
        "/push/unsubscribe", json={"endpoint": "https://push.example.com/e2"}
    )
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_unsubscribe_missing_endpoint(client, app):
    user_id = create_user(app, role="PARENT", email="p5@t.local")
    login(client, user_id)
    response = client.post("/push/unsubscribe", json={})
    assert response.status_code == 400
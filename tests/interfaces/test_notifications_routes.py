import json

from tests.helpers import add_notification, create_channel, create_user, login


def test_list_notifications_requires_login(client):
    response = client.get("/notifications/")
    assert response.status_code == 302


def test_list_notifications_json(client, app):
    user_id = create_user(app, role="PARENT", email="p@t.local")
    channel_id = create_channel(app, "Canal", user_id, [user_id])
    add_notification(app, user_id, "Nouveau message dans le canal Canal", channel_id)
    login(client, user_id)
    response = client.get("/notifications/")
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert len(payload) == 1
    assert payload[0]["channel_id"] == channel_id
    assert payload[0]["is_read"] is False


def test_mark_notification_read(client, app):
    user_id = create_user(app, role="PARENT", email="p2@t.local")
    notif_id = add_notification(app, user_id, "hello")
    login(client, user_id)
    response = client.post(
        f"/notifications/{notif_id}/read", follow_redirects=True
    )
    assert response.status_code == 200

    from app.extensions import db
    from app.infrastructure.database.models import NotificationModel

    with app.app_context():
        notif = db.session.get(NotificationModel, notif_id)
        assert notif.is_read is True
from tests.helpers import add_message, create_channel, create_user, login


def test_channels_page_requires_login(client):
    response = client.get("/messages/channels")
    assert response.status_code == 302


def test_parent_cannot_create_channel(client, app):
    parent_id = create_user(app, role="PARENT", email="p@t.local")
    login(client, parent_id)
    response = client.post(
        "/messages/channels", data={"name": "Canal", "members": []}
    )
    assert response.status_code == 200
    assert b"Only admin and teachers can create channels" in response.data


def test_teacher_can_create_channel(client, app):
    teacher_id = create_user(app, role="TEACHER", email="t@t.local")
    parent_id = create_user(app, role="PARENT", email="p2@t.local")
    login(client, teacher_id)
    response = client.post(
        "/messages/channels",
        data={"name": "Classe A", "members": [str(parent_id)]},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Canal cree" in response.data


def test_create_channel_requires_name(client, app):
    teacher_id = create_user(app, role="TEACHER", email="t2@t.local")
    login(client, teacher_id)
    response = client.post(
        "/messages/channels", data={"name": "  ", "members": []}
    )
    assert b"Channel name is required" in response.data


def test_member_can_send_message(client, app):
    admin_id = create_user(app, role="ADMIN", email="a@t.local")
    channel_id = create_channel(app, "Canal", admin_id, [admin_id])
    login(client, admin_id)
    response = client.post(
        f"/messages/channels/{channel_id}",
        data={"action": "send_message", "content": "Bonjour"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Bonjour" in response.data


def test_non_member_cannot_send_message(client, app):
    admin_id = create_user(app, role="ADMIN", email="a2@t.local")
    outsider_id = create_user(app, role="PARENT", email="o@t.local")
    channel_id = create_channel(app, "Prive", admin_id, [admin_id])
    login(client, outsider_id)
    response = client.post(
        f"/messages/channels/{channel_id}",
        data={"action": "send_message", "content": "spam"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"User is not member of this channel" in response.data


def test_channel_detail_pagination_load_older(client, app):
    admin_id = create_user(app, role="ADMIN", email="a3@t.local")
    channel_id = create_channel(app, "Canal", admin_id, [admin_id])
    for i in range(60):
        add_message(app, channel_id, admin_id, f"msg {i}")
    login(client, admin_id)
    response = client.get(f"/messages/channels/{channel_id}")
    assert response.status_code == 200
    assert b"plus anciens" in response.data

    import re

    match = re.search(rb"before=(\d+)", response.data)
    assert match is not None
    response_page2 = client.get(
        f"/messages/channels/{channel_id}?before={match.group(1).decode()}"
    )
    assert b"plus anciens" not in response_page2.data


def test_channel_detail_add_members_admin(client, app):
    admin_id = create_user(app, role="ADMIN", email="a4@t.local")
    parent_id = create_user(app, role="PARENT", email="p4@t.local")
    channel_id = create_channel(app, "Canal", admin_id, [admin_id])
    login(client, admin_id)
    response = client.post(
        f"/messages/channels/{channel_id}",
        data={"action": "add_members", "members": [str(parent_id)]},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Membres ajoutes" in response.data
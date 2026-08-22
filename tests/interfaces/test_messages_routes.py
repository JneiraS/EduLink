from app.infrastructure.database.models import ChannelModel, MessageModel, MessageTemplateModel
from tests.helpers import add_message, create_channel, create_user, login


def test_teacher_can_pin_message(client, app):
    teacher_id = create_user(app, role="TEACHER", email="pin1@t.local")
    channel_id = create_channel(app, "Canal", teacher_id, [teacher_id])
    msg_id = add_message(app, channel_id, teacher_id, "Reglement important")
    login(client, teacher_id)
    resp = client.post(
        f"/messages/channels/{channel_id}",
        data={"action": "toggle_pin", "message_id": str(msg_id), "pinned": "1"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Epingles" in resp.data
    assert b"Reglement important" in resp.data
    with app.app_context():
        from app.extensions import db

        assert db.session.get(MessageModel, msg_id).is_pinned is True


def test_pin_message_requires_admin_or_teacher(client, app):
    admin_id = create_user(app, role="ADMIN", email="pin2@t.local")
    parent_id = create_user(app, role="PARENT", email="pin3@t.local")
    channel_id = create_channel(app, "Canal", admin_id, [admin_id, parent_id])
    msg_id = add_message(app, channel_id, admin_id, "Reglement")
    login(client, parent_id)
    resp = client.post(
        f"/messages/channels/{channel_id}",
        data={"action": "toggle_pin", "message_id": str(msg_id), "pinned": "1"},
        follow_redirects=True,
    )
    assert b"Only admins and teachers can pin messages" in resp.data
    with app.app_context():
        from app.extensions import db

        assert db.session.get(MessageModel, msg_id).is_pinned is False


def test_channel_detail_hides_pin_for_parent(client, app):
    admin_id = create_user(app, role="ADMIN", email="pin4@t.local")
    parent_id = create_user(app, role="PARENT", email="pin5@t.local")
    channel_id = create_channel(app, "Canal", admin_id, [admin_id, parent_id])
    add_message(app, channel_id, admin_id, "Bonjour")
    login(client, parent_id)
    resp = client.get(f"/messages/channels/{channel_id}")
    assert resp.status_code == 200
    assert b'name="action" value="toggle_pin"' not in resp.data


def test_channel_detail_search_results(client, app):
    admin_id = create_user(app, role="ADMIN", email="srch1@t.local")
    channel_id = create_channel(app, "Canal", admin_id, [admin_id])
    add_message(app, channel_id, admin_id, "Hello world")
    add_message(app, channel_id, admin_id, "Bonjour le monde")
    login(client, admin_id)
    resp = client.get(f"/messages/channels/{channel_id}?q=hello")
    assert resp.status_code == 200
    assert b"Hello world" in resp.data
    assert b"Bonjour" not in resp.data


def test_channel_detail_search_rejects_non_member(client, app):
    owner_id = create_user(app, role="ADMIN", email="srch2@t.local")
    outsider_id = create_user(app, role="PARENT", email="srch3@t.local")
    channel_id = create_channel(app, "Prive", owner_id, [owner_id])
    add_message(app, channel_id, owner_id, "secret information")
    login(client, outsider_id)
    resp = client.get(
        f"/messages/channels/{channel_id}?q=secret", follow_redirects=True
    )
    assert b"User is not member of this channel" in resp.data


def test_channel_detail_search_no_results(client, app):
    admin_id = create_user(app, role="ADMIN", email="srch4@t.local")
    channel_id = create_channel(app, "Canal", admin_id, [admin_id])
    add_message(app, channel_id, admin_id, "Hello world")
    login(client, admin_id)
    resp = client.get(f"/messages/channels/{channel_id}?q=doesnotexist")
    assert resp.status_code == 200
    assert b"Aucun message" in resp.data


def test_channels_page_requires_login(client):
    response = client.get("/messages/channels")
    assert response.status_code == 302


def test_new_conversation_page_requires_login(client):
    response = client.get("/messages/new-conversation")
    assert response.status_code == 302


def test_templates_page_requires_login(client):
    response = client.get("/messages/templates")
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


def test_channel_creation_renders_member_picker(client, app):
    teacher_id = create_user(app, role="TEACHER", email="t5@t.local")
    login(client, teacher_id)
    response = client.get("/messages/channels")
    assert response.status_code == 200
    assert b"data-member-picker" in response.data
    assert b"data-member-search" in response.data
    assert b"data-selected-count" in response.data
    assert b"data-clear-selection" in response.data


def test_channel_creation_groups_members_by_role(client, app):
    admin_id = create_user(app, role="ADMIN", email="a5@t.local", full_name="Aimee Admin")
    teacher_id = create_user(app, role="TEACHER", email="t6@t.local", full_name="Benoit Teacher")
    parent_id = create_user(app, role="PARENT", email="p6@t.local", full_name="Celine Parent")
    login(client, teacher_id)
    response = client.get("/messages/channels")
    admin_pos = response.data.index(b'data-role-group="ADMIN"')
    teacher_pos = response.data.index(b'data-role-group="TEACHER"')
    parent_pos = response.data.index(b'data-role-group="PARENT"')
    assert admin_pos < teacher_pos < parent_pos
    assert response.data.count(f'id="member_{parent_id}"'.encode()) == 1
    assert response.data.count(f'id="member_{teacher_id}"'.encode()) == 1
    assert response.data.count(f'id="member_{admin_id}"'.encode()) == 1


def test_channel_creation_marks_creator_checked_and_disabled(client, app):
    teacher_id = create_user(app, role="TEACHER", email="t7@t.local")
    login(client, teacher_id)
    response = client.get("/messages/channels")
    assert (
        f'value="{teacher_id}" id="member_{teacher_id}" checked disabled'.encode()
        in response.data
    )


def test_channel_creation_preserves_selection_on_error(client, app):
    teacher_id = create_user(app, role="TEACHER", email="t8@t.local")
    parent_id = create_user(app, role="PARENT", email="p8@t.local")
    login(client, teacher_id)
    response = client.post(
        "/messages/channels",
        data={"name": "  ", "members": [str(parent_id)]},
    )
    assert response.status_code == 200
    assert f'value="{parent_id}" id="member_{parent_id}" checked'.encode() in response.data


def test_channel_creation_preserves_name_on_error(client, app):
    teacher_id = create_user(app, role="TEACHER", email="t9@t.local")
    login(client, teacher_id)
    long_name = "A" * 121
    response = client.post(
        "/messages/channels", data={"name": long_name, "members": []}
    )
    assert response.status_code == 200
    assert b"at most 120 characters" in response.data
    assert f'value="{long_name}"'.encode() in response.data


def test_channel_detail_add_members_renders_picker(client, app):
    admin_id = create_user(app, role="ADMIN", email="a6@t.local")
    parent_id = create_user(app, role="PARENT", email="p9@t.local", full_name="Celine Parent")
    channel_id = create_channel(app, "Canal", admin_id, [admin_id])
    login(client, admin_id)
    response = client.get(f"/messages/channels/{channel_id}")
    assert response.status_code == 200
    assert b"data-member-picker" in response.data
    assert b'data-role-group="PARENT"' in response.data
    assert b"data-member-search" in response.data
    assert f'id="member_add_{parent_id}"'.encode() in response.data


def test_new_conversation_page_renders_contacts(client, app):
    teacher_id = create_user(app, role="TEACHER", email="nc1@t.local", full_name="Noemie Teacher")
    parent_id = create_user(app, role="PARENT", email="nc2@t.local", full_name="Pierre Parent")
    login(client, teacher_id)
    response = client.get("/messages/new-conversation")
    assert response.status_code == 200
    assert f'id="contact_{parent_id}"'.encode() in response.data
    assert f'id="contact_{teacher_id}"'.encode() not in response.data


def test_open_direct_conversation_creates(client, app):
    teacher_id = create_user(app, role="TEACHER", email="nc3@t.local")
    parent_id = create_user(app, role="PARENT", email="nc4@t.local")
    login(client, teacher_id)
    response = client.post(
        "/messages/new-conversation",
        data={"member": str(parent_id)},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Conversation creee" in response.data
    with app.app_context():
        direct = ChannelModel.query.filter_by(kind="direct").first()
        assert direct is not None
        assert direct.name == "User PARENT - User TEACHER"


def test_open_direct_conversation_reuses_existing(client, app):
    teacher_id = create_user(app, role="TEACHER", email="nc5@t.local")
    parent_id = create_user(app, role="PARENT", email="nc6@t.local")
    login(client, teacher_id)
    client.post("/messages/new-conversation", data={"member": str(parent_id)})
    client.post("/messages/new-conversation", data={"member": str(parent_id)})
    with app.app_context():
        assert ChannelModel.query.filter_by(kind="direct").count() == 1


def test_open_direct_conversation_requires_member(client, app):
    teacher_id = create_user(app, role="TEACHER", email="nc7@t.local")
    login(client, teacher_id)
    response = client.post(
        "/messages/new-conversation", data={"member": ""}, follow_redirects=True
    )
    assert b"Selectionnez un contact" in response.data


def test_channels_page_lists_direct_and_group_sections(client, app):
    teacher_id = create_user(app, role="TEACHER", email="nc8@t.local")
    parent_id = create_user(app, role="PARENT", email="nc9@t.local")
    create_channel(app, "Classe X", teacher_id, [parent_id])
    login(client, teacher_id)
    client.post("/messages/new-conversation", data={"member": str(parent_id)})
    response = client.get("/messages/channels")
    assert response.status_code == 200
    assert b"Conversations" in response.data
    assert b"Canaux" in response.data
    assert b"Classe X" in response.data


def test_channel_detail_hides_add_members_for_direct(client, app):
    teacher_id = create_user(app, role="TEACHER", email="nc10@t.local")
    parent_id = create_user(app, role="PARENT", email="nc11@t.local")
    login(client, teacher_id)
    client.post("/messages/new-conversation", data={"member": str(parent_id)})
    with app.app_context():
        direct_id = ChannelModel.query.filter_by(kind="direct").first().id
    response = client.get(f"/messages/channels/{direct_id}")
    assert response.status_code == 200
    assert b"Ajouter des membres" not in response.data


def test_channel_detail_hides_members_card_for_direct(client, app):
    teacher_id = create_user(app, role="TEACHER", email="nc14@t.local")
    parent_id = create_user(app, role="PARENT", email="nc15@t.local")
    login(client, teacher_id)
    client.post("/messages/new-conversation", data={"member": str(parent_id)})
    with app.app_context():
        direct_id = ChannelModel.query.filter_by(kind="direct").first().id
    response = client.get(f"/messages/channels/{direct_id}")
    assert response.status_code == 200
    assert b">Membres</h2>" not in response.data
    assert b"col-lg-12" in response.data


def test_channel_detail_shows_members_card_for_group(client, app):
    admin_id = create_user(app, role="ADMIN", email="nc16@t.local")
    channel_id = create_channel(app, "Classe", admin_id, [admin_id])
    login(client, admin_id)
    response = client.get(f"/messages/channels/{channel_id}")
    assert response.status_code == 200
    assert b">Membres</h2>" in response.data
    assert b"col-lg-12" not in response.data


def test_add_members_rejected_for_direct(client, app):
    teacher_id = create_user(app, role="TEACHER", email="nc12@t.local")
    parent_id = create_user(app, role="PARENT", email="nc13@t.local")
    login(client, teacher_id)
    client.post("/messages/new-conversation", data={"member": str(parent_id)})
    with app.app_context():
        direct_id = ChannelModel.query.filter_by(kind="direct").first().id
    response = client.post(
        f"/messages/channels/{direct_id}",
        data={"action": "add_members", "members": [str(teacher_id)]},
        follow_redirects=True,
    )
    assert b"Cannot add members to a direct conversation" in response.data


def test_create_message_template_route(client, app):
    teacher_id = create_user(app, role="TEACHER", email="mt1@t.local")
    login(client, teacher_id)
    response = client.post(
        "/messages/templates",
        data={"label": "Reponse", "content": "Bonjour"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Modele cree" in response.data
    assert b"Reponse" in response.data


def test_create_message_template_requires_label(client, app):
    teacher_id = create_user(app, role="TEACHER", email="mt2@t.local")
    login(client, teacher_id)
    response = client.post(
        "/messages/templates",
        data={"label": "  ", "content": "Bonjour"},
        follow_redirects=True,
    )
    assert b"Label is required" in response.data


def test_delete_message_template_route(client, app):
    teacher_id = create_user(app, role="TEACHER", email="mt3@t.local")
    login(client, teacher_id)
    client.post(
        "/messages/templates", data={"label": "Reponse", "content": "Bonjour"}
    )
    with app.app_context():
        template_id = MessageTemplateModel.query.first().id
    response = client.post(
        f"/messages/templates/{template_id}/delete", follow_redirects=True
    )
    assert b"Modele supprime" in response.data
    with app.app_context():
        assert MessageTemplateModel.query.count() == 0


def test_delete_template_rejects_other_owner(client, app):
    teacher_id = create_user(app, role="TEACHER", email="mt5@t.local")
    other_id = create_user(app, role="TEACHER", email="mt6@t.local")
    with app.app_context():
        from app.extensions import db

        db.session.add(
            MessageTemplateModel(owner_id=other_id, label="Autre", content="Contenu")
        )
        db.session.commit()
        template_id = MessageTemplateModel.query.first().id
    login(client, teacher_id)
    response = client.post(
        f"/messages/templates/{template_id}/delete", follow_redirects=True
    )
    assert b"Only the owner can delete this template" in response.data
    with app.app_context():
        assert MessageTemplateModel.query.count() == 1


def test_template_picker_renders_in_channel(client, app):
    admin_id = create_user(app, role="ADMIN", email="mt4@t.local")
    channel_id = create_channel(app, "Canal", admin_id, [admin_id])
    login(client, admin_id)
    client.post("/messages/templates", data={"label": "Reponse", "content": "Bonjour"})
    response = client.get(f"/messages/channels/{channel_id}")
    assert response.status_code == 200
    assert b"data-template-picker" in response.data
    assert b"data-template-content" in response.data


def test_channel_detail_shows_template_entry_without_templates(client, app):
    admin_id = create_user(app, role="ADMIN", email="mt7@t.local")
    channel_id = create_channel(app, "Canal", admin_id, [admin_id])
    login(client, admin_id)
    response = client.get(f"/messages/channels/{channel_id}")
    assert response.status_code == 200
    assert b"Gerer mes modeles" in response.data


def test_channels_page_links_to_message_templates(client, app):
    parent_id = create_user(app, role="PARENT", email="mt8@t.local")
    login(client, parent_id)
    response = client.get("/messages/channels")
    assert response.status_code == 200
    assert b"Mes modeles de messages" in response.data


def test_channels_page_has_top_new_conversation_cta(client, app):
    teacher_id = create_user(app, role="TEACHER", email="nc7@t.local")
    login(client, teacher_id)
    response = client.get("/messages/channels")
    assert response.status_code == 200
    html = response.data.decode()
    cta = html.find("/messages/new-conversation")
    first_card = html.find(">Creer un canal<")
    assert cta != -1
    assert first_card != -1
    assert cta < first_card


def test_edit_template_page_requires_login(client):
    response = client.get("/messages/templates/1/edit")
    assert response.status_code == 302


def test_edit_template_renders_form(client, app):
    teacher_id = create_user(app, role="TEACHER", email="mt9@t.local")
    login(client, teacher_id)
    client.post("/messages/templates", data={"label": "Reponse", "content": "Bonjour"})
    with app.app_context():
        template_id = MessageTemplateModel.query.first().id
    response = client.get(f"/messages/templates/{template_id}/edit")
    assert response.status_code == 200
    assert b"Modifier le modele" in response.data
    assert b"value=\"Reponse\"" in response.data


def test_edit_template_updates(client, app):
    teacher_id = create_user(app, role="TEACHER", email="mt10@t.local")
    login(client, teacher_id)
    client.post("/messages/templates", data={"label": "Reponse", "content": "Bonjour"})
    with app.app_context():
        template_id = MessageTemplateModel.query.first().id
    response = client.post(
        f"/messages/templates/{template_id}/edit",
        data={"label": "Nouveau", "content": "Mis a jour"},
        follow_redirects=True,
    )
    assert b"Modele mis a jour" in response.data
    with app.app_context():
        from app.extensions import db

        template = db.session.get(MessageTemplateModel, template_id)
        assert template.label == "Nouveau"
        assert template.content == "Mis a jour"


def test_edit_template_rejects_other_owner(client, app):
    teacher_id = create_user(app, role="TEACHER", email="mt11@t.local")
    other_id = create_user(app, role="TEACHER", email="mt12@t.local")
    with app.app_context():
        from app.extensions import db

        db.session.add(
            MessageTemplateModel(owner_id=other_id, label="Autre", content="Contenu")
        )
        db.session.commit()
        template_id = MessageTemplateModel.query.first().id
    login(client, teacher_id)
    response = client.post(
        f"/messages/templates/{template_id}/edit",
        data={"label": "X", "content": "y"},
        follow_redirects=True,
    )
    assert b"Template not found" in response.data
    with app.app_context():
        from app.extensions import db

        template = db.session.get(MessageTemplateModel, template_id)
        assert template.label == "Autre"


def test_channels_page_renders_notification_toggles(client, app):
    teacher_id = create_user(app, role="TEACHER", email="notif1@t.local")
    channel_id = create_channel(app, "Canal", teacher_id, [teacher_id])
    login(client, teacher_id)
    resp = client.get("/messages/channels")
    assert resp.status_code == 200
    assert b"notif-global-toggle" in resp.data
    assert b"Recevoir toutes les notifications" in resp.data
    assert f"/messages/channels/{channel_id}/notifications".encode() in resp.data
    assert b"bi-bell" in resp.data


def test_global_notifications_toggle_persists(client, app):
    teacher_id = create_user(app, role="TEACHER", email="notif2@t.local")
    login(client, teacher_id)
    resp = client.post(
        "/messages/notifications/global",
        data={"enabled": "0"},
        follow_redirects=True,
    )
    assert b"Notifications globales desactivees" in resp.data
    with app.app_context():
        from app.extensions import db
        from app.infrastructure.database.models import UserNotificationSettingModel

        row = db.session.get(UserNotificationSettingModel, teacher_id)
        assert row is not None and row.global_enabled is False


def test_channel_notifications_toggle_persists(client, app):
    teacher_id = create_user(app, role="TEACHER", email="notif3@t.local")
    channel_id = create_channel(app, "Canal", teacher_id, [teacher_id])
    login(client, teacher_id)
    resp = client.post(
        f"/messages/channels/{channel_id}/notifications",
        follow_redirects=True,
    )
    assert b"Notifications desactivees" in resp.data
    with app.app_context():
        from app.extensions import db
        from app.infrastructure.database.models import ChannelNotificationSettingModel

        row = db.session.get(
            ChannelNotificationSettingModel, (teacher_id, channel_id)
        )
        assert row is not None and row.enabled is False


def test_channel_notifications_toggle_requires_membership(client, app):
    owner_id = create_user(app, role="TEACHER", email="notif4@t.local")
    outsider_id = create_user(app, role="PARENT", email="notif5@t.local")
    channel_id = create_channel(app, "Canal", owner_id, [owner_id])
    login(client, outsider_id)
    resp = client.post(
        f"/messages/channels/{channel_id}/notifications",
        follow_redirects=True,
    )
    assert b"User is not member of this channel" in resp.data
    with app.app_context():
        from app.extensions import db
        from app.infrastructure.database.models import ChannelNotificationSettingModel

        row = db.session.get(
            ChannelNotificationSettingModel, (outsider_id, channel_id)
        )
        assert row is None


def test_channel_detail_toggle_notifications(client, app):
    teacher_id = create_user(app, role="TEACHER", email="notif6@t.local")
    channel_id = create_channel(app, "Canal", teacher_id, [teacher_id])
    add_message(app, channel_id, teacher_id, "Bonjour")
    login(client, teacher_id)
    resp = client.post(
        f"/messages/channels/{channel_id}",
        data={"action": "toggle_notifications"},
        follow_redirects=True,
    )
    assert b"Notifications desactivees" in resp.data
    with app.app_context():
        from app.extensions import db
        from app.infrastructure.database.models import ChannelNotificationSettingModel

        row = db.session.get(
            ChannelNotificationSettingModel, (teacher_id, channel_id)
        )
        assert row is not None and row.enabled is False


# ---------------------------------------------------------------------------
# Find parent
# ---------------------------------------------------------------------------

def test_find_parent_requires_login(client):
    resp = client.get("/messages/find-parent")
    assert resp.status_code == 302


def test_find_parent_requires_teacher_or_admin(client, app):
    parent_id = create_user(app, role="PARENT", email="fp1@t.local")
    login(client, parent_id)
    resp = client.get("/messages/find-parent", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Acces r" in resp.data


def test_find_parent_renders_search_form(client, app):
    teacher_id = create_user(app, role="TEACHER", email="fp2@t.local")
    login(client, teacher_id)
    resp = client.get("/messages/find-parent")
    assert resp.status_code == 200
    assert b"Trouver un parent" in resp.data
    assert b"Nom de l" in resp.data


def test_find_parent_shows_results(client, app):
    teacher_id = create_user(app, role="TEACHER", email="fp3@t.local")
    parent_id = create_user(app, role="PARENT", email="fp4@t.local", full_name="Marie Dupont")
    from app.infrastructure.database.models import ChildModel
    from app.extensions import db
    with app.app_context():
        child = ChildModel(parent_id=parent_id, full_name="Alice Dupont", class_name="CM1")
        db.session.add(child)
        db.session.commit()

    login(client, teacher_id)
    resp = client.get("/messages/find-parent?q=Alice")
    assert resp.status_code == 200
    assert b"Alice Dupont" in resp.data
    assert b"Marie Dupont" in resp.data
    assert b"Contacter" in resp.data


def test_find_parent_post_opens_conversation(client, app):
    teacher_id = create_user(app, role="TEACHER", email="fp5@t.local")
    parent_id = create_user(app, role="PARENT", email="fp6@t.local")
    login(client, teacher_id)
    resp = client.post(
        "/messages/find-parent",
        data={"parent_id": str(parent_id)},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Conversation creee" in resp.data

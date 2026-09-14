from tests.helpers import (
    add_announcement,
    add_calendar_event,
    add_message,
    add_notification,
    create_channel,
    create_user,
    login,
)


def test_opening_channel_marks_its_notifications_read(app, client):
    from app.extensions import db
    from app.infrastructure.database.models import NotificationModel

    parent_id = create_user(app, role="PARENT", email="dash.markread@t.local")
    teacher_id = create_user(
        app, role="TEACHER", email="dash.markread.t@t.local",
        full_name="Teacher Mark",
    )
    channel_id = create_channel(app, "CM2", teacher_id, [teacher_id, parent_id])
    notif_id = add_notification(app, parent_id, "Nouveau message", channel_id=channel_id)

    login(client, parent_id)
    resp = client.get(f"/messages/channels/{channel_id}")
    assert resp.status_code == 200

    with app.app_context():
        row = db.session.get(NotificationModel, notif_id)
        assert row.is_read is True


def test_dashboard_shows_stat_cards_for_all_roles(app, client):
    user_id = create_user(app, role="PARENT", email="dash.parent@t.local")
    login(client, user_id)
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"stat-card" in resp.data
    assert b"Non lus" in resp.data
    assert b"Conversations" in resp.data
    assert b"Annonces non lues" in resp.data


def test_parent_sees_children_panel(app, client):
    parent_id = create_user(app, role="PARENT", email="dash.parent@t.local")
    login(client, parent_id)

    from app.extensions import db
    from app.infrastructure.database.models import ChildModel

    with app.app_context():
        db.session.add(
            ChildModel(
                parent_id=parent_id, full_name="Emma Dupont", class_name="CM2"
            )
        )
        db.session.commit()

    resp = client.get("/")
    assert b"Mes enfants" in resp.data
    assert b"Emma Dupont" in resp.data


def test_parent_without_children_gets_onboarding_hint(app, client):
    parent_id = create_user(app, role="PARENT", email="dash.parent@t.local")
    login(client, parent_id)
    resp = client.get("/")
    assert b"Aucun enfant" in resp.data


def test_teacher_sees_conversations_with_latest_message(app, client):
    teacher_id = create_user(app, role="TEACHER", email="dash.teacher@t.local", full_name="Teacher One")
    login(client, teacher_id)
    channel_id = create_channel(app, "CM2", teacher_id, [teacher_id])
    add_message(app, channel_id, teacher_id, "Dernier message important")

    resp = client.get("/")
    assert b"CM2" in resp.data
    assert b"Dernier message important" in resp.data


def test_admin_sees_platform_stats_and_recent_signups(app, client):
    admin_id = create_user(app, role="ADMIN", email="dash.admin@t.local", full_name="Admin Chief")
    teacher_id = create_user(app, role="TEACHER", email="dash.teacher2@t.local", full_name="Teacher Two")
    create_channel(app, "CM2", teacher_id, [teacher_id])
    add_announcement(app, "Rentree", "Bienvenue", teacher_id)

    login(client, admin_id)
    resp = client.get("/")
    assert b"plateforme" in resp.data
    assert b"Inscriptions r\xc3\xa9centes" in resp.data
    assert b"Teacher Two" in resp.data
    assert b"1" in resp.data


def test_dashboard_renders_empty_state_when_no_activity(app, client):
    user_id = create_user(app, role="PARENT", email="dash.parent@t.local")
    login(client, user_id)
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Aucune activit\xc3\xa9 r\xc3\xa9cente" in resp.data


def test_dashboard_shows_calendar_summary_with_upcoming_deadline(app, client):
    parent_id = create_user(app, role="PARENT", email="dash.calendar@t.local")
    from datetime import datetime, timedelta

    add_calendar_event(
        app,
        "Rendu fiches cantine",
        type_value="deadline",
        start_date=datetime.now() + timedelta(days=5),
    )
    login(client, parent_id)
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Calendrier scolaire" in resp.data
    assert b"Rendu fiches cantine" in resp.data
    assert b"Voir le calendrier" in resp.data


def test_dashboard_shows_calendar_empty_state_when_no_events(app, client):
    user_id = create_user(app, role="TEACHER", email="dash.calendar.empty@t.local")
    login(client, user_id)
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Calendrier scolaire" in resp.data
    assert "Aucune date planifiée".encode() in resp.data
    assert b"Ouvrir le calendrier" in resp.data
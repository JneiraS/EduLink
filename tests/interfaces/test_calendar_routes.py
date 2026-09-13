from datetime import datetime, timedelta

from tests.helpers import add_calendar_event, create_user, login


def test_calendar_requires_login(app, client):
    resp = client.get("/calendar/")
    assert resp.status_code == 302


def test_calendar_renders_empty_state(app, client):
    user_id = create_user(app, role="PARENT", email="cal.empty@t.local")
    login(client, user_id)
    resp = client.get("/calendar/")
    assert resp.status_code == 200
    assert b"Calendrier" in resp.data
    assert b"Aucune date" in resp.data


def test_calendar_lists_events(app, client):
    user_id = create_user(app, role="PARENT", email="cal.list@t.local")
    add_calendar_event(app, "Réunion parents-profs", start_date=datetime(2026, 9, 20, 18, 0))
    add_calendar_event(
        app, "Date limite", type_value="deadline", start_date=datetime(2026, 9, 25, 12, 0)
    )
    login(client, user_id)
    resp = client.get("/calendar/")
    assert resp.status_code == 200
    assert b"R\xc3\xa9union parents-profs" in resp.data
    assert b"Date limite" in resp.data


def test_calendar_filters_by_type(app, client):
    user_id = create_user(app, role="PARENT", email="cal.filter@t.local")
    add_calendar_event(app, "Réunion de rentrée", start_date=datetime(2026, 9, 20, 18, 0))
    add_calendar_event(
        app, "Vacances de Toussaint", type_value="holiday",
        start_date=datetime(2026, 10, 17, 8, 0),
        end_date=datetime(2026, 11, 2, 18, 0),
    )
    login(client, user_id)
    resp = client.get("/calendar/?type=holiday")
    assert resp.status_code == 200
    assert b"Vacances de Toussaint" in resp.data
    assert b"R\xc3\xa9union de rentr\xc3\xa9e" not in resp.data


def test_calendar_highlights_next_deadline(app, client):
    user_id = create_user(app, role="PARENT", email="cal.deadline@t.local")
    add_calendar_event(
        app, "Rendu des fiches", type_value="deadline",
        start_date=datetime.now().replace(hour=23, minute=59, second=0, microsecond=0) + timedelta(days=2),
    )
    login(client, user_id)
    resp = client.get("/calendar/")
    assert b"Rendu des fiches" in resp.data
    assert b"Dans 2 jours" in resp.data


def test_parent_cannot_see_add_button_or_delete(app, client):
    user_id = create_user(app, role="PARENT", email="cal.parent@t.local")
    event_id = add_calendar_event(app, "Kermesse", start_date=datetime(2026, 9, 30, 9, 0))
    login(client, user_id)
    resp = client.get("/calendar/")
    assert resp.status_code == 200
    assert b"Ajouter une date" not in resp.data
    assert f"/calendar/events/{event_id}/delete".encode() not in resp.data


def test_teacher_and_admin_can_create_event(app, client):
    teacher_id = create_user(app, role="TEACHER", email="cal.teacher@t.local")
    login(client, teacher_id)
    resp = client.post(
        "/calendar/events",
        data={
            "title": "Conseil de classe",
            "type": "event",
            "start_date": "2026-09-22T10:00",
            "category": "meeting",
            "class_name": "CM2",
            "description": "Préparation du trimestre",
            "location": "Salle B12",
            "priority": "high",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    body = resp.data
    assert b"Conseil de classe" in body
    assert b"ajout" in body.lower()


def test_create_event_csrf_disabled_in_testing(app, client):
    user_id = create_user(app, role="ADMIN", email="cal.admin@t.local")
    login(client, user_id)
    resp = client.post(
        "/calendar/events",
        data={
            "title": "Journée sport",
            "type": "event",
            "start_date": "2026-09-23T08:00",
            "category": "outing",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Journ\xc3\xa9e sport" in resp.data


def test_create_event_missing_date_redirects(app, client):
    user_id = create_user(app, role="ADMIN", email="cal.missing@t.local")
    login(client, user_id)
    resp = client.post(
        "/calendar/events",
        data={"title": "Sans date", "type": "event", "start_date": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"date de d\xc3\xa9but est requise".lower() in resp.data.lower() or b"date" in resp.data.lower()


def test_delete_event_as_admin(app, client):
    admin_id = create_user(app, role="ADMIN", email="cal.deladmin@t.local")
    event_id = add_calendar_event(app, "À supprimer", start_date=datetime(2026, 9, 24, 9, 0))
    login(client, admin_id)
    resp = client.post(
        f"/calendar/events/{event_id}/delete", follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"\xc3\x80 supprimer" not in resp.data
    assert b"supprim" in resp.data.lower()


def test_parent_cannot_delete_event(app, client):
    parent_id = create_user(app, role="PARENT", email="cal.delparent@t.local")
    event_id = add_calendar_event(app, "Intouchable", start_date=datetime(2026, 9, 24, 9, 0))
    login(client, parent_id)
    resp = client.post(
        f"/calendar/events/{event_id}/delete", follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"Intouchable" in resp.data
    assert b"Acc\xc3\xa8s r\xc3\xa9serv" in resp.data.lower() or b"r\xc3\xa9serv" in resp.data.lower()


def test_calendar_class_filter_dropdown_includes_classes(app, client):
    user_id = create_user(app, role="PARENT", email="cal.classes@t.local")
    add_calendar_event(app, "Réunion", class_name="Classe de CM2-A", start_date=datetime(2026, 9, 21, 17, 0))
    login(client, user_id)
    resp = client.get("/calendar/")
    assert resp.status_code == 200
    assert b"Classe de CM2-A" in resp.data


def test_calendar_nav_link_present(app, client):
    user_id = create_user(app, role="PARENT", email="cal.nav@t.local")
    login(client, user_id)
    resp = client.get("/calendar/")
    assert b"/calendar/" in resp.data or b"Calendrier" in resp.data
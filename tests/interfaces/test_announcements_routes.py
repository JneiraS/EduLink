import io

from app.infrastructure.database.models import AnnouncementReadModel, NotificationModel, UserModel
from tests.helpers import (
    add_announcement,
    create_channel,
    create_user,
    login,
)


def _pdf_bytes():
    return io.BytesIO(b"%PDF-1.4 fake pdf content")


def test_list_requires_login(client):
    response = client.get("/announcements/")
    assert response.status_code == 302


def test_parent_cannot_create(client, app):
    parent_id = create_user(app, role="PARENT", email="p@t.local")
    login(client, parent_id)
    response = client.post(
        "/announcements/new",
        data={"title": "T", "content": "C"},
        follow_redirects=True,
    )
    assert b"peuvent cr\xc3\xa9er des annonces" in response.data


def test_teacher_can_create(client, app):
    teacher_id = create_user(app, role="TEACHER", email="t@t.local")
    login(client, teacher_id)
    response = client.post(
        "/announcements/new",
        data={"title": "Annonce", "content": "Contenu"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Annonce publi\xc3\xa9e" in response.data


def test_create_with_pdf_upload(client, app):
    admin_id = create_user(app, role="ADMIN", email="a@t.local")
    login(client, admin_id)
    response = client.post(
        "/announcements/new",
        data={
            "title": "Avec PDF",
            "content": "Doc",
            "document": (_pdf_bytes(), "cours.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Annonce publi\xc3\xa9e" in response.data


def test_create_page_shows_author_channels(client, app):
    teacher_id = create_user(app, role="TEACHER", email="t2@t.local")
    create_channel(app, "Classe B", teacher_id)
    login(client, teacher_id)
    response = client.get("/announcements/new")
    assert response.status_code == 200
    assert b"Classe B" in response.data
    assert b"target_channels" in response.data


def test_create_targeted_announcement_notifies_only_members(client, app):
    teacher_id = create_user(app, role="TEACHER", email="t3@t.local")
    parent_id = create_user(app, role="PARENT", email="p3@t.local")
    create_user(app, role="PARENT", email="p4@t.local")
    channel_id = create_channel(app, "Classe C", teacher_id, [parent_id])
    login(client, teacher_id)
    response = client.post(
        "/announcements/new",
        data={
            "title": "Ciblee",
            "content": "Contenu",
            "audience": "channels",
            "target_channels": str(channel_id),
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Annonce publi\xc3\xa9e" in response.data
    with app.app_context():
        notified = {n.user_id for n in NotificationModel.query.all()}
    assert notified == {teacher_id, parent_id}


def test_create_targeted_announcement_requires_channel(client, app):
    teacher_id = create_user(app, role="TEACHER", email="t4@t.local")
    login(client, teacher_id)
    response = client.post(
        "/announcements/new",
        data={
            "title": "Sans cible",
            "content": "Contenu",
            "audience": "channels",
        },
        follow_redirects=True,
    )
    assert b"Selectionnez au moins un canal" in response.data


def test_parent_can_confirm_read(client, app):
    teacher_id = create_user(app, role="TEACHER", email="cr1@t.local")
    parent_id = create_user(app, role="PARENT", email="cr2@t.local")
    ann_id = add_announcement(app, "Annonce", "Contenu", teacher_id)
    login(client, parent_id)
    response = client.post(f"/announcements/{ann_id}/confirm-read", follow_redirects=True)
    assert response.status_code == 200
    assert b"Lecture confirm\xc3\xa9e" in response.data
    with app.app_context():
        row = AnnouncementReadModel.query.filter_by(
            announcement_id=ann_id, user_id=parent_id
        ).first()
        assert row is not None


def test_list_shows_read_status_counts_for_teacher(client, app):
    teacher_id = create_user(app, role="TEACHER", email="cr3@t.local")
    create_user(app, role="PARENT", email="cr4@t.local")
    create_user(app, role="PARENT", email="cr5@t.local")
    add_announcement(app, "Annonce", "Contenu", teacher_id)
    login(client, teacher_id)
    response = client.get("/announcements/")
    with app.app_context():
        total = UserModel.query.count()
    assert f"Vu par 0/{total}".encode() in response.data


def test_list_shows_confirm_button_for_parent(client, app):
    teacher_id = create_user(app, role="TEACHER", email="cr6@t.local")
    parent_id = create_user(app, role="PARENT", email="cr7@t.local")
    create_user(app, role="PARENT", email="cr8@t.local")
    ann_id = add_announcement(app, "Annonce", "Contenu", teacher_id)
    login(client, parent_id)
    response = client.get("/announcements/")
    assert b"Confirmer la lecture" in response.data
    assert f"/announcements/{ann_id}/confirm-read".encode() in response.data


def test_list_shows_confirmed_state_after_read(client, app):
    teacher_id = create_user(app, role="TEACHER", email="cr9@t.local")
    parent_id = create_user(app, role="PARENT", email="cr10@t.local")
    ann_id = add_announcement(app, "Annonce", "Contenu", teacher_id)
    login(client, parent_id)
    client.post(f"/announcements/{ann_id}/confirm-read")
    response = client.get("/announcements/")
    assert b"Confirme" in response.data


def test_create_rejects_non_pdf(client, app):
    admin_id = create_user(app, role="ADMIN", email="a2@t.local")
    login(client, admin_id)
    response = client.post(
        "/announcements/new",
        data={
            "title": "Bad",
            "content": "Doc",
            "document": (io.BytesIO(b"not a pdf"), "evil.exe"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"Seuls les PDF sont autoris\xc3\xa9s" in response.data


def test_create_rejects_html_disguised_as_pdf(client, app):
    admin_id = create_user(app, role="ADMIN", email="a6@t.local")
    login(client, admin_id)
    response = client.post(
        "/announcements/new",
        data={
            "title": "Bad",
            "content": "Doc",
            "document": (io.BytesIO(b"<html><script>alert(1)</script></html>"), "cours.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"Seuls les PDF sont autoris\xc3\xa9s" in response.data


def test_download_missing_pdf_returns_404(client, app):
    admin_id = create_user(app, role="ADMIN", email="a3@t.local")
    login(client, admin_id)
    response = client.get("/announcements/files/nonexistent.pdf")
    assert response.status_code == 404


def test_download_rejects_non_pdf_extension(client, app):
    admin_id = create_user(app, role="ADMIN", email="a4@t.local")
    login(client, admin_id)
    response = client.get("/announcements/files/../../etc/passwd")
    assert response.status_code == 404


def test_list_paginates(client, app):
    admin_id = create_user(app, role="ADMIN", email="a5@t.local")
    for i in range(12):
        add_announcement(app, f"Annonce {i}", "contenu", admin_id)
    login(client, admin_id)
    response = client.get("/announcements/")
    assert response.status_code == 200
    assert b"Suivant" in response.data
    response_page2 = client.get("/announcements/?page=2")
    assert b"Page 2 / 2" in response_page2.data
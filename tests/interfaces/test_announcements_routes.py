import io

from tests.helpers import add_announcement, create_user, login


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
    assert b"Only admin and teachers" in response.data


def test_teacher_can_create(client, app):
    teacher_id = create_user(app, role="TEACHER", email="t@t.local")
    login(client, teacher_id)
    response = client.post(
        "/announcements/new",
        data={"title": "Annonce", "content": "Contenu"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Annonce publiee" in response.data


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
    assert b"Annonce publiee" in response.data


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
    assert b"Seuls les PDF sont autorises" in response.data


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
    assert b"Seuls les PDF sont autorises" in response.data


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
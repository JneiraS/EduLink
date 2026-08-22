import os
from pathlib import Path

from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from tests.helpers import (
    add_announcement,
    add_message,
    add_notification,
    create_channel,
    create_user,
    login,
)


def _uploads_dir(app) -> str:
    return os.path.abspath(
        os.path.join(app.root_path, "..", app.config["UPLOAD_FOLDER"])
    )


def _write_pdf(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(b"%PDF-1.4\n%%EOF\n")


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------

def test_admin_members_page_requires_login(client):
    response = client.get("/admin/members")
    assert response.status_code == 302


def test_admin_members_page_requires_admin(client, app):
    teacher_id = create_user(app, role="TEACHER", email="t@admin.local")
    login(client, teacher_id)
    response = client.get("/admin/members", follow_redirects=True)
    assert response.status_code == 200
    assert b"Acces reserve a l" in response.data


def test_admin_role_change_requires_admin(client, app):
    teacher_id = create_user(app, role="TEACHER", email="t2@admin.local")
    parent_id = create_user(app, role="PARENT", email="p2@admin.local")
    login(client, teacher_id)
    response = client.post(
        f"/admin/members/{parent_id}/role",
        data={"role": "TEACHER"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        user = SQLAlchemyUserRepository().find_by_id(parent_id)
        assert user.role.value == "PARENT"


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------

def test_admin_members_page_lists_users(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin@admin.local")
    create_user(app, role="TEACHER", email="teacher@admin.local", full_name="Marie Prof")
    create_user(app, role="PARENT", email="parent@admin.local", full_name="Paul Parent")
    login(client, admin_id)

    response = client.get("/admin/members")
    assert response.status_code == 200
    assert b"Marie Prof" in response.data
    assert b"Paul Parent" in response.data


def test_admin_members_page_links_to_create_user(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin11@admin.local")
    login(client, admin_id)
    response = client.get("/admin/members")
    assert response.status_code == 200
    assert b"/auth/users/new" in response.data
    assert b"Creer un utilisateur" in response.data


def test_admin_role_change_success(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin2@admin.local")
    parent_id = create_user(app, role="PARENT", email="parent2@admin.local")
    login(client, admin_id)

    response = client.post(
        f"/admin/members/{parent_id}/role",
        data={"role": "TEACHER"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Role mis a jour" in response.data
    with app.app_context():
        user = SQLAlchemyUserRepository().find_by_id(parent_id)
        assert user.role.value == "TEACHER"


def test_admin_role_change_rejects_self_demotion(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin3@admin.local")
    login(client, admin_id)

    response = client.post(
        f"/admin/members/{admin_id}/role",
        data={"role": "PARENT"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"own role" in response.data
    with app.app_context():
        user = SQLAlchemyUserRepository().find_by_id(admin_id)
        assert user.role.value == "ADMIN"


def test_admin_toggle_active_success_blocks_login(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin4@admin.local")
    teacher_id = create_user(app, role="TEACHER", email="victime@admin.local")
    login(client, admin_id)

    response = client.post(
        f"/admin/members/{teacher_id}/toggle-active", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Compte desactive" in response.data
    with app.app_context():
        user = SQLAlchemyUserRepository().find_by_id(teacher_id)
        assert user.is_active is False

    client.post("/auth/logout")
    login_response = client.post(
        "/auth/login",
        data={"email": "victime@admin.local", "password": "secret"},
    )
    assert login_response.status_code == 200
    assert b"Invalid credentials" in login_response.data


def test_admin_toggle_active_rejects_self(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin5@admin.local")
    login(client, admin_id)

    response = client.post(
        f"/admin/members/{admin_id}/toggle-active", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"own account" in response.data


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------

def test_admin_announcements_page_lists_announcements(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin6@admin.local")
    author_id = create_user(app, role="TEACHER", email="auteur@admin.local", full_name="Anne Auteur")
    add_announcement(app, title="Conseil de classe", content="Vendredi", created_by=author_id)
    login(client, admin_id)

    response = client.get("/admin/announcements")
    assert response.status_code == 200
    assert b"Conseil de classe" in response.data
    assert b"Anne Auteur" in response.data


def test_admin_delete_announcement_removes_pdf(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin7@admin.local")
    author_id = create_user(app, role="TEACHER", email="auteur2@admin.local")
    announcement_id = add_announcement(
        app, title="A supprimer", content="Contenu", created_by=author_id,
        pdf_filename="aaa111_cours.pdf",
    )
    uploads = _uploads_dir(app)
    _write_pdf(os.path.join(uploads, "aaa111_cours.pdf"))
    login(client, admin_id)

    response = client.post(
        f"/admin/announcements/{announcement_id}/delete", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Annonce supprimee" in response.data
    assert not os.path.exists(os.path.join(uploads, "aaa111_cours.pdf"))


def test_admin_delete_announcement_requires_admin(client, app):
    teacher_id = create_user(app, role="TEACHER", email="t3@admin.local")
    author_id = create_user(app, role="TEACHER", email="auteur3@admin.local")
    announcement_id = add_announcement(
        app, title="Garde", content="Contenu", created_by=author_id
    )
    login(client, teacher_id)

    response = client.post(
        f"/admin/announcements/{announcement_id}/delete", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Acces reserve a l" in response.data


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------

def test_admin_channels_page_lists_channels_with_member_counts(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin8@admin.local")
    teacher_id = create_user(app, role="TEACHER", email="t4@admin.local")
    create_channel(app, name="CM2", created_by=admin_id, member_ids=[admin_id, teacher_id])
    login(client, admin_id)

    response = client.get("/admin/channels")
    assert response.status_code == 200
    assert b"CM2" in response.data
    assert b"2" in response.data


def test_admin_delete_channel_cascades(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin9@admin.local")
    teacher_id = create_user(app, role="TEACHER", email="t5@admin.local")
    channel_id = create_channel(
        app, name="A purger", created_by=admin_id, member_ids=[admin_id, teacher_id]
    )
    add_message(app, channel_id=channel_id, sender_id=teacher_id, content="Old message")
    add_notification(app, user_id=teacher_id, content="Notif", channel_id=channel_id)
    login(client, admin_id)

    response = client.post(
        f"/admin/channels/{channel_id}/delete", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Canal supprime" in response.data


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

def test_admin_nav_link_visible_for_admin(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin10@admin.local")
    login(client, admin_id)
    admin_page = client.get("/").data
    assert b"Membres" in admin_page


def test_admin_nav_link_hidden_for_parent(client, app):
    parent_id = create_user(app, role="PARENT", email="p10@admin.local")
    login(client, parent_id)
    parent_page = client.get("/").data
    assert b"Membres" not in parent_page
    assert b"Mes enfants" in parent_page


def test_admin_pages_link_to_all_admin_sections(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin12@admin.local")
    login(client, admin_id)
    for page_url in ["/admin/members", "/admin/announcements", "/admin/channels"]:
        response = client.get(page_url)
        assert response.status_code == 200
        assert b"/admin/members" in response.data
        assert b"/admin/announcements" in response.data
        assert b"/admin/channels" in response.data


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def test_admin_stats_page_requires_login(client):
    response = client.get("/admin/stats")
    assert response.status_code == 302


def test_admin_stats_page_requires_admin(client, app):
    teacher_id = create_user(app, role="TEACHER", email="t6@admin.local")
    login(client, teacher_id)
    response = client.get("/admin/stats", follow_redirects=True)
    assert response.status_code == 200
    assert b"Acces reserve a l" in response.data


def test_admin_stats_page_renders_charts(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin13@admin.local")
    create_user(app, role="TEACHER", email="t7@admin.local")
    login(client, admin_id)

    response = client.get("/admin/stats")
    assert response.status_code == 200
    assert b"Statistiques" in response.data
    assert b"chart-users-by-role" in response.data
    assert b"chart-messages-by-day" in response.data
    assert b"chart-registrations" in response.data
    assert b"chart-top-channels" in response.data
    assert b"chart-read-rates" in response.data
    assert b"chart-push-adoption" in response.data
    assert b"data-chart=" in response.data
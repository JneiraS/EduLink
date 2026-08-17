from app.extensions import db
from app.infrastructure.database.models import (
    ChannelModel,
    ChildModel,
    channel_members,
)

from tests.helpers import create_channel, create_user, login


def _add_child(app, parent_id, full_name="Enfant Test", class_name="CM2"):
    with app.app_context():
        child = ChildModel(
            parent_id=parent_id,
            full_name=full_name,
            class_name=class_name,
        )
        db.session.add(child)
        db.session.commit()
        return child.id


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------


def test_admin_children_page_lists_children(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin_child@test.local")
    parent_id = create_user(app, role="PARENT", email="parent_child@test.local")
    _add_child(app, parent_id, full_name="Enfant Test", class_name="CM2")
    _add_child(app, parent_id, full_name="Enfant B", class_name="6eme A")
    login(client, admin_id)
    resp = client.get("/admin/children")
    assert resp.status_code == 200
    assert b"Enfant Test" in resp.data
    assert b"CM2" in resp.data
    assert b'<datalist id="class-list">' in resp.data
    assert b'<option value="CM2"></option>' in resp.data
    assert b'<option value="6eme A"></option>' in resp.data


def test_admin_children_page_requires_admin(client, app):
    teacher_id = create_user(app, role="TEACHER", email="teacher_child@test.local")
    login(client, teacher_id)
    resp = client.get("/admin/children", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Acces reserve" in resp.data


def test_admin_create_child_success(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin_create@test.local")
    parent_id = create_user(app, role="PARENT", email="parent_create@test.local")
    login(client, admin_id)
    resp = client.post(
        "/admin/children/create",
        data={"parent_id": str(parent_id), "full_name": "Leo Test", "class_name": "CM1"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        child = ChildModel.query.filter_by(full_name="Leo Test").first()
        assert child is not None
        assert child.parent_id == parent_id
        assert child.class_name == "CM1"


def test_admin_create_child_links_class_channel(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin_auto@test.local")
    parent_id = create_user(app, role="PARENT", email="parent_auto@test.local")
    login(client, admin_id)
    resp = client.post(
        "/admin/children/create",
        data={"parent_id": str(parent_id), "full_name": "Leo Auto", "class_name": "CM4"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        channel = ChannelModel.query.filter_by(name="CM4", kind="group").first()
        assert channel is not None
        rows = db.session.execute(
            channel_members.select().where(
                channel_members.c.channel_id == channel.id
            )
        ).all()
        assert parent_id in [row.user_id for row in rows]


def test_admin_create_child_rejects_non_parent(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin_t@test.local")
    teacher_id = create_user(app, role="TEACHER", email="teacher_t@test.local")
    login(client, admin_id)
    resp = client.post(
        "/admin/children/create",
        data={"parent_id": str(teacher_id), "full_name": "Leo", "class_name": "CM1"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        assert ChildModel.query.filter_by(full_name="Leo").first() is None


def test_admin_delete_child(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin_del@test.local")
    parent_id = create_user(app, role="PARENT", email="parent_del@test.local")
    child_id = _add_child(app, parent_id)
    login(client, admin_id)
    resp = client.post(f"/admin/children/{child_id}/delete", follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        assert db.session.get(ChildModel, child_id) is None


def test_admin_link_child_channels_creates_class_channel(client, app):
    admin_id = create_user(app, role="ADMIN", email="admin_link@test.local")
    parent_id = create_user(app, role="PARENT", email="parent_link@test.local")
    child_id = _add_child(app, parent_id, class_name="CM3")
    login(client, admin_id)
    resp = client.post(f"/admin/children/{child_id}/link-channels", follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        channel = ChannelModel.query.filter_by(name="CM3", kind="group").first()
        assert channel is not None
        rows = db.session.execute(
            channel_members.select().where(
                channel_members.c.channel_id == channel.id
            )
        ).all()
        assert parent_id in [row.user_id for row in rows]


# ---------------------------------------------------------------------------
# Parent routes
# ---------------------------------------------------------------------------


def test_parent_children_page_lists_children(client, app):
    parent_id = create_user(app, role="PARENT", email="pp@test.local")
    _add_child(app, parent_id, full_name="Enfant Parent", class_name="CP")
    login(client, parent_id)
    resp = client.get("/parent/children")
    assert resp.status_code == 200
    assert b"Enfant Parent" in resp.data


def test_parent_children_requires_parent(client, app):
    teacher_id = create_user(app, role="TEACHER", email="tp@test.local")
    login(client, teacher_id)
    resp = client.get("/parent/children", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Acces reserve" in resp.data


def test_parent_child_channels_lists_class_channels(client, app):
    parent_id = create_user(app, role="PARENT", email="pp2@test.local")
    teacher_id = create_user(app, role="TEACHER", email="tt2@test.local")
    child_id = _add_child(app, parent_id, class_name="CM2")
    create_channel(app, "CM2", teacher_id, member_ids=[parent_id])
    login(client, parent_id)
    resp = client.get(f"/parent/children/{child_id}/channels")
    assert resp.status_code == 200
    assert b"CM2" in resp.data
    assert b"/messages/channels" in resp.data


def test_parent_child_channels_other_parent_redirect(client, app):
    parent_a = create_user(app, role="PARENT", email="pa@test.local")
    parent_b = create_user(app, role="PARENT", email="pb@test.local")
    child_id = _add_child(app, parent_a, class_name="CM2")
    login(client, parent_b)
    resp = client.get(f"/parent/children/{child_id}/channels", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Enfant introuvable" in resp.data


def test_parent_child_channels_empty_state(client, app):
    parent_id = create_user(app, role="PARENT", email="pp3@test.local")
    child_id = _add_child(app, parent_id, class_name="CM9")
    login(client, parent_id)
    resp = client.get(f"/parent/children/{child_id}/channels")
    assert resp.status_code == 200
    assert b"Aucun canal" in resp.data

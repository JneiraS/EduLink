from app.extensions import db
from app.infrastructure.database.models import ChannelModel, UserModel, channel_members

from tests.helpers import login


def test_parent_cannot_see_add_members_panel(app):
    with app.app_context():
        parent = UserModel(
            full_name="Parent User",
            email="parent@test.local",
            role="PARENT",
            password_hash="x",
            is_active=True,
        )
        admin = UserModel(
            full_name="Admin User",
            email="admin2@test.local",
            role="ADMIN",
            password_hash="x",
            is_active=True,
        )
        channel = ChannelModel(name="Canal test", created_by=1)

        db.session.add(parent)
        db.session.add(admin)
        db.session.add(channel)
        db.session.flush()

        db.session.execute(
            channel_members.insert().values(channel_id=channel.id, user_id=parent.id)
        )
        db.session.commit()

        parent_id = parent.id
        admin_id = admin.id
        channel_id = channel.id

    client = app.test_client()
    login(client, parent_id)

    response = client.get(f"/messages/channels/{channel_id}")
    assert response.status_code == 200
    assert b"Ajouter des membres" not in response.data

    post_response = client.post(
        f"/messages/channels/{channel_id}",
        data={"action": "add_members", "members": [str(admin_id)]},
        follow_redirects=True,
    )
    assert post_response.status_code == 200
    assert b"peuvent ajouter des membres" in post_response.data

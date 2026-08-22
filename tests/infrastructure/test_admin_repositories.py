from app import create_app
from app.domain.entities.announcement import Announcement
from app.domain.entities.channel import Channel
from app.extensions import db
from app.infrastructure.database.models import (
    AnnouncementModel,
    ChannelModel,
    MessageModel,
    NotificationModel,
    UserModel,
    channel_members,
)
from app.infrastructure.repositories.announcement_repository import (
    SQLAlchemyAnnouncementRepository,
)
from app.infrastructure.repositories.channel_repository import (
    SQLAlchemyChannelRepository,
)
from tests.helpers import (
    add_announcement,
    add_message,
    add_notification,
    create_channel,
    create_user,
)


def test_announcement_repository_find_by_id_and_delete():
    app = create_app(testing=True)

    with app.app_context():
        author_id = create_user(app, role="TEACHER", email="a@repo.local")
        announcement_id = add_announcement(
            app, title="Titre", content="Contenu", created_by=author_id,
            pdf_filename="x.pdf",
        )

        repo = SQLAlchemyAnnouncementRepository()
        found = repo.find_by_id(announcement_id)
        assert found is not None
        assert found.title == "Titre"
        assert found.pdf_filename == "x.pdf"

        deleted = repo.delete(announcement_id)
        assert deleted is not None
        assert repo.find_by_id(announcement_id) is None


def test_announcement_repository_delete_unknown_returns_none():
    app = create_app(testing=True)
    with app.app_context():
        repo = SQLAlchemyAnnouncementRepository()
        assert repo.delete(999) is None
        assert repo.find_by_id(999) is None


def test_announcement_repository_list_recent_orders_desc_with_limit():
    from datetime import datetime, timedelta, timezone

    app = create_app(testing=True)

    with app.app_context():
        author_id = create_user(app, role="TEACHER", email="rec@repo.local")
        now = datetime.now(timezone.utc)
        ids = []
        for days in range(5):
            model = AnnouncementModel(
                title=f"Annonce {days}",
                content="Contenu",
                created_by=author_id,
                created_at=now - timedelta(days=days),
            )
            db.session.add(model)
            db.session.flush()
            ids.append(model.id)
        db.session.commit()

        repo = SQLAlchemyAnnouncementRepository()
        recent = repo.list_recent(limit=3)
        assert [a.title for a in recent] == [
            "Annonce 0",
            "Annonce 1",
            "Annonce 2",
        ]
        assert len(recent) == 3


def test_channel_repository_list_all_orders_by_creation():
    app = create_app(testing=True)

    with app.app_context():
        owner_id = create_user(app, role="TEACHER", email="o@repo.local")
        create_channel(app, name="Alpha", created_by=owner_id, member_ids=[owner_id])
        create_channel(app, name="Bravo", created_by=owner_id, member_ids=[owner_id])

        repo = SQLAlchemyChannelRepository()
        channels = repo.list_all()
        assert len(channels) == 2
        assert {c.name for c in channels} == {"Alpha", "Bravo"}


def test_channel_repository_delete_cascades_members_messages_notifications():
    app = create_app(testing=True)

    with app.app_context():
        admin_id = create_user(app, role="ADMIN", email="ad@repo.local")
        member_id = create_user(app, role="PARENT", email="m@repo.local")
        other_id = create_user(app, role="PARENT", email="o2@repo.local")
        channel_id = create_channel(
            app, name="Canal", created_by=admin_id, member_ids=[admin_id, member_id]
        )
        add_message(app, channel_id=channel_id, sender_id=admin_id, content="Bonjour")
        add_notification(app, user_id=member_id, content="Notif", channel_id=channel_id)
        add_notification(app, user_id=other_id, content="Sans canal")

        repo = SQLAlchemyChannelRepository()
        deleted = repo.delete(channel_id)
        assert deleted is not None
        assert deleted.name == "Canal"

        assert db.session.get(ChannelModel, channel_id) is None
        assert MessageModel.query.filter_by(channel_id=channel_id).count() == 0
        assert NotificationModel.query.filter_by(channel_id=channel_id).count() == 0
        rows = db.session.execute(
            channel_members.select().where(
                channel_members.c.channel_id == channel_id
            )
        ).all()
        assert rows == []

        # Unrelated notification and users survive.
        assert NotificationModel.query.filter_by(user_id=other_id).count() == 1
        assert db.session.get(UserModel, member_id) is not None


def test_channel_repository_delete_unknown_returns_none():
    app = create_app(testing=True)
    with app.app_context():
        repo = SQLAlchemyChannelRepository()
        assert repo.delete(999) is None
        assert repo.find_by_id(999) is None
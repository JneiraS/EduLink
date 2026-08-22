from app import create_app
from app.domain.entities.announcement import Announcement
from app.domain.entities.channel import Channel
from app.domain.entities.message import Message
from app.domain.entities.notification import Notification
from app.extensions import db
from app.infrastructure.database.models import (
    AnnouncementModel,
    AnnouncementReadModel,
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
from app.infrastructure.repositories.message_repository import (
    SQLAlchemyMessageRepository,
)
from app.infrastructure.repositories.notification_repository import (
    SQLAlchemyNotificationRepository,
)


def _seed_channel(name="Canal") -> int:
    model = ChannelModel(name=name, created_by=1)
    db.session.add(model)
    db.session.flush()
    return model.id


def _seed_message(channel_id, content, sender_id=1) -> int:
    model = MessageModel(
        channel_id=channel_id, sender_id=sender_id, content=content
    )
    db.session.add(model)
    db.session.commit()
    return model.id


def _seed_user(email, role="PARENT"):
    user = UserModel(
        full_name="User",
        email=email,
        role=role,
        password_hash="x",
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()
    return user.id


class TestListLatestByChannels:
    def test_returns_latest_message_per_channel(self):
        app = create_app(testing=True)
        with app.app_context():
            c1 = _seed_channel("A")
            c2 = _seed_channel("B")
            _seed_message(c1, "vieux")
            _seed_message(c1, "recent")
            _seed_message(c2, "seul")

            result = SQLAlchemyMessageRepository().list_latest_by_channels(
                [c1, c2]
            )

            assert result[c1].content == "recent"
            assert result[c2].content == "seul"
            assert len(result) == 2

    def test_ignores_channels_without_messages(self):
        app = create_app(testing=True)
        with app.app_context():
            c1 = _seed_channel("A")
            c2 = _seed_channel("B")
            _seed_message(c1, "hello")

            result = SQLAlchemyMessageRepository().list_latest_by_channels(
                [c1, c2]
            )

            assert c1 in result
            assert c2 not in result

    def test_empty_channel_list(self):
        app = create_app(testing=True)
        with app.app_context():
            assert (
                SQLAlchemyMessageRepository().list_latest_by_channels([]) == {}
            )


class TestCountUnreadNotifications:
    def test_counts_only_unread(self):
        app = create_app(testing=True)
        with app.app_context():
            user_id = _seed_user("n1@test.local")
            db.session.add_all(
                [
                    NotificationModel(
                        user_id=user_id, content="a", is_read=False
                    ),
                    NotificationModel(
                        user_id=user_id, content="b", is_read=False
                    ),
                    NotificationModel(
                        user_id=user_id, content="c", is_read=True
                    ),
                ]
            )
            db.session.commit()

            assert SQLAlchemyNotificationRepository().count_unread(user_id) == 2

    def test_zero_when_no_notifications(self):
        app = create_app(testing=True)
        with app.app_context():
            assert SQLAlchemyNotificationRepository().count_unread(999) == 0


class TestCountUnreadForUser:
    def test_counts_announcements_user_has_not_read(self):
        app = create_app(testing=True)
        with app.app_context():
            user_id = _seed_user("a1@test.local")
            a1 = AnnouncementModel(
                title="t1", content="c", created_by=1, pdf_filename=None
            )
            a2 = AnnouncementModel(
                title="t2", content="c", created_by=1, pdf_filename=None
            )
            db.session.add_all([a1, a2])
            db.session.flush()
            db.session.add(
                AnnouncementReadModel(
                    announcement_id=a1.id, user_id=user_id
                )
            )
            db.session.commit()

            assert (
                SQLAlchemyAnnouncementRepository().count_unread_for_user(
                    user_id
                )
                == 1
            )

    def test_zero_when_none(self):
        app = create_app(testing=True)
        with app.app_context():
            assert SQLAlchemyAnnouncementRepository().count_unread_for_user(999) == 0


class TestMarkChannelRead:
    def test_marks_only_matching_channel_and_user(self):
        app = create_app(testing=True)
        with app.app_context():
            user_id = _seed_user("m1@test.local")
            other_id = _seed_user("m2@test.local")
            c1 = _seed_channel("A")
            c2 = _seed_channel("B")
            db.session.add_all(
                [
                    NotificationModel(
                        user_id=user_id, content="a", is_read=False,
                        channel_id=c1,
                    ),
                    NotificationModel(
                        user_id=user_id, content="b", is_read=False,
                        channel_id=c1,
                    ),
                    NotificationModel(
                        user_id=user_id, content="c", is_read=False,
                        channel_id=c2,
                    ),
                    NotificationModel(
                        user_id=other_id, content="d", is_read=False,
                        channel_id=c1,
                    ),
                    NotificationModel(
                        user_id=user_id, content="e", is_read=True,
                        channel_id=c1,
                    ),
                ]
            )
            db.session.commit()

            SQLAlchemyNotificationRepository().mark_channel_read(c1, user_id)

            rows = db.session.query(NotificationModel).all()
            state = {(n.user_id, n.channel_id, n.content): n.is_read for n in rows}
            assert state[(user_id, c1, "a")] is True
            assert state[(user_id, c1, "b")] is True
            assert state[(user_id, c2, "c")] is False
            assert state[(other_id, c1, "d")] is False
            assert state[(user_id, c1, "e")] is True
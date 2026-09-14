from werkzeug.security import generate_password_hash

from app.extensions import db
from app.infrastructure.database.models import (
    AnnouncementModel,
    ChannelModel,
    MessageModel,
    NotificationModel,
    UserModel,
    channel_members,
)


def login(client, user_id: int) -> None:
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True


def create_user(app, role="PARENT", email=None, full_name=None, active=True, password="secret"):
    with app.app_context():
        user = UserModel(
            full_name=full_name or f"User {role}",
            email=email or f"{role.lower()}.{id(user)}@test.local",
            role=role,
            password_hash=generate_password_hash(password),
            is_active=active,
        )
        db.session.add(user)
        db.session.commit()
        return user.id


def create_channel(app, name, created_by, member_ids=None):
    with app.app_context():
        channel = ChannelModel(name=name, created_by=created_by)
        db.session.add(channel)
        db.session.flush()
        for uid in dict.fromkeys([created_by, *(member_ids or [])]):
            db.session.execute(
                channel_members.insert().values(channel_id=channel.id, user_id=uid)
            )
        db.session.commit()
        return channel.id


def add_message(app, channel_id, sender_id, content):
    with app.app_context():
        message = MessageModel(
            channel_id=channel_id, sender_id=sender_id, content=content
        )
        db.session.add(message)
        db.session.commit()
        return message.id


def add_announcement(app, title, content, created_by, pdf_filename=None):
    with app.app_context():
        announcement = AnnouncementModel(
            title=title,
            content=content,
            created_by=created_by,
            pdf_filename=pdf_filename,
        )
        db.session.add(announcement)
        db.session.commit()
        return announcement.id


def add_notification(app, user_id, content, channel_id=None, is_read=False):
    with app.app_context():
        notification = NotificationModel(
            user_id=user_id,
            content=content,
            is_read=is_read,
            channel_id=channel_id,
        )
        db.session.add(notification)
        db.session.commit()
        return notification.id


def add_calendar_event(
    app,
    title,
    type_value="event",
    category="academic",
    class_name="Tous les niveaux",
    description=None,
    location=None,
    priority="normal",
    start_date=None,
    end_date=None,
):
    from datetime import datetime

    from app.infrastructure.database.models import CalendarEventModel

    with app.app_context():
        event = CalendarEventModel(
            title=title,
            type=type_value,
            category=category,
            class_name=class_name,
            description=description,
            location=location,
            priority=priority,
            start_date=start_date or datetime(2026, 9, 20, 18, 0),
            end_date=end_date,
        )
        db.session.add(event)
        db.session.commit()
        return event.id
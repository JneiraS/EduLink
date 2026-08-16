from datetime import datetime, timezone

from flask_login import UserMixin

from app.extensions import db

USERS_ID_FK = "users.id"


def utc_now() -> datetime:
    utc_zone = getattr(datetime, "UTC", timezone.utc)
    return datetime.now(utc_zone)


channel_members = db.Table(
    "channel_members",
    db.Column("channel_id", db.Integer, db.ForeignKey("channels.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey(USERS_ID_FK), primary_key=True),
)

announcement_channels = db.Table(
    "announcement_channels",
    db.Column(
        "announcement_id",
        db.Integer,
        db.ForeignKey("announcements.id"),
        primary_key=True,
    ),
    db.Column(
        "channel_id", db.Integer, db.ForeignKey("channels.id"), primary_key=True
    ),
)


class UserModel(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    role = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    channels = db.relationship(
        "ChannelModel", secondary=channel_members, back_populates="members"
    )


class InvitationModel(db.Model):
    __tablename__ = "invitations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(USERS_ID_FK), nullable=False, index=True)
    token = db.Column(db.String(128), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)


class AnnouncementModel(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey(USERS_ID_FK), nullable=False)
    pdf_filename = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)


class AnnouncementReadModel(db.Model):
    __tablename__ = "announcement_reads"

    announcement_id = db.Column(
        db.Integer, db.ForeignKey("announcements.id"), primary_key=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey(USERS_ID_FK), primary_key=True)
    read_at = db.Column(db.DateTime, default=utc_now, nullable=False)


class ChannelModel(db.Model):
    __tablename__ = "channels"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    kind = db.Column(db.String(10), nullable=False, default="group")
    created_by = db.Column(db.Integer, db.ForeignKey(USERS_ID_FK), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    members = db.relationship(
        "UserModel", secondary=channel_members, back_populates="channels"
    )


class MessageModel(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(
        db.Integer, db.ForeignKey("channels.id"), nullable=False, index=True
    )
    sender_id = db.Column(db.Integer, db.ForeignKey(USERS_ID_FK), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)


class NotificationModel(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey(USERS_ID_FK), nullable=False, index=True
    )
    content = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    channel_id = db.Column(
        db.Integer, db.ForeignKey("channels.id"), nullable=True, index=True
    )
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)


class PushSubscriptionModel(db.Model):
    __tablename__ = "push_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey(USERS_ID_FK), nullable=False, index=True
    )
    endpoint = db.Column(db.String(1024), nullable=False, unique=True)
    p256dh_key = db.Column(db.String(255), nullable=False)
    auth_key = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)


class MessageTemplateModel(db.Model):
    __tablename__ = "message_templates"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey(USERS_ID_FK), nullable=False)
    label = db.Column(db.String(80), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

from datetime import datetime

from flask_login import UserMixin

from app.extensions import db

USERS_ID_FK = "users.id"

channel_members = db.Table(
    "channel_members",
    db.Column("channel_id", db.Integer, db.ForeignKey("channels.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey(USERS_ID_FK), primary_key=True),
)


class UserModel(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    role = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    channels = db.relationship(
        "ChannelModel", secondary=channel_members, back_populates="members"
    )


class AnnouncementModel(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey(USERS_ID_FK), nullable=False)
    pdf_filename = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ChannelModel(db.Model):
    __tablename__ = "channels"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey(USERS_ID_FK), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class NotificationModel(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey(USERS_ID_FK), nullable=False, index=True
    )
    content = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

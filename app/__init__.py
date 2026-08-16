import os
import secrets

from flask import Flask
from flask import flash, redirect, url_for
from dotenv import load_dotenv

# Load .env as early as possible so config module sees environment variables.
load_dotenv()

from app.application.container import UseCaseContainer
from app.application.use_cases.announcement_use_cases import (
    CreateAnnouncement,
    ListAnnouncements,
)
from app.application.use_cases.auth_use_cases import LoginUser, RegisterUser
from app.application.use_cases.channel_use_cases import AddChannelMembers, CreateChannel
from app.application.use_cases.dashboard_use_case import GetDashboard
from app.application.use_cases.message_use_cases import (
    ListChannelMessages,
    ListChannelMembers,
    ListUserChannels,
    SendMessage,
)
from app.application.use_cases.notification_use_cases import (
    ListNotifications,
    MarkNotificationRead,
    SubscribePushNotifications,
    UnsubscribePushNotifications,
)
from app.config.settings import DevelopmentConfig, TestingConfig
from app.domain.errors import DomainError
from app.extensions import csrf, db, login_manager, socketio
from app.infrastructure.auth.password_hasher import WerkzeugPasswordHasher
from app.infrastructure.database.models import UserModel
from app.infrastructure.notifications.socketio_service import (
    SocketIONotificationService,
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
from app.infrastructure.repositories.push_subscription_repository import (
    SQLAlchemyPushSubscriptionRepository,
)
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from app.interfaces.web.routes.announcements_routes import announcements_bp
from app.interfaces.web.routes.auth_routes import auth_bp
from app.interfaces.web.routes.dashboard_routes import dashboard_bp
from app.interfaces.web.routes.messages_routes import messages_bp
from app.interfaces.web.routes.notifications_routes import notifications_bp
from app.interfaces.web.routes.push_routes import push_bp
from app.interfaces.web.socket_events import register_socket_handlers


def create_app(testing: bool = False):
    app = Flask(
        __name__,
        template_folder="interfaces/web/templates",
        static_folder="interfaces/web/static",
    )
    app.config.from_object(TestingConfig if testing else DevelopmentConfig)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(announcements_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(push_bp)

    with app.app_context():
        db.create_all()
        _seed_initial_admin()

    users_repo = SQLAlchemyUserRepository()
    announcements_repo = SQLAlchemyAnnouncementRepository()
    messages_repo = SQLAlchemyMessageRepository()
    channels_repo = SQLAlchemyChannelRepository()
    notifications_repo = SQLAlchemyNotificationRepository()
    push_subscriptions_repo = SQLAlchemyPushSubscriptionRepository()
    hasher = WerkzeugPasswordHasher()
    realtime = SocketIONotificationService(
        socketio=socketio,
        push_subscriptions=push_subscriptions_repo,
        vapid_private_key=app.config.get("VAPID_PRIVATE_KEY", ""),
        vapid_public_key=app.config.get("VAPID_PUBLIC_KEY", ""),
        vapid_subject=app.config.get("VAPID_SUBJECT", "mailto:admin@edulink.local"),
    )

    app.extensions["services"] = {
        "users": users_repo,
        "announcements": announcements_repo,
        "messages": messages_repo,
        "channels": channels_repo,
        "notifications": notifications_repo,
        "push_subscriptions": push_subscriptions_repo,
        "hasher": hasher,
        "realtime_notifications": realtime,
    }

    app.extensions["use_cases"] = UseCaseContainer(
        register_user=RegisterUser(users=users_repo, hasher=hasher),
        login_user=LoginUser(users=users_repo, hasher=hasher),
        create_announcement=CreateAnnouncement(
            announcements=announcements_repo,
            notifications=notifications_repo,
            users=users_repo,
            realtime=realtime,
        ),
        list_announcements=ListAnnouncements(announcements=announcements_repo),
        get_dashboard=GetDashboard(
            announcements=announcements_repo, notifications=notifications_repo
        ),
        send_message=SendMessage(
            messages=messages_repo,
            channels=channels_repo,
            notifications=notifications_repo,
            realtime=realtime,
        ),
        list_channel_messages=ListChannelMessages(
            messages=messages_repo, channels=channels_repo
        ),
        list_channel_members=ListChannelMembers(
            channels=channels_repo, users=users_repo
        ),
        list_user_channels=ListUserChannels(channels=channels_repo),
        list_notifications=ListNotifications(notifications=notifications_repo),
        mark_notification_read=MarkNotificationRead(notifications=notifications_repo),
        subscribe_push_notifications=SubscribePushNotifications(
            push_subscriptions=push_subscriptions_repo
        ),
        unsubscribe_push_notifications=UnsubscribePushNotifications(
            push_subscriptions=push_subscriptions_repo
        ),
        create_channel=CreateChannel(channels=channels_repo),
        add_channel_members=AddChannelMembers(
            channels=channels_repo,
            users=users_repo,
        ),
    )

    register_socket_handlers(socketio)

    @app.errorhandler(DomainError)
    def handle_domain_error(exc):
        flash(str(exc), "danger")
        return redirect(url_for("dashboard.home"))

    return app


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(UserModel, int(user_id))


def _seed_initial_admin() -> None:
    admin_email = os.getenv("EDULINK_ADMIN_EMAIL", "admin@edulink.local")
    admin_password = os.getenv("EDULINK_ADMIN_PASSWORD")

    existing = UserModel.query.filter_by(email=admin_email).first()
    if existing:
        return

    if not admin_password:
        admin_password = secrets.token_urlsafe(12)
        print(f"[EduLink] Generated admin password for {admin_email}: {admin_password}")

    hasher = WerkzeugPasswordHasher()
    admin = UserModel(
        full_name="System Admin",
        email=admin_email,
        role="ADMIN",
        password_hash=hasher.hash_password(admin_password),
        is_active=True,
    )
    db.session.add(admin)
    db.session.commit()

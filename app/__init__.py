import logging
import os
import secrets
from pathlib import Path

from flask import Flask
from flask import flash, redirect, url_for
from dotenv import load_dotenv
from alembic import command
from alembic.config import Config

# Load .env as early as possible so config module sees environment variables.
load_dotenv()

logger = logging.getLogger(__name__)

from app.application.container import UseCaseContainer
from app.application.use_cases.admin_use_cases import (
    DeleteAnnouncement,
    DeleteChannel,
    ListAnnouncementsForAdmin,
    ListChannelsForAdmin,
    ListUsersForAdmin,
    ToggleUserActive,
    UpdateUserRole,
)
from app.application.use_cases.announcement_use_cases import (
    ConfirmAnnouncementRead,
    CreateAnnouncement,
    GetAnnouncementReadStatus,
    ListAnnouncements,
)
from app.application.use_cases.auth_use_cases import (
    AcceptInvitation,
    CreateInvitation,
    CreateUserWithInvitation,
    LoginUser,
    RegisterUser,
    ValidateInvitation,
)
from app.application.use_cases.channel_use_cases import (
    AddChannelMembers,
    CreateChannel,
    OpenDirectConversation,
)
from app.application.use_cases.dashboard_use_case import GetDashboard
from app.application.use_cases.message_use_cases import (
    ListChannelMembers,
    ListChannelMessages,
    ListPinnedMessages,
    ListUserChannels,
    PinMessage,
    SearchChannelMessages,
    SendMessage,
)
from app.application.use_cases.message_template_use_cases import (
    CreateMessageTemplate,
    DeleteMessageTemplate,
    ListMessageTemplates,
    UpdateMessageTemplate,
)
from app.application.use_cases.notification_use_cases import (
    GetNotificationSettings,
    ListNotifications,
    MarkNotificationRead,
    SetGlobalNotifications,
    SubscribePushNotifications,
    ToggleChannelNotifications,
    UnsubscribePushNotifications,
)
from app.application.use_cases.user_query_use_cases import FindUsersByIds, ListAllUsers
from app.application.use_cases.children_use_cases import (
    CreateChild,
    DeleteChild,
    LinkChildToClassChannels,
    ListChildren,
    ListClassNames,
)
from app.config.settings import DevelopmentConfig, TestingConfig
from app.domain.errors import DomainError
from app.extensions import csrf, db, limiter, login_manager, socketio
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
from app.infrastructure.repositories.invitation_repository import (
    SQLAlchemyInvitationRepository,
)
from app.infrastructure.repositories.message_repository import (
    SQLAlchemyMessageRepository,
)
from app.infrastructure.repositories.message_template_repository import (
    SQLAlchemyMessageTemplateRepository,
)
from app.infrastructure.repositories.notification_repository import (
    SQLAlchemyNotificationRepository,
)
from app.infrastructure.repositories.notification_preferences_repository import (
    SQLAlchemyNotificationPreferencesRepository,
)
from app.infrastructure.repositories.push_subscription_repository import (
    SQLAlchemyPushSubscriptionRepository,
)
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from app.infrastructure.repositories.children_repository import SQLAlchemyChildrenRepository
from app.interfaces.web.routes.announcements_routes import announcements_bp
from app.interfaces.web.routes.admin_routes import admin_bp
from app.interfaces.web.routes.auth_routes import auth_bp
from app.interfaces.web.routes.dashboard_routes import dashboard_bp
from app.interfaces.web.routes.messages_routes import messages_bp
from app.interfaces.web.routes.notifications_routes import notifications_bp
from app.interfaces.web.routes.push_routes import push_bp
from app.interfaces.web.routes.parent_routes import parent_bp
from app.interfaces.web.socket_events import register_socket_handlers


def create_app(testing: bool = False):
    app = Flask(
        __name__,
        template_folder="interfaces/web/templates",
        static_folder="interfaces/web/static",
    )
    app.config.from_object(TestingConfig if testing else DevelopmentConfig)

    _resolve_secret_key(app)

    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = app.config.get(
        "SESSION_COOKIE_SECURE", False
    )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)
    limiter.init_app(app)
    limiter.enabled = app.config.get("RATE_LIMIT_ENABLED", False)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(announcements_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(push_bp)
    app.register_blueprint(parent_bp)

    with app.app_context():
        if app.config["TESTING"]:
            # In-memory SQLite: create_all on the app's own connection (Alembic
            # would open a separate connection to :memory:, yielding a fresh DB).
            db.create_all()
        else:
            # Dev/prod: schema is managed by Alembic migrations.
            _run_migrations()
        _seed_initial_admin()

    users_repo = SQLAlchemyUserRepository()
    announcements_repo = SQLAlchemyAnnouncementRepository()
    messages_repo = SQLAlchemyMessageRepository()
    channels_repo = SQLAlchemyChannelRepository()
    notifications_repo = SQLAlchemyNotificationRepository()
    notification_prefs_repo = SQLAlchemyNotificationPreferencesRepository()
    push_subscriptions_repo = SQLAlchemyPushSubscriptionRepository()
    message_templates_repo = SQLAlchemyMessageTemplateRepository()
    children_repo = SQLAlchemyChildrenRepository()
    invitations_repo = SQLAlchemyInvitationRepository()
    hasher = WerkzeugPasswordHasher()
    realtime = SocketIONotificationService(
        socketio=socketio,
        push_subscriptions=push_subscriptions_repo,
        app=app,
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
        "notification_preferences": notification_prefs_repo,
        "push_subscriptions": push_subscriptions_repo,
        "message_templates": message_templates_repo,
        "children": children_repo,
        "invitations": invitations_repo,
        "hasher": hasher,
        "realtime_notifications": realtime,
    }

    app.extensions["use_cases"] = UseCaseContainer(
        register_user=RegisterUser(users=users_repo, hasher=hasher),
        login_user=LoginUser(users=users_repo, hasher=hasher),
        create_user_with_invitation=CreateUserWithInvitation(
            users=users_repo,
            invitations=invitations_repo,
            ttl_hours=app.config.get("INVITATION_TTL_HOURS", 72),
        ),
        validate_invitation=ValidateInvitation(
            users=users_repo, invitations=invitations_repo
        ),
        accept_invitation=AcceptInvitation(
            users=users_repo, invitations=invitations_repo, hasher=hasher
        ),
        create_invitation=CreateInvitation(
            users=users_repo,
            invitations=invitations_repo,
            ttl_hours=app.config.get("INVITATION_TTL_HOURS", 72),
        ),
        create_announcement=CreateAnnouncement(
            announcements=announcements_repo,
            notifications=notifications_repo,
            users=users_repo,
            channels=channels_repo,
            realtime=realtime,
        ),
        list_announcements=ListAnnouncements(announcements=announcements_repo),
        confirm_announcement_read=ConfirmAnnouncementRead(
            announcements=announcements_repo
        ),
        get_announcement_read_status=GetAnnouncementReadStatus(
            announcements=announcements_repo,
            channels=channels_repo,
            users=users_repo,
        ),
        get_dashboard=GetDashboard(
            announcements=announcements_repo, notifications=notifications_repo
        ),
        send_message=SendMessage(
            messages=messages_repo,
            channels=channels_repo,
            notifications=notifications_repo,
            realtime=realtime,
            preferences=notification_prefs_repo,
        ),
        search_channel_messages=SearchChannelMessages(
            messages=messages_repo, channels=channels_repo
        ),
        list_pinned_messages=ListPinnedMessages(
            messages=messages_repo, channels=channels_repo
        ),
        pin_message=PinMessage(messages=messages_repo, channels=channels_repo),
        list_channel_messages=ListChannelMessages(
            messages=messages_repo, channels=channels_repo
        ),
        list_channel_members=ListChannelMembers(
            channels=channels_repo, users=users_repo
        ),
        list_user_channels=ListUserChannels(channels=channels_repo),
        list_notifications=ListNotifications(notifications=notifications_repo),
        mark_notification_read=MarkNotificationRead(notifications=notifications_repo),
        get_notification_settings=GetNotificationSettings(
            preferences=notification_prefs_repo, channels=channels_repo
        ),
        set_global_notifications=SetGlobalNotifications(
            preferences=notification_prefs_repo
        ),
        toggle_channel_notifications=ToggleChannelNotifications(
            preferences=notification_prefs_repo, channels=channels_repo
        ),
        subscribe_push_notifications=SubscribePushNotifications(
            push_subscriptions=push_subscriptions_repo
        ),
        unsubscribe_push_notifications=UnsubscribePushNotifications(
            push_subscriptions=push_subscriptions_repo
        ),
        list_message_templates=ListMessageTemplates(
            templates=message_templates_repo
        ),
        create_message_template=CreateMessageTemplate(
            templates=message_templates_repo
        ),
        delete_message_template=DeleteMessageTemplate(
            templates=message_templates_repo
        ),
        update_message_template=UpdateMessageTemplate(
            templates=message_templates_repo
        ),
        create_channel=CreateChannel(channels=channels_repo),
        add_channel_members=AddChannelMembers(
            channels=channels_repo,
            users=users_repo,
        ),
        open_direct_conversation=OpenDirectConversation(
            channels=channels_repo,
            users=users_repo,
        ),
        list_all_users=ListAllUsers(users=users_repo),
        find_users_by_ids=FindUsersByIds(users=users_repo),
        list_users_for_admin=ListUsersForAdmin(users=users_repo),
        list_announcements_for_admin=ListAnnouncementsForAdmin(
            announcements=announcements_repo
        ),
        list_channels_for_admin=ListChannelsForAdmin(channels=channels_repo),
        update_user_role=UpdateUserRole(users=users_repo),
        toggle_user_active=ToggleUserActive(users=users_repo),
        delete_announcement=DeleteAnnouncement(announcements=announcements_repo),
        delete_channel=DeleteChannel(channels=channels_repo),
        create_child=CreateChild(
            children=children_repo, users=users_repo, channels=channels_repo
        ),
        list_children=ListChildren(children=children_repo),
        list_class_names=ListClassNames(children=children_repo),
        delete_child=DeleteChild(children=children_repo),
        link_child_to_class_channels=LinkChildToClassChannels(
            children=children_repo, channels=channels_repo
        ),
    )

    register_socket_handlers(socketio)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' https://cdn.socket.io https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'",
        )
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response

    @app.errorhandler(DomainError)
    def handle_domain_error(exc):
        flash(str(exc), "danger")
        return redirect(url_for("dashboard.home"))

    return app


def _resolve_secret_key(app) -> None:
    """Resolve a strong SECRET_KEY, persisting a generated one for dev."""
    configured = os.getenv("SECRET_KEY")
    if configured and configured != "dev-secret-change-me":
        app.config["SECRET_KEY"] = configured
        return

    if app.config.get("TESTING"):
        return  # TestingConfig provides its own fixed test secret.

    secret_file = Path(app.instance_path) / "secret_key"
    if secret_file.exists():
        existing = secret_file.read_text().strip()
        if existing and existing != "dev-secret-change-me":
            app.config["SECRET_KEY"] = existing
            return

    generated = secrets.token_hex(32)
    secret_file.parent.mkdir(parents=True, exist_ok=True)
    secret_file.write_text(generated)
    try:
        os.chmod(secret_file, 0o600)
    except OSError:  # pragma: no cover - Windows/permissions edge case.
        pass
    app.config["SECRET_KEY"] = generated


def _run_migrations() -> None:
    alembic_ini = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    )
    command.upgrade(Config(alembic_ini), "head")


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
        if os.getenv("EDULINK_DEBUG") == "1":
            print(f"[EduLink] Generated admin password for {admin_email}: {admin_password}")
        else:
            logger.warning(
                "EDULINK_ADMIN_PASSWORD not set: generated a random admin password "
                "for %s (shown only in console in debug mode).", admin_email
            )

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

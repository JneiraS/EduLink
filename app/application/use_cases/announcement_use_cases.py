from dataclasses import dataclass

from app.domain.entities.announcement import Announcement
from app.domain.entities.notification import Notification
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, ValidationError
from app.domain.ports.repositories import (
    AnnouncementRepositoryPort,
    NotificationRepositoryPort,
    UserRepositoryPort,
)
from app.domain.ports.services import RealtimeNotificationPort

MAX_TITLE_LENGTH = 255
MAX_CONTENT_LENGTH = 5000


@dataclass(slots=True)
class CreateAnnouncement:
    announcements: AnnouncementRepositoryPort
    notifications: NotificationRepositoryPort
    users: UserRepositoryPort
    realtime: RealtimeNotificationPort

    def execute(
        self, actor: User, title: str, content: str, pdf_filename: str | None = None
    ) -> Announcement:
        if actor.role not in {UserRole.ADMIN, UserRole.TEACHER}:
            raise AuthorizationError("Only admin and teachers can create announcements")
        if not title.strip() or not content.strip():
            raise ValidationError("Title and content are required")
        title = title.strip()
        content = content.strip()
        if len(title) > MAX_TITLE_LENGTH:
            raise ValidationError(f"Title must be at most {MAX_TITLE_LENGTH} characters")
        if len(content) > MAX_CONTENT_LENGTH:
            raise ValidationError(
                f"Content must be at most {MAX_CONTENT_LENGTH} characters"
            )

        announcement = Announcement(
            id=None,
            title=title,
            content=content,
            created_by=actor.id or 0,
            pdf_filename=pdf_filename,
        )
        saved = self.announcements.save(announcement)

        for user in self.users.list_users():
            notification = Notification(
                id=None,
                user_id=user.id or 0,
                content=f"Nouvelle annonce: {saved.title}",
                is_read=False,
                channel_id=None,
            )
            created_notif = self.notifications.save(notification)
            self.realtime.notify_user(
                user.id or 0,
                {
                    "id": created_notif.id,
                    "content": created_notif.content,
                    "created_at": str(created_notif.created_at),
                },
            )

        return saved


@dataclass(slots=True)
class ListAnnouncements:
    announcements: AnnouncementRepositoryPort

    def execute(self, page: int = 1, per_page: int = 10):
        return self.announcements.paginate(page, per_page)

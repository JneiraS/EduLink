from dataclasses import dataclass

from app.domain.entities.announcement import Announcement
from app.domain.entities.notification import Notification
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, NotFoundError, ValidationError
from app.domain.ports.repositories import (
    AnnouncementRepositoryPort,
    ChannelRepositoryPort,
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
    channels: ChannelRepositoryPort
    realtime: RealtimeNotificationPort

    def execute(
        self,
        actor: User,
        title: str,
        content: str,
        pdf_filename: str | None = None,
        target_channel_ids: list[int] | None = None,
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

        target_channel_ids = sorted(set(int(cid) for cid in (target_channel_ids or [])))

        if target_channel_ids:
            for channel_id in target_channel_ids:
                if not self.channels.find_by_id(channel_id):
                    raise NotFoundError(f"Channel {channel_id} not found")
                if actor.role != UserRole.ADMIN and not self.channels.is_member(
                    channel_id, actor.id or 0
                ):
                    raise AuthorizationError(
                        "Teachers can only target channels they belong to"
                    )
            audience: set[int] = set()
            for channel_id in target_channel_ids:
                audience.update(self.channels.list_member_ids(channel_id))
        else:
            audience = {user.id or 0 for user in self.users.list_users()}

        announcement = Announcement(
            id=None,
            title=title,
            content=content,
            created_by=actor.id or 0,
            pdf_filename=pdf_filename,
            target_channel_ids=target_channel_ids,
        )
        saved = self.announcements.save(announcement)

        for user_id in audience:
            notification = Notification(
                id=None,
                user_id=user_id,
                content=f"Nouvelle annonce: {saved.title}",
                is_read=False,
                channel_id=None,
            )
            created_notif = self.notifications.save(notification)
            self.realtime.notify_user(
                user_id,
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
    channels: ChannelRepositoryPort

    def execute(self, actor: User, page: int = 1, per_page: int = 10):
        channel_ids = [c.id or 0 for c in self.channels.list_for_user(actor.id or 0)]
        return self.announcements.paginate(page, per_page, channel_ids)


@dataclass(slots=True)
class ConfirmAnnouncementRead:
    announcements: AnnouncementRepositoryPort
    channels: ChannelRepositoryPort

    def execute(self, actor: User, announcement_id: int) -> Announcement:
        announcement = self.announcements.find_by_id(announcement_id)
        if announcement is None:
            raise NotFoundError("Announcement not found")
        if not self._can_view(actor, announcement):
            raise NotFoundError("Announcement not found")
        self.announcements.mark_read(announcement_id, actor.id or 0)
        return announcement

    def _can_view(self, actor: User, announcement: Announcement) -> bool:
        if not announcement.target_channel_ids:
            return True
        channel_ids = {
            channel.id or 0
            for channel in self.channels.list_for_user(actor.id or 0)
        }
        return any(
            target in channel_ids for target in announcement.target_channel_ids
        )


@dataclass(slots=True)
class GetAnnouncementPdf:
    announcements: AnnouncementRepositoryPort
    channels: ChannelRepositoryPort

    def execute(self, actor: User, pdf_filename: str) -> Announcement:
        announcement = self.announcements.find_by_pdf_filename(pdf_filename)
        if announcement is None:
            raise NotFoundError("Announcement not found")
        if announcement.target_channel_ids:
            channel_ids = {
                channel.id or 0
                for channel in self.channels.list_for_user(actor.id or 0)
            }
            if not any(
                target in channel_ids for target in announcement.target_channel_ids
            ):
                raise NotFoundError("Announcement not found")
        return announcement


@dataclass(slots=True)
class GetAnnouncementReadStatus:
    announcements: AnnouncementRepositoryPort
    channels: ChannelRepositoryPort
    users: UserRepositoryPort

    def execute(
        self, actor: User, announcements: list[Announcement]
    ) -> dict[int, tuple[int, int, bool]]:
        status: dict[int, tuple[int, int, bool]] = {}
        for announcement in announcements:
            read_count = self.announcements.count_read(announcement.id)
            if announcement.target_channel_ids:
                audience: set[int] = set()
                for channel_id in announcement.target_channel_ids:
                    audience.update(self.channels.list_member_ids(channel_id))
                audience_size = len(audience)
            else:
                audience_size = len(self.users.list_users())
            is_read = self.announcements.is_read(announcement.id, actor.id or 0)
            status[announcement.id] = (read_count, audience_size, is_read)
        return status

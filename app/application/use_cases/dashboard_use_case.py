from dataclasses import dataclass
from datetime import date

from app.domain.entities.user import User, UserRole
from app.domain.ports.repositories import (
    AnnouncementRepositoryPort,
    CalendarRepositoryPort,
    ChannelRepositoryPort,
    ChildrenRepositoryPort,
    MessageRepositoryPort,
    NotificationRepositoryPort,
    UserRepositoryPort,
)


@dataclass(slots=True)
class GetDashboard:
    announcements: AnnouncementRepositoryPort
    notifications: NotificationRepositoryPort
    channels: ChannelRepositoryPort
    messages: MessageRepositoryPort
    children: ChildrenRepositoryPort
    users: UserRepositoryPort
    events: CalendarRepositoryPort

    def execute(self, actor: User, today: date | None = None) -> dict:
        today = today or date.today()
        user_id = actor.id or 0
        role_message = {
            UserRole.ADMIN: "Espace administration",
            UserRole.TEACHER: "Espace enseignant",
            UserRole.PARENT: "Espace parent",
        }.get(actor.role, "Espace utilisateur")

        user_channels = self.channels.list_for_user(user_id)
        latest_messages = self.messages.list_latest_by_channels(
            [c.id for c in user_channels]
        )
        notifications = self.notifications.list_by_user(user_id)
        latest_announcements = self.announcements.list_all()[:5]
        announcement_read = {
            announcement.id: self.announcements.is_read(
                announcement.id, user_id
            )
            for announcement in latest_announcements
        }
        unread_announcements = self.announcements.count_unread_for_user(user_id)

        conversations = [
            {
                "channel": channel,
                "last_message": latest_messages.get(channel.id),
            }
            for channel in user_channels
        ]

        data = {
            "role_message": role_message,
            "stats": {
                "unread_notifications": self.notifications.count_unread(
                    user_id
                ),
                "conversations_count": len(user_channels),
                "unread_announcements": unread_announcements,
            },
            "conversations": conversations,
            "latest_announcements": [
                {
                    "announcement": announcement,
                    "is_read": announcement_read[announcement.id],
                }
                for announcement in latest_announcements
            ],
            "notifications": notifications[:5],
        }

        data["calendar"] = self._calendar_summary(today)

        if actor.role == UserRole.PARENT:
            data["children"] = self.children.list_by_parent(user_id)
        elif actor.role == UserRole.ADMIN:
            all_users = self.users.list_users()
            data["user_counts"] = {
                UserRole.ADMIN: sum(
                    1 for u in all_users if u.role == UserRole.ADMIN
                ),
                UserRole.TEACHER: sum(
                    1 for u in all_users if u.role == UserRole.TEACHER
                ),
                UserRole.PARENT: sum(
                    1 for u in all_users if u.role == UserRole.PARENT
                ),
            }
            data["channel_count"] = len(self.channels.list_all())
            data["announcement_count"] = len(self.announcements.list_all())
            data["recent_users"] = all_users[:5]

        return data

    def _calendar_summary(self, today: date) -> dict:
        all_events = self.events.list_events()
        upcoming = [e for e in all_events if e.start_date.date() >= today]

        next_deadline = next(
            (e for e in upcoming if e.type.value == "deadline"), None
        )
        days_to_deadline = None
        if next_deadline is not None:
            days_to_deadline = max(
                (next_deadline.start_date.date() - today).days, 0
            )

        return {
            "next_deadline": next_deadline,
            "days_to_deadline": days_to_deadline,
            "next_holiday": next(
                (e for e in upcoming if e.type.value == "holiday"), None
            ),
            "month_count": sum(
                1
                for e in all_events
                if e.start_date.month == today.month
                and e.start_date.year == today.year
            ),
        }
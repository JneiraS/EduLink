from dataclasses import dataclass

from app.domain.entities.user import User, UserRole
from app.domain.ports.repositories import (
    AnnouncementRepositoryPort,
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

    def execute(self, actor: User) -> dict:
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
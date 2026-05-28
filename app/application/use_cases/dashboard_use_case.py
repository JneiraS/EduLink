from dataclasses import dataclass

from app.domain.entities.user import User, UserRole
from app.domain.ports.repositories import (
    AnnouncementRepositoryPort,
    NotificationRepositoryPort,
)


@dataclass(slots=True)
class GetDashboard:
    announcements: AnnouncementRepositoryPort
    notifications: NotificationRepositoryPort

    def execute(self, actor: User) -> dict:
        role_message = {
            UserRole.ADMIN: "Espace administration",
            UserRole.TEACHER: "Espace enseignant",
            UserRole.PARENT: "Espace parent",
        }.get(actor.role, "Espace utilisateur")

        return {
            "role_message": role_message,
            "latest_announcements": self.announcements.list_all()[:5],
            "notifications": self.notifications.list_by_user(actor.id or 0)[:5],
        }

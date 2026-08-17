from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError
from app.domain.ports.repositories import (
    AnnouncementRepositoryPort,
    ChannelRepositoryPort,
    MessageRepositoryPort,
    PushSubscriptionRepositoryPort,
    UserRepositoryPort,
)

RECENT_ANNOUNCEMENTS = 5
TOP_CHANNELS = 5
MESSAGES_WINDOW_DAYS = 14
REGISTRATIONS_WINDOW_DAYS = 30


def _week_start(day) -> object:
    """Return the Monday of the week containing `day` (ISO week)."""
    return day - timedelta(days=day.weekday())


@dataclass(slots=True)
class GetAdminStats:
    users: UserRepositoryPort
    messages: MessageRepositoryPort
    announcements: AnnouncementRepositoryPort
    channels: ChannelRepositoryPort
    push_subscriptions: PushSubscriptionRepositoryPort

    def execute(self, actor: User) -> dict:
        if actor.role != UserRole.ADMIN:
            raise AuthorizationError("Acces reserve a l'administration")

        now = datetime.now(timezone.utc)
        registrations_since = now - timedelta(days=REGISTRATIONS_WINDOW_DAYS)
        messages_since = now - timedelta(days=MESSAGES_WINDOW_DAYS)

        return {
            "registrations_by_week": self._registrations_by_week(
                registrations_since, now
            ),
            "users_by_role": self.users.count_by_role(),
            "messages_by_day": self._messages_by_day(messages_since, now),
            "top_channels": self.messages.count_top_channels(limit=TOP_CHANNELS),
            "announcement_read_rates": self._announcement_read_rates(),
            "push_adoption": {
                "subscribers": self.push_subscriptions.count_distinct_users(),
                "total_users": self.users.count_total(),
            },
        }

    def _registrations_by_week(self, since, now) -> list[dict]:
        daily = {row["date"]: row["count"] for row in self.users.count_grouped_by_date(since)}
        buckets: dict[object, int] = {}
        current = _week_start(since.date())
        end = _week_start(now.date())
        while current <= end:
            buckets[current] = 0
            current += timedelta(days=7)
        for day, count in daily.items():
            if day >= since.date() and day <= now.date():
                buckets[_week_start(day)] += count
        return [
            {"label": week.isoformat(), "count": count}
            for week, count in sorted(buckets.items())
        ]

    def _messages_by_day(self, since, now) -> list[dict]:
        daily = {row["date"]: row["count"] for row in self.messages.count_grouped_by_date(since)}
        days = []
        for offset in range(MESSAGES_WINDOW_DAYS - 1, -1, -1):
            day = (now.date() - timedelta(days=offset))
            days.append({"label": day.isoformat(), "count": daily.get(day, 0)})
        return days

    def _announcement_read_rates(self) -> list[dict]:
        rates = []
        for announcement in self.announcements.list_all()[:RECENT_ANNOUNCEMENTS]:
            audience: set[int] = set()
            if announcement.target_channel_ids:
                for channel_id in announcement.target_channel_ids:
                    audience.update(self.channels.list_member_ids(channel_id))
            else:
                audience = {u.id or 0 for u in self.users.list_users()}
            read = self.announcements.count_read(announcement.id)
            rates.append(
                {
                    "title": announcement.title,
                    "read": read,
                    "unread": max(len(audience) - read, 0),
                }
            )
        return rates
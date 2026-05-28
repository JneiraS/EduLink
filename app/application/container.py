from dataclasses import dataclass

from app.application.use_cases.announcement_use_cases import (
    CreateAnnouncement,
    ListAnnouncements,
)
from app.application.use_cases.auth_use_cases import LoginUser, RegisterUser
from app.application.use_cases.channel_use_cases import CreateChannel
from app.application.use_cases.dashboard_use_case import GetDashboard
from app.application.use_cases.message_use_cases import (
    ListChannelMessages,
    ListUserChannels,
    SendMessage,
)
from app.application.use_cases.notification_use_cases import (
    ListNotifications,
    MarkNotificationRead,
    SubscribePushNotifications,
    UnsubscribePushNotifications,
)


@dataclass(slots=True)
class UseCaseContainer:
    register_user: RegisterUser
    login_user: LoginUser
    create_announcement: CreateAnnouncement
    list_announcements: ListAnnouncements
    get_dashboard: GetDashboard
    send_message: SendMessage
    list_channel_messages: ListChannelMessages
    list_user_channels: ListUserChannels
    list_notifications: ListNotifications
    mark_notification_read: MarkNotificationRead
    subscribe_push_notifications: SubscribePushNotifications
    unsubscribe_push_notifications: UnsubscribePushNotifications
    create_channel: CreateChannel

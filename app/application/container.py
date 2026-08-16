from dataclasses import dataclass

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
from app.application.use_cases.user_query_use_cases import FindUsersByIds, ListAllUsers


@dataclass(slots=True)
class UseCaseContainer:
    register_user: RegisterUser
    login_user: LoginUser
    create_announcement: CreateAnnouncement
    list_announcements: ListAnnouncements
    get_dashboard: GetDashboard
    send_message: SendMessage
    list_channel_messages: ListChannelMessages
    list_channel_members: ListChannelMembers
    list_user_channels: ListUserChannels
    list_notifications: ListNotifications
    mark_notification_read: MarkNotificationRead
    subscribe_push_notifications: SubscribePushNotifications
    unsubscribe_push_notifications: UnsubscribePushNotifications
    create_channel: CreateChannel
    add_channel_members: AddChannelMembers
    list_all_users: ListAllUsers
    find_users_by_ids: FindUsersByIds
    list_users_for_admin: ListUsersForAdmin
    list_announcements_for_admin: ListAnnouncementsForAdmin
    list_channels_for_admin: ListChannelsForAdmin
    update_user_role: UpdateUserRole
    toggle_user_active: ToggleUserActive
    delete_announcement: DeleteAnnouncement
    delete_channel: DeleteChannel

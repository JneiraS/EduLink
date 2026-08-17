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
    ListChannelMessages,
    ListChannelMembers,
    ListUserChannels,
    SendMessage,
)
from app.application.use_cases.message_template_use_cases import (
    CreateMessageTemplate,
    DeleteMessageTemplate,
    ListMessageTemplates,
    UpdateMessageTemplate,
)
from app.application.use_cases.notification_use_cases import (
    ListNotifications,
    MarkNotificationRead,
    SubscribePushNotifications,
    UnsubscribePushNotifications,
)
from app.application.use_cases.children_use_cases import (
    CreateChild,
    DeleteChild,
    LinkChildToClassChannels,
    ListChildren,
)
from app.application.use_cases.user_query_use_cases import FindUsersByIds, ListAllUsers


@dataclass(slots=True)
class UseCaseContainer:
    register_user: RegisterUser
    login_user: LoginUser
    create_user_with_invitation: CreateUserWithInvitation
    validate_invitation: ValidateInvitation
    accept_invitation: AcceptInvitation
    create_invitation: CreateInvitation
    create_announcement: CreateAnnouncement
    list_announcements: ListAnnouncements
    confirm_announcement_read: ConfirmAnnouncementRead
    get_announcement_read_status: GetAnnouncementReadStatus
    get_dashboard: GetDashboard
    send_message: SendMessage
    list_channel_messages: ListChannelMessages
    list_channel_members: ListChannelMembers
    list_user_channels: ListUserChannels
    list_notifications: ListNotifications
    mark_notification_read: MarkNotificationRead
    subscribe_push_notifications: SubscribePushNotifications
    unsubscribe_push_notifications: UnsubscribePushNotifications
    list_message_templates: ListMessageTemplates
    create_message_template: CreateMessageTemplate
    delete_message_template: DeleteMessageTemplate
    update_message_template: UpdateMessageTemplate
    create_channel: CreateChannel
    add_channel_members: AddChannelMembers
    open_direct_conversation: OpenDirectConversation
    list_all_users: ListAllUsers
    find_users_by_ids: FindUsersByIds
    list_users_for_admin: ListUsersForAdmin
    list_announcements_for_admin: ListAnnouncementsForAdmin
    list_channels_for_admin: ListChannelsForAdmin
    create_child: CreateChild
    list_children: ListChildren
    delete_child: DeleteChild
    link_child_to_class_channels: LinkChildToClassChannels
    update_user_role: UpdateUserRole
    toggle_user_active: ToggleUserActive
    delete_announcement: DeleteAnnouncement
    delete_channel: DeleteChannel

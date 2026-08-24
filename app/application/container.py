from dataclasses import dataclass

from app.application.use_cases.admin_stats_use_case import GetAdminStats
from app.application.use_cases.ai_use_cases import (
    RephraseDraft,
    SummarizeChannelMessages,
)
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
    GetAnnouncementPdf,
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
    MarkChannelNotificationsRead,
    MarkNotificationRead,
    SetGlobalNotifications,
    SubscribePushNotifications,
    ToggleChannelNotifications,
    UnsubscribePushNotifications,
)
from app.application.use_cases.children_use_cases import (
    CreateChild,
    DeleteChild,
    FindParentsByChild,
    LinkChildToClassChannels,
    ListChildren,
    ListClassNames,
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
    get_announcement_pdf: GetAnnouncementPdf
    get_dashboard: GetDashboard
    get_admin_stats: GetAdminStats
    send_message: SendMessage
    search_channel_messages: SearchChannelMessages
    list_channel_messages: ListChannelMessages
    list_pinned_messages: ListPinnedMessages
    pin_message: PinMessage
    list_channel_members: ListChannelMembers
    list_user_channels: ListUserChannels
    list_notifications: ListNotifications
    mark_notification_read: MarkNotificationRead
    mark_channel_notifications_read: MarkChannelNotificationsRead
    get_notification_settings: GetNotificationSettings
    set_global_notifications: SetGlobalNotifications
    toggle_channel_notifications: ToggleChannelNotifications
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
    list_class_names: ListClassNames
    delete_child: DeleteChild
    link_child_to_class_channels: LinkChildToClassChannels
    find_parents_by_child: FindParentsByChild
    update_user_role: UpdateUserRole
    toggle_user_active: ToggleUserActive
    delete_announcement: DeleteAnnouncement
    delete_channel: DeleteChannel
    summarize_channel_messages: SummarizeChannelMessages
    rephrase_draft: RephraseDraft

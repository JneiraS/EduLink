from collections.abc import Mapping

MESSAGE_CHANNEL_NOTIFICATION_PREFIX = "Nouveau message dans le canal "


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    return [value]


def read_value(item, key: str, default=None):
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def parse_member_ids(form_data) -> list[int]:
    raw_members = form_data.getlist("members") + form_data.getlist("members[]")
    return sorted({int(value) for value in raw_members if value.isdigit()})


def build_channel_maps(channels):
    channel_id_by_name = {}
    channel_links_by_name = {}

    for channel in as_list(channels):
        channel_name = str(read_value(channel, "name", "") or "").strip()
        channel_id = read_value(channel, "id")
        if not channel_name or channel_id is None:
            continue

        channel_id_by_name[channel_name.casefold()] = channel_id
        channel_links_by_name[channel_name] = channel_id

    return channel_id_by_name, channel_links_by_name


def build_notification_channel_links(
    notifications,
    channel_id_by_name,
    message_prefix: str = MESSAGE_CHANNEL_NOTIFICATION_PREFIX,
):
    notification_channel_links = {}
    notification_channel_links_by_content = {}

    for notification in notifications:
        content = str(read_value(notification, "content", "") or "")
        if not content.startswith(message_prefix):
            continue

        notification_id = read_value(notification, "id")
        channel_name_key = (
            content[len(message_prefix) :].strip().rstrip(" .!?:;").casefold()
        )
        channel_id = channel_id_by_name.get(channel_name_key)
        if channel_id is None:
            continue

        if notification_id is not None:
            notification_channel_links[notification_id] = channel_id
        notification_channel_links_by_content[content] = channel_id

    return notification_channel_links, notification_channel_links_by_content


def resolve_channel_name(
    channel_id: int, user_channels, db_channel_name: str | None = None
) -> str:
    if db_channel_name:
        channel_name = str(db_channel_name).strip()
        if channel_name:
            return channel_name

    for channel in user_channels:
        if read_value(channel, "id") != channel_id:
            continue
        channel_name = str(read_value(channel, "name", "") or "").strip()
        if channel_name:
            return channel_name

    return f"Canal #{channel_id}"


def build_member_name_index(channel_members, channel_messages, users_lookup):
    member_names = {}
    for member in channel_members:
        member_names[member.id] = member.full_name
        member_names[str(member.id)] = member.full_name

    sender_ids = {message.sender_id for message in channel_messages}
    if sender_ids:
        for user in users_lookup(sender_ids):
            member_names[user.id] = user.full_name
            member_names[str(user.id)] = user.full_name

    return member_names


def resolve_sender_name(member_names, sender_id):
    try:
        sender_id_int = int(sender_id)
    except (TypeError, ValueError):
        sender_id_int = None

    return (
        member_names.get(sender_id)
        or member_names.get(str(sender_id))
        or (member_names.get(sender_id_int) if sender_id_int is not None else None)
        or f"Utilisateur {sender_id}"
    )


def build_messages_view(channel_messages, member_names):
    return [
        {
            "sender_name": resolve_sender_name(member_names, message.sender_id),
            "created_at": message.created_at,
            "content": message.content,
        }
        for message in channel_messages
    ]

from collections.abc import Mapping

from app.domain.entities.user import UserRole


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


ROLE_ORDER = (UserRole.ADMIN, UserRole.TEACHER, UserRole.PARENT)
ROLE_LABELS = {
    UserRole.ADMIN: "Administrateurs",
    UserRole.TEACHER: "Enseignants",
    UserRole.PARENT: "Parents",
}


def group_users_by_role(users) -> list[tuple[UserRole, str, list]]:
    """Group domain users by role into fixed-order sections for the member picker."""
    buckets = {role: [] for role in ROLE_ORDER}
    for user in users:
        try:
            role = UserRole(user.role)
        except (TypeError, ValueError):
            continue
        if role in buckets:
            buckets[role].append(user)
    return [(role, ROLE_LABELS[role], buckets[role]) for role in ROLE_ORDER]


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
            "id": message.id,
            "sender_id": message.sender_id,
            "sender_name": resolve_sender_name(member_names, message.sender_id),
            "created_at": message.created_at,
            "content": message.content,
            "is_pinned": message.is_pinned,
        }
        for message in channel_messages
    ]

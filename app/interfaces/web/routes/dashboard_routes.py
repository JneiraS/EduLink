from flask import Blueprint, render_template
from flask_login import login_required
from collections.abc import Mapping

from app.interfaces.web.routes.utils import current_actor, get_use_cases

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/")


@dashboard_bp.route("/", methods=["GET"])
@login_required
def home():
    def as_list(value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, (tuple, set)):
            return list(value)
        return [value]

    actor = current_actor()
    use_cases = get_use_cases()
    data = use_cases.get_dashboard.execute(actor)

    if isinstance(data, dict):
        role_message = data.get("role_message", "Espace utilisateur")
        latest_announcements = as_list(data.get("latest_announcements", []))
        notifications = as_list(data.get("notifications", []))
    else:
        role_message = getattr(data, "role_message", "Espace utilisateur")
        latest_announcements = as_list(getattr(data, "latest_announcements", []))
        notifications = as_list(getattr(data, "notifications", []))

    # Build direct links for "new message in channel" notifications.
    channels = as_list(use_cases.list_user_channels.execute(actor))

    channel_id_by_name = {}
    channel_links_by_name = {}
    for channel in channels:
        if isinstance(channel, Mapping):
            channel_name = str(channel.get("name") or "").strip()
            channel_id = channel.get("id")
        else:
            channel_name = str(getattr(channel, "name", "") or "").strip()
            channel_id = getattr(channel, "id", None)

        if not channel_name or channel_id is None:
            continue

        channel_id_by_name[channel_name.casefold()] = channel_id
        channel_links_by_name[channel_name] = channel_id
    message_prefix = "Nouveau message dans le canal "
    notification_channel_links = {}
    notification_channel_links_by_content = {}

    for notification in notifications:
        if isinstance(notification, dict):
            content = notification.get("content") or ""
            notification_id = notification.get("id")
        else:
            content = getattr(notification, "content", "") or ""
            notification_id = getattr(notification, "id", None)
        if not content.startswith(message_prefix):
            continue
        channel_name = (
            content[len(message_prefix) :].strip().rstrip(" .!?:;").casefold()
        )
        channel_id = channel_id_by_name.get(channel_name)
        if channel_id and notification_id is not None:
            notification_channel_links[notification_id] = channel_id
        if channel_id:
            notification_channel_links_by_content[content] = channel_id

    return render_template(
        "dashboard/home.html",
        role_message=role_message,
        latest_announcements=latest_announcements,
        notifications=notifications,
        notification_channel_links=notification_channel_links,
        notification_channel_links_by_content=notification_channel_links_by_content,
        channel_links_by_name=channel_links_by_name,
    )

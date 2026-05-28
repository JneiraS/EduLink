from flask import Blueprint, render_template
from flask_login import login_required

from app.interfaces.web.routes.presentation import (
    as_list,
    build_channel_maps,
    build_notification_channel_links,
    read_value,
)
from app.interfaces.web.routes.utils import current_actor, get_use_cases

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/")


@dashboard_bp.route("/", methods=["GET"])
@login_required
def home():
    actor = current_actor()
    use_cases = get_use_cases()
    data = use_cases.get_dashboard.execute(actor)

    role_message = read_value(data, "role_message", "Espace utilisateur")
    latest_announcements = as_list(read_value(data, "latest_announcements", []))
    notifications = as_list(read_value(data, "notifications", []))

    channels = use_cases.list_user_channels.execute(actor)
    channel_id_by_name, channel_links_by_name = build_channel_maps(channels)
    notification_channel_links, notification_channel_links_by_content = (
        build_notification_channel_links(notifications, channel_id_by_name)
    )

    return render_template(
        "dashboard/home.html",
        role_message=role_message,
        latest_announcements=latest_announcements,
        notifications=notifications,
        notification_channel_links=notification_channel_links,
        notification_channel_links_by_content=notification_channel_links_by_content,
        channel_links_by_name=channel_links_by_name,
    )

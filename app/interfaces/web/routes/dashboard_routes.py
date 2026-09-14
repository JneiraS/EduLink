from datetime import date

from flask import Blueprint, render_template
from flask_login import login_required

from app.interfaces.web.routes.presentation import as_list, read_value
from app.interfaces.web.routes.utils import current_actor, get_use_cases

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/")

_FR_DAYS = (
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
    "Dimanche",
)
_FR_MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)


@dashboard_bp.route("/", methods=["GET"])
@login_required
def home():
    actor = current_actor()
    use_cases = get_use_cases()

    today = date.today()
    data = use_cases.get_dashboard.execute(actor, today=today)

    date_label = (
        f"{_FR_DAYS[today.weekday()]} {today.day} {_FR_MONTHS[today.month - 1]}"
    )

    role_message = read_value(data, "role_message", "Espace utilisateur")
    latest_announcements = as_list(read_value(data, "latest_announcements", []))
    notifications = as_list(read_value(data, "notifications", []))
    stats = read_value(data, "stats", {})
    conversations = as_list(read_value(data, "conversations", []))
    children = as_list(read_value(data, "children", []))
    user_counts = read_value(data, "user_counts", None)
    channel_count = read_value(data, "channel_count", None)
    announcement_count = read_value(data, "announcement_count", None)
    recent_users = as_list(read_value(data, "recent_users", []))
    calendar_info = read_value(data, "calendar", None)

    return render_template(
        "dashboard/home.html",
        role_message=role_message,
        date_label=date_label,
        latest_announcements=latest_announcements,
        notifications=notifications,
        stats=stats,
        conversations=conversations,
        children=children,
        user_counts=user_counts,
        channel_count=channel_count,
        announcement_count=announcement_count,
        recent_users=recent_users,
        calendar_info=calendar_info,
    )

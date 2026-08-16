from flask import Blueprint, render_template
from flask_login import login_required

from app.interfaces.web.routes.presentation import as_list, read_value
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

    return render_template(
        "dashboard/home.html",
        role_message=role_message,
        latest_announcements=latest_announcements,
        notifications=notifications,
    )

from flask import Blueprint, jsonify, redirect, url_for
from flask_login import login_required

from app.domain.errors import NotFoundError
from app.interfaces.web.routes.utils import current_actor, get_use_cases

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@notifications_bp.route("/", methods=["GET"])
@login_required
def list_notifications():
    notifications = get_use_cases().list_notifications.execute(current_actor())
    payload = [
        {
            "id": n.id,
            "content": n.content,
            "is_read": n.is_read,
            "channel_id": n.channel_id,
            "created_at": str(n.created_at),
        }
        for n in notifications
    ]
    return jsonify(payload)


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
@login_required
def read_notification(notification_id: int):
    try:
        get_use_cases().mark_notification_read.execute(current_actor(), notification_id)
    except NotFoundError:
        pass
    return redirect(url_for("dashboard.home"))

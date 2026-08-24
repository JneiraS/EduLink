from flask import Blueprint, jsonify
from flask_login import login_required

from app.domain.errors import (
    AuthorizationError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from app.extensions import limiter
from app.interfaces.web.routes.utils import current_actor, get_use_cases

ai_bp = Blueprint("ai", __name__, url_prefix="/ai")

_ERROR_STATUS = {
    ValidationError: 400,
    AuthorizationError: 403,
    NotFoundError: 404,
    ServiceUnavailableError: 503,
}


@ai_bp.route("/channels/<int:channel_id>/summary", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def channel_summary(channel_id: int):
    try:
        summary = get_use_cases().summarize_channel_messages.execute(
            current_actor(), channel_id=channel_id
        )
    except (ValidationError, AuthorizationError, NotFoundError,
            ServiceUnavailableError) as exc:
        return jsonify({"error": str(exc)}), _ERROR_STATUS[type(exc)]
    return jsonify({"summary": summary})

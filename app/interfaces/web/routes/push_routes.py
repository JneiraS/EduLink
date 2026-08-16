import base64
from urllib.parse import urlparse

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from flask_login import login_required

from app.interfaces.web.routes.utils import current_actor, get_use_cases

push_bp = Blueprint("push", __name__)

ALLOWED_PUSH_HOSTS = {
    "fcm.googleapis.com",
    "updates.push.services.mozilla.com",
    "web.push.apple.com",
}


def _is_valid_base64url(value: str) -> bool:
    if not value or len(value) > 255:
        return False
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, TypeError):
        return False
    return len(decoded) >= 16


def _validate_subscription_payload(payload: dict) -> bool:
    endpoint = payload.get("endpoint")
    keys = payload.get("keys") or {}
    p256dh_key = keys.get("p256dh")
    auth_key = keys.get("auth")

    if not endpoint or not p256dh_key or not auth_key:
        return False

    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    if parsed.hostname not in ALLOWED_PUSH_HOSTS:
        return False

    return _is_valid_base64url(p256dh_key) and _is_valid_base64url(auth_key)


@push_bp.route("/service-worker.js", methods=["GET"])
def service_worker():
    return send_from_directory(current_app.static_folder + "/js", "sw.js")


@push_bp.route("/push/public-key", methods=["GET"])
@login_required
def get_public_key():
    key = current_app.config.get("VAPID_PUBLIC_KEY", "")
    return jsonify({"publicKey": key})


@push_bp.route("/push/subscribe", methods=["POST"])
@login_required
def subscribe_push():
    payload = request.get_json(silent=True) or {}

    if not _validate_subscription_payload(payload):
        return jsonify({"error": "Invalid subscription payload"}), 400

    get_use_cases().subscribe_push_notifications.execute(
        actor=current_actor(),
        endpoint=payload["endpoint"],
        p256dh_key=payload["keys"]["p256dh"],
        auth_key=payload["keys"]["auth"],
    )
    return jsonify({"status": "ok"})


@push_bp.route("/push/unsubscribe", methods=["POST"])
@login_required
def unsubscribe_push():
    payload = request.get_json(silent=True) or {}
    endpoint = payload.get("endpoint")
    if not endpoint:
        return jsonify({"error": "Missing endpoint"}), 400

    get_use_cases().unsubscribe_push_notifications.execute(
        actor=current_actor(),
        endpoint=endpoint,
    )
    return jsonify({"status": "ok"})

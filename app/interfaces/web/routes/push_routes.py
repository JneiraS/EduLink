from flask import Blueprint, current_app, jsonify, request, send_from_directory
from flask_login import login_required

from app.extensions import csrf
from app.interfaces.web.routes.utils import current_actor, get_use_cases

push_bp = Blueprint("push", __name__)


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
@csrf.exempt
def subscribe_push():
    payload = request.get_json(silent=True) or {}
    endpoint = payload.get("endpoint")
    keys = payload.get("keys") or {}
    p256dh_key = keys.get("p256dh")
    auth_key = keys.get("auth")

    if not endpoint or not p256dh_key or not auth_key:
        return jsonify({"error": "Invalid subscription payload"}), 400

    get_use_cases().subscribe_push_notifications.execute(
        actor=current_actor(),
        endpoint=endpoint,
        p256dh_key=p256dh_key,
        auth_key=auth_key,
    )
    return jsonify({"status": "ok"})


@push_bp.route("/push/unsubscribe", methods=["POST"])
@login_required
@csrf.exempt
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

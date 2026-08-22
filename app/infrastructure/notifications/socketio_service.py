import json
import logging
from binascii import Error as BinasciiError
from concurrent.futures import ThreadPoolExecutor

from pywebpush import WebPushException, webpush

from app.domain.ports.services import RealtimeNotificationPort

logger = logging.getLogger(__name__)

_WEB_PUSH_WORKERS = 4


class SocketIONotificationService(RealtimeNotificationPort):
    def __init__(
        self,
        socketio,
        push_subscriptions,
        app,
        vapid_private_key: str,
        vapid_public_key: str,
        vapid_subject: str,
    ):
        self.socketio = socketio
        self.push_subscriptions = push_subscriptions
        self.app = app
        self.vapid_private_key = vapid_private_key
        self.vapid_public_key = vapid_public_key
        self.vapid_subject = vapid_subject
        self._web_push_enabled = True
        self._executor = ThreadPoolExecutor(max_workers=_WEB_PUSH_WORKERS)

    def notify_user(self, user_id: int, payload: dict) -> None:
        self.socketio.emit("notification", payload, room=f"user_{user_id}")
        self._send_web_push(user_id, payload)

    def notify_channel(self, channel_id: int, payload: dict) -> None:
        self.socketio.emit("channel_message", payload, room=f"channel_{channel_id}")

    def _send_web_push(self, user_id: int, payload: dict) -> None:
        if not self._web_push_enabled:
            return

        if not self.vapid_private_key or not self.vapid_public_key:
            return

        subscriptions = self.push_subscriptions.list_by_user(user_id)
        if not subscriptions:
            return

        data = json.dumps(
            {
                "title": "EduLink",
                "body": payload.get("content", "Nouvelle notification"),
                "url": "/",
            }
        )

        for subscription in subscriptions:
            subscription_info = {
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh_key,
                    "auth": subscription.auth_key,
                },
            }
            self._executor.submit(self._send_one, subscription_info, data)

    def _send_one(self, subscription_info: dict, data: str) -> None:
        try:
            webpush(
                subscription_info=subscription_info,
                data=data,
                vapid_private_key=self.vapid_private_key,
                vapid_claims={"sub": self.vapid_subject},
            )
        except WebPushException as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", 0)
            if status_code in {404, 410}:
                self._cleanup_endpoint(subscription_info["endpoint"])
        except (ValueError, TypeError, BinasciiError) as exc:
            # Invalid VAPID keys should not break the user request flow.
            self._web_push_enabled = False
            logger.warning(
                "Web push disabled due to invalid VAPID configuration: %s", exc
            )

    def _cleanup_endpoint(self, endpoint: str) -> None:
        try:
            with self.app.app_context():
                self.push_subscriptions.delete_by_endpoint(endpoint)
                from app.extensions import db

                db.session.remove()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to remove stale push subscription: %s", exc)
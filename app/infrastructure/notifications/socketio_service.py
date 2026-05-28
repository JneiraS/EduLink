import json

from pywebpush import WebPushException, webpush

from app.domain.ports.services import RealtimeNotificationPort


class SocketIONotificationService(RealtimeNotificationPort):
    def __init__(
        self,
        socketio,
        push_subscriptions,
        vapid_private_key: str,
        vapid_public_key: str,
        vapid_subject: str,
    ):
        self.socketio = socketio
        self.push_subscriptions = push_subscriptions
        self.vapid_private_key = vapid_private_key
        self.vapid_public_key = vapid_public_key
        self.vapid_subject = vapid_subject

    def notify_user(self, user_id: int, payload: dict) -> None:
        self.socketio.emit("notification", payload, room=f"user_{user_id}")
        self._send_web_push(user_id, payload)

    def notify_channel(self, channel_id: int, payload: dict) -> None:
        self.socketio.emit("channel_message", payload, room=f"channel_{channel_id}")

    def _send_web_push(self, user_id: int, payload: dict) -> None:
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
                    self.push_subscriptions.delete_by_endpoint(subscription.endpoint)

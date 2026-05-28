from app.domain.ports.services import RealtimeNotificationPort


class SocketIONotificationService(RealtimeNotificationPort):
    def __init__(self, socketio):
        self.socketio = socketio

    def notify_user(self, user_id: int, payload: dict) -> None:
        self.socketio.emit("notification", payload, room=f"user_{user_id}")

    def notify_channel(self, channel_id: int, payload: dict) -> None:
        self.socketio.emit("channel_message", payload, room=f"channel_{channel_id}")

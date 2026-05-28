from flask_login import current_user
from flask_socketio import join_room


def register_socket_handlers(socketio):
    @socketio.on("connect")
    def on_connect():
        if not current_user.is_authenticated:
            return False

        join_room(f"user_{current_user.id}")
        for channel in getattr(current_user, "channels", []):
            join_room(f"channel_{channel.id}")

import os

from app import create_app, socketio

app = create_app()

if __name__ == "__main__":
    host = os.getenv("EDULINK_HOST", "127.0.0.1")
    port = int(os.getenv("EDULINK_PORT", "5050"))
    debug = os.getenv("EDULINK_DEBUG", "1") == "1"
    socketio.run(app, host=host, port=port, debug=debug, use_reloader=False)

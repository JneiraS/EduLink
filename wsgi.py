"""Gunicorn entrypoint.

Flask-SocketIO's ``SocketIO.init_app(app)`` attaches the SockIOMiddleware on
``app.wsgi_app``, so the raw Flask ``app`` is the correct WSGI target for
gunicorn — it routes SocketIO traffic (including WebSocket upgrades) through
the middleware automatically.
"""

from run import app

application = app
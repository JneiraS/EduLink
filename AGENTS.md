# AGENTS.md

EduLink MVP: Flask school-communication platform using hexagonal architecture (Ports & Adapters). Python 3.12+, Flask, Flask-SQLAlchemy, SQLite, Flask-SocketIO.

## Commands

```bash
# Setup (Linux; the Windows path in README is stale for this env)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run dev server (default http://127.0.0.1:5050, binds 0.0.0.0)
python run.py

# Tests
pytest

# HTTPS tunnel for mobile web-push testing
bash scripts/start_tunnel.sh [PORT]   # tries cloudflared -> ngrok -> npx localtunnel
```

No linter, formatter, or CI config exists. `pyproject.toml` only configures pytest (`pythonpath = ["."]`) so bare `pytest` works — don't rely on `python -m pytest`.

## Architecture

Hexagonal: dependencies point inward. `interfaces -> application -> domain`. Follow this layering — do not import Flask/SQLAlchemy into `app/domain`.

- `app/domain/` — entities (`User`, `Channel`, ...), ports (abstract `repositories.py`, `services.py`), `errors.py`. No framework imports.
- `app/application/` — pure use cases + `container.py` (composition root).
- `app/infrastructure/` — adapters: `database/models.py` (SQLAlchemy), `repositories/`, `auth/`, `notifications/`.
- `app/interfaces/web/` — `routes/` blueprints, `templates/`, `static/`, `socket_events.py`.
- `app/config/settings.py` — `BaseConfig`/`DevelopmentConfig`/`TestingConfig` (no env file loader beyond `.env`).

Use cases and repos are wired in `app/__init__.py` `create_app()` and registered on `app.extensions["use_cases"]` / `app.extensions["services"]`. Route code reaches them via `get_use_cases()` / `current_actor()` from `app/interfaces/web/routes/utils.py` — not by instantiating repos directly.

## Key conventions

- Roles enum `UserRole` = `PARENT` / `TEACHER` / `ADMIN` (`app/domain/entities/user.py`). "Can manage channel members" = `ADMIN` or `TEACHER`.
- Use-case errors are `DomainError` subclasses in `app/domain/errors.py`: `AuthorizationError`, `NotFoundError`, `ValidationError`, `AuthenticationError`. Routes catch these and `flash(str(exc), "danger")`. Don't raise `flask.abort` for business logic. `create_app()` also registers a global `DomainError` errorhandler that flashes and redirects to the dashboard — a safety net, so don't rely on uncaught errors bubbling.
- Flask-WTF CSRF is on for dev, off in tests (`TestingConfig.WTF_CSRF_ENABLED = False`). In tests that need a logged-in session, set `sess["_user_id"]` directly (see `tests/interfaces/test_messages_channel_permissions.py:_login`).
- Admin seeding: `create_app()` seeds `admin@edulink.local` (or `EDULINK_ADMIN_EMAIL`) with `EDULINK_ADMIN_PASSWORD`; if unset, a random one is printed to console. `.env` is gitignored but already contains a dev admin password + VAPID keys — do not commit or log secrets.
- Uploads: `UPLOAD_FOLDER` (default `uploads/`), only `.pdf`, max 5 MB (`MAX_CONTENT_LENGTH`, `ALLOWED_EXTENSIONS` in settings).

## Testing notes

- `tests/conftest.py` provides an `app` fixture via `create_app(testing=True)` (in-memory SQLite, CSRF off). Create users/channels inside `with app.app_context():` and flush to get IDs before using `app.test_client()`.
- DB schema is created with `db.create_all()` on app creation — there are **no migrations** (no Alembic). Schema changes require deleting the dev `*.db`/`instance/` file.
- Real-time features (SocketIO) and web push are only exercised indirectly; the notification/message use-case tests rely on the realtime service tolerating no connected client.
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

# Migrations (Alembic)
alembic upgrade head        # explicit fallback; dev server auto-migrates on boot
alembic revision --autogenerate -m "describe change"
alembic downgrade -1

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

Routes must not import `app.infrastructure` models or `app.extensions.db` directly. Reads (e.g. listing all users, resolving sender names) go through query use cases (`get_use_cases().list_all_users` / `.find_users_by_ids`). `current_actor()` fetches the domain `User` via the users repo (`find_by_id`), so ORM→domain mapping lives only in `_to_entity`. `get_services()` exists solely for the Flask-Login handoff (`get_services()["users"].get_auth_model(id)`), which returns the ORM `UserMixin` instance — a concrete-repo method, deliberately not on the abstract port.

## Key conventions

- Roles enum `UserRole` = `PARENT` / `TEACHER` / `ADMIN` (`app/domain/entities/user.py`). "Can manage channel members" = `ADMIN` or `TEACHER`.
- Use-case errors are `DomainError` subclasses in `app/domain/errors.py`: `AuthorizationError`, `NotFoundError`, `ValidationError`, `AuthenticationError`. Routes catch these and `flash(str(exc), "danger")`. Don't raise `flask.abort` for business logic. `create_app()` also registers a global `DomainError` errorhandler that flashes and redirects to the dashboard — a safety net, so don't rely on uncaught errors bubbling.
- Flask-WTF CSRF is on for dev, off in tests (`TestingConfig.WTF_CSRF_ENABLED = False`). In tests that need a logged-in session, set `sess["_user_id"]` directly (see `tests/interfaces/test_messages_channel_permissions.py:_login`).
- Admin seeding: `create_app()` seeds `admin@edulink.local` (or `EDULINK_ADMIN_EMAIL`) with `EDULINK_ADMIN_PASSWORD`; if unset, a random one is generated — printed to console **only** in debug mode (`EDULINK_DEBUG=1`), otherwise a generic warning is logged. `.env` is gitignored but already contains a dev admin password + VAPID keys — do not commit or log secrets.
- `SECRET_KEY` is resolved in `create_app()` (`_resolve_secret_key`): env var wins; otherwise a random key is generated and persisted to `instance/secret_key` (0600, gitignored). The public default `dev-secret-change-me` is never used — do not regress to a hardcoded key.
- Login POST is rate-limited (`Flask-Limiter`, 5 per 15 min per IP) in dev (`RATE_LIMIT_ENABLED`, off in `TestingConfig`; rate-limit tests re-enable via `app.config["RATE_LIMIT_ENABLED"] = True` + `limiter.enabled = True` + `limiter.reset()`).
- Push subscription `endpoint` is allowlisted (HTTPS + FCM/Mozilla/Apple hosts) and `p256dh`/`auth` keys must be valid base64url — SSRF guard in `push_routes.py`. Don't widen the allowlist without a security review.
- Security headers (CSP with `script-src` `'self'` + CDNs, `X-Frame-Options`, `nosniff`, `Referrer-Policy`, HSTS when HTTPS) are set via `after_request`; the theme script lives in `static/js/app.js` (no inline scripts) so CSP needs no `'unsafe-inline'` for scripts.
- Uploads: `UPLOAD_FOLDER` (default `uploads/`), only `.pdf`, max 5 MB (`MAX_CONTENT_LENGTH`, `ALLOWED_EXTENSIONS` in settings), plus PDF magic-byte (`%PDF`) check before saving.
- Notifications: `channel_id` FK column (nullable) links message-notifications to a channel; announcement-notifications leave it `NULL`. UI links to the channel via `n.channel_id` — do **not** parse the human-readable `content` string. Web push delivery runs in a `ThreadPoolExecutor` (background) inside `SocketIONotificationService`; DB writes and socket emits stay in the request.
- Pagination: announcements use page-based `paginate(page, per_page)` (default 10, `?page=`); channel messages use a chat pattern — latest `limit` (default 50) plus a "load older" link via `?before=<message_id>` (`list_by_channel(channel_id, limit, before_id)` returns `(messages, has_more)`).

## Documentation

Developer docs live in `docs/` and are the onboarding path for new developers: `ARCHITECTURE.md` (how the project works) and `ADDING_A_FEATURE.md` (the step-by-step recipe for adding a feature). They must never drift from the code. Whenever you implement a new feature — new use case, port method, entity, route, template, migration, config/settings change, or test convention — update the relevant `docs/` file(s) in the same change. A feature is not done, and must not be committed, if the docs are stale.

## Testing notes

- `tests/conftest.py` provides an `app` fixture via `create_app(testing=True)` (in-memory SQLite, CSRF off). Create users/channels inside `with app.app_context():` and flush to get IDs before using `app.test_client()`. Shared helpers live in `tests/helpers.py` (`login`, `create_user`, `create_channel`, `add_message`, `add_announcement`, `add_notification`).
- Schema is managed by **Alembic** (`migrations/`). In dev, `create_app()` runs `alembic upgrade head` automatically on boot; `scripts/migrate.sh` is the explicit fallback. In testing, `create_app(testing=True)` still uses `db.create_all()` on the in-memory DB (Alembic can't share a `:memory:` connection), so schema changes go through a new Alembic migration for dev, not `create_all`.
- `TestingConfig` sets `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY` to `""` so tests are hermetic and never read `.env` keys or trigger web push.
- CSRF is off in `TestingConfig`; CSRF tests re-enable it per-test via `app.config["WTF_CSRF_ENABLED"] = True`. Note flashed messages and template values are HTML-escaped (apostrophes render as `&#39;`), so assert on substrings without apostrophes.
- Real-time features (SocketIO) and web push are only exercised indirectly; the notification/message use-case tests rely on the realtime service tolerating no connected client.
- Input validation: `RegisterUser` enforces email format + lengths (`full_name` ≤120, email ≤254, password 8–128); announcement title ≤255 / content ≤5000; channel name ≤120; message content ≤5000. New length caps must raise `ValidationError` in the use case, not in the route.
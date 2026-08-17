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
- `app/config/settings.py` — `BaseConfig`/`DevelopmentConfig`/`TestingConfig`/`ProductionConfig` (no env file loader beyond `.env`). `create_app()` selects config: `TestingConfig` if `testing=True`, else `ProductionConfig` if `APP_ENV=production`, else `DevelopmentConfig`.

Use cases and repos are wired in `app/__init__.py` `create_app()` and registered on `app.extensions["use_cases"]` / `app.extensions["services"]`. Route code reaches them via `get_use_cases()` / `current_actor()` from `app/interfaces/web/routes/utils.py` — not by instantiating repos directly.

Routes must not import `app.infrastructure` models or `app.extensions.db` directly. Reads (e.g. listing all users, resolving sender names) go through query use cases (`get_use_cases().list_all_users` / `.find_users_by_ids`). `current_actor()` fetches the domain `User` via the users repo (`find_by_id`), so ORM→domain mapping lives only in `_to_entity`. `get_services()` exists solely for the Flask-Login handoff (`get_services()["users"].get_auth_model(id)`), which returns the ORM `UserMixin` instance — a concrete-repo method, deliberately not on the abstract port.

## Key conventions

- Roles enum `UserRole` = `PARENT` / `TEACHER` / `ADMIN` (`app/domain/entities/user.py`). "Can manage channel members" = `ADMIN` or `TEACHER`.
- Use-case errors are `DomainError` subclasses in `app/domain/errors.py`: `AuthorizationError`, `NotFoundError`, `ValidationError`, `AuthenticationError`. Routes catch these and `flash(str(exc), "danger")`. Don't raise `flask.abort` for business logic. `create_app()` also registers a global `DomainError` errorhandler that flashes and redirects to the dashboard — a safety net, so don't rely on uncaught errors bubbling.
- Flask-WTF CSRF is on for dev, off in tests (`TestingConfig.WTF_CSRF_ENABLED = False`). In tests that need a logged-in session, set `sess["_user_id"]` directly (see `tests/interfaces/test_messages_channel_permissions.py:_login`).
- Admin seeding: `create_app()` seeds `admin@edulink.local` (or `EDULINK_ADMIN_EMAIL`) with `EDULINK_ADMIN_PASSWORD`; if unset, a random one is generated — printed to console **only** in debug mode (`EDULINK_DEBUG=1`), otherwise a generic warning is logged. `.env` is gitignored but already contains a dev admin password + VAPID keys — do not commit or log secrets.
- `SECRET_KEY` is resolved in `create_app()` (`_resolve_secret_key`): env var wins; otherwise a random key is generated and persisted to `instance/secret_key` (0600, gitignored). The public default `dev-secret-change-me` is never used — do not regress to a hardcoded key.
- Login POST is rate-limited (`Flask-Limiter`, 5 per 15 min per IP) in dev (`RATE_LIMIT_ENABLED`, off in `TestingConfig`; rate-limit tests re-enable via `app.config["RATE_LIMIT_ENABLED"] = True` + `limiter.enabled = True` + `limiter.reset()`). `/auth/invite/<token>` POST is also rate-limited (10/hour/IP). All login failures raise the **same** `AuthenticationError("Invalid credentials")` — no account enumeration (unknown email / no password / bad password / disabled all look identical). After a successful login or invitation acceptance, `session.clear()` + `session.permanent = True` run before `login_user()`.
- Push subscription `endpoint` is allowlisted (HTTPS + FCM/Mozilla/Apple hosts, **port 443 only**) and `p256dh` must be **exactly 65 bytes** (uncompressed ECDH P-256 public key) / `auth` valid base64url — SSRF + strict-key guard in `push_routes.py`. Don't widen the allowlist without a security review.
- Security headers (CSP with `script-src` `'self'` + CDNs, `X-Frame-Options`, `nosniff`, `Referrer-Policy`, HSTS when `SESSION_COOKIE_SECURE`) are set via `after_request`; the theme script lives in `static/js/app.js` (no inline scripts) so CSP needs no `'unsafe-inline'` for scripts.
- Sessions: `SESSION_COOKIE_HTTPONLY` + `SameSite=Lax` always; `SESSION_COOKIE_SECURE` = env-driven in dev, forced `True` in `ProductionConfig` (which also sets `PERMANENT_SESSION_LIFETIME`, default 12 h via `SESSION_LIFETIME_SECONDS`).
- Uploads: `UPLOAD_FOLDER` (default `uploads/`, gitignored), only `.pdf`, max 5 MB (`MAX_CONTENT_LENGTH`, `ALLOWED_EXTENSIONS` in settings), plus PDF magic-byte (`%PDF`) check before saving.
- Notifications: `channel_id` FK column (nullable) links message-notifications to a channel; announcement-notifications leave it `NULL`. `content` is `Text` (announcement titles up to 255 chars would overflow a `String(255)`). UI links to the channel via `n.channel_id` — do **not** parse the human-readable `content` string. Web push delivery runs in a bounded `ThreadPoolExecutor` (`_WEB_PUSH_WORKERS = 4`) inside `SocketIONotificationService`; DB writes and socket emits stay in the request.
- Pagination: announcements use page-based `paginate(page, per_page, channel_ids=None)` (default 10, `?page=`) — the listing is **scoped by membership** (global announcements always visible; channel-targeted only if the actor is a member, enforced in the repo query). `GetAnnouncementPdf` / `ConfirmAnnouncementRead` apply the same scope (404 outside it). Channel messages use a chat pattern — latest `limit` (default 50) plus a "load older" link via `?before=<message_id>` (`list_by_channel(channel_id, limit, before_id)` returns `(messages, has_more)`).
- Read-model DTOs: user listings exposed to templates (`list_all_users`, `find_users_by_ids`, `list_channel_members`) return **`UserSummary`** (`id`/`full_name`/`role`), never full `User` entities — don't regress to leaking `email`/`password_hash` into template context.
- Admin stats: `GET /admin/stats` (`admin_routes.py`) → `GetAdminStats` (5 repos) returns 6 sections rendered by Chart.js (`static/js/admin-charts.js`). Time windows + zero-padding live in the use case (`REGISTRATIONS_WINDOW_DAYS=30` bucketed by ISO week, `MESSAGES_WINDOW_DAYS=14`); repos only do raw `GROUP BY date(created_at)` (`count_grouped_by_date`, `count_by_role`, `count_top_channels`, `count_distinct_users`). Announcement read-rates are computed in the use case (audience = `count_total()` for global, union of `channels.list_member_ids()` for targeted), not stored. Chart data reaches the page via `data-chart="{{ ...|tojson }}"` canvas attributes — **no inline scripts** (CSP has no `'unsafe-inline'`).
- Channel/announcement guards: `CreateChannel` validates every member exists (no phantom members). `CreateAnnouncement` lets an `ADMIN` target any channel but restricts a `TEACHER` to channels they belong to. `PinMessage` verifies the message belongs to the given channel (`MessageRepositoryPort.find_by_id` + `channel_id` match) — anti cross-channel BOLA.

## Documentation

Developer docs live in `docs/` and are the onboarding path for new developers: `ARCHITECTURE.md` (how the project works) and `ADDING_A_FEATURE.md` (the step-by-step recipe for adding a feature). They must never drift from the code. Whenever you implement a new feature — new use case, port method, entity, route, template, migration, config/settings change, or test convention — update the relevant `docs/` file(s) in the same change. A feature is not done, and must not be committed, if the docs are stale.

## Testing notes

- `tests/conftest.py` provides an `app` fixture via `create_app(testing=True)` (in-memory SQLite, CSRF off). Create users/channels inside `with app.app_context():` and flush to get IDs before using `app.test_client()`. Shared helpers live in `tests/helpers.py` (`login`, `create_user`, `create_channel`, `add_message`, `add_announcement`, `add_notification`).
- Schema is managed by **Alembic** (`migrations/`). In dev, `create_app()` runs `alembic upgrade head` automatically on boot; `scripts/migrate.sh` is the explicit fallback. In testing, `create_app(testing=True)` still uses `db.create_all()` on the in-memory DB (Alembic can't share a `:memory:` connection), so schema changes go through a new Alembic migration for dev, not `create_all`.
- `TestingConfig` sets `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY` to `""` so tests are hermetic and never read `.env` keys or trigger web push.
- CSRF is off in `TestingConfig`; CSRF tests re-enable it per-test via `app.config["WTF_CSRF_ENABLED"] = True`. Note flashed messages and template values are HTML-escaped (apostrophes render as `&#39;`), so assert on substrings without apostrophes.
- **One login per test client**: pytest-flask pushes an autouse `test_request_context` that caches `current_user` for the whole test — chaining `login(A)` then `login(B)` does NOT actually rebind the current user (session changes, `current_user` doesn't). To act as a different user, insert the data directly via SQLAlchemy models, then do a single `login()`. See `tests/interfaces/test_messages_routes.py::test_delete_template_rejects_other_owner`.
- Real-time features (SocketIO) and web push are only exercised indirectly; the notification/message use-case tests rely on the realtime service tolerating no connected client.
- Flask ≥ 3.1.3 and Werkzeug ≥ 3.1.5 are required (`requirements.txt`) — Flask 3.1's `get_signing_serializer` reads `app.config["SECRET_KEY_FALLBACKS"]`, so the `SimpleNamespace` stubs in `tests/interfaces/test_security_hardening.py` must include `config={"SECRET_KEY_FALLBACKS": []}`.
- Push-key tests use a real 65-byte P-256 key constant; a 63-byte legacy constant will now (correctly) fail `_validate_subscription_payload`.
- `tests/interfaces/test_production_config.py` checks `ProductionConfig` cookie defaults, `APP_ENV=production` config selection, and HSTS presence/absence.
- Input validation: `RegisterUser` enforces email format + lengths (`full_name` ≤120, email ≤254, password 8–128); announcement title ≤255 / content ≤5000; channel name ≤120; message content ≤5000; message template label ≤80 / content ≤5000. New length caps must raise `ValidationError` in the use case, not in the route.
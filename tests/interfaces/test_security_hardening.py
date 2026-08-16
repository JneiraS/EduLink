from types import SimpleNamespace

from flask.sessions import SecureCookieSessionInterface

from app import _resolve_secret_key
from tests.helpers import create_user

PUBLIC_DEFAULT_SECRET = "dev-secret-change-me"


def _forge_session_cookie(secret: str, user_id: int) -> str:
    app = SimpleNamespace(secret_key=secret)
    serializer = SecureCookieSessionInterface().get_signing_serializer(app)
    return serializer.dumps({"_user_id": str(user_id), "_fresh": True})


def test_forged_cookie_with_public_default_secret_rejected(client, app):
    user_id = create_user(app, role="ADMIN", email="admin@t.local")
    client.set_cookie("session", _forge_session_cookie(PUBLIC_DEFAULT_SECRET, user_id))
    response = client.get("/")
    assert response.status_code == 302


def test_session_cookie_with_valid_secret_authenticates(client, app):
    user_id = create_user(app, role="ADMIN", email="admin2@t.local")
    client.set_cookie("session", _forge_session_cookie("test-secret", user_id))
    response = client.get("/")
    assert response.status_code == 200


def test_resolve_secret_key_generates_and_persists(monkeypatch, tmp_path):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    app = SimpleNamespace(
        config={"SECRET_KEY": None, "TESTING": False}, instance_path=str(tmp_path)
    )
    _resolve_secret_key(app)
    key = app.config["SECRET_KEY"]
    assert key and key != PUBLIC_DEFAULT_SECRET
    assert len(key) >= 32
    assert (tmp_path / "secret_key").read_text().strip() == key

    reused = SimpleNamespace(
        config={"SECRET_KEY": None, "TESTING": False}, instance_path=str(tmp_path)
    )
    _resolve_secret_key(reused)
    assert reused.config["SECRET_KEY"] == key


def test_resolve_secret_key_uses_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "correct horse battery staple")
    app = SimpleNamespace(
        config={"SECRET_KEY": None, "TESTING": False}, instance_path="/nonexistent"
    )
    _resolve_secret_key(app)
    assert app.config["SECRET_KEY"] == "correct horse battery staple"


def test_resolve_secret_key_ignores_public_default_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SECRET_KEY", PUBLIC_DEFAULT_SECRET)
    app = SimpleNamespace(
        config={"SECRET_KEY": None, "TESTING": False}, instance_path=str(tmp_path)
    )
    _resolve_secret_key(app)
    assert app.config["SECRET_KEY"] != PUBLIC_DEFAULT_SECRET


def test_login_rate_limited(client, app):
    from app.extensions import limiter

    app.config["RATE_LIMIT_ENABLED"] = True
    limiter.enabled = True
    limiter.reset()
    create_user(app, role="ADMIN", email="rl@t.local")
    for _ in range(5):
        client.post("/auth/login", data={"email": "rl@t.local", "password": "wrong"})
    response = client.post(
        "/auth/login", data={"email": "rl@t.local", "password": "secret"}
    )
    assert response.status_code == 429


def test_security_headers_present(client):
    response = client.get("/auth/login")
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self' https://cdn.socket.io https://cdn.jsdelivr.net" in csp
    assert "frame-ancestors 'none'" in csp
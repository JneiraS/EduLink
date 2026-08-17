import os

from app import create_app
from app.config.settings import (
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
)


def test_production_config_secure_cookie_defaults():
    assert ProductionConfig.SESSION_COOKIE_SECURE is True
    assert ProductionConfig.SESSION_COOKIE_HTTPONLY is True
    assert ProductionConfig.SESSION_COOKIE_SAMESITE == "Lax"
    assert ProductionConfig.PERMANENT_SESSION_LIFETIME >= 3600
    assert ProductionConfig.RATE_LIMIT_ENABLED is True


def test_development_config_keeps_http_cookie():
    assert DevelopmentConfig.SESSION_COOKIE_SECURE is False


def test_testing_config_is_insecure_cookie():
    assert TestingConfig.SESSION_COOKIE_SECURE is False


def test_create_app_production_env(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "prod-secret-test-1234")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setenv("VAPID_PUBLIC_KEY", "")
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "")
    app = create_app()
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True


def test_hsts_header_only_when_secure_cookie(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "prod-secret-test-1234")
    monkeypatch.setenv("UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setenv("VAPID_PUBLIC_KEY", "")
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "")
    app = create_app()
    client = app.test_client()
    response = client.get("/auth/login")
    assert response.headers["Strict-Transport-Security"] == (
        "max-age=31536000; includeSubDomains"
    )
    assert "Strict-Transport-Security" in response.headers


def test_hsts_absent_when_cookie_not_secure(client, app):
    assert "Strict-Transport-Security" not in client.get("/auth/login").headers
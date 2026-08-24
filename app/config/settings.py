import os


class BaseConfig:
    SECRET_KEY = None  # resolved in create_app() (see app/__init__.py)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"pdf"}
    VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
    VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
    VAPID_SUBJECT = os.getenv("VAPID_SUBJECT", "mailto:admin@edulink.local")
    INVITATION_TTL_HOURS = 72
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.1.28:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


class DevelopmentConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///edulink.db")
    RATE_LIMIT_ENABLED = True
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"


class ProductionConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///edulink.db")
    RATE_LIMIT_ENABLED = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME_SECONDS", "43200"))


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATE_LIMIT_ENABLED = False
    SESSION_COOKIE_SECURE = False
    SECRET_KEY = "test-secret"
    UPLOAD_FOLDER = "instance/uploads-test"
    # Hermetic tests: never read VAPID keys from .env, so no web push in tests.
    VAPID_PUBLIC_KEY = ""
    VAPID_PRIVATE_KEY = ""

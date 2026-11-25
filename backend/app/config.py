import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-only-secret")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-jwt-secret")
    JWT_EXPIRES = timedelta(hours=int(os.getenv("JWT_EXPIRES_HOURS", "12")))
    JWT_REMEMBER_EXPIRES = timedelta(days=30)
    MONGODB_URI = os.getenv("MONGODB_URI", "")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "smart_career_mentor")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5000")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB resume limit
    COOKIE_SECURE = os.getenv("FLASK_ENV") == "production"
    COOKIE_NAME = "scm_token"
    CSRF_COOKIE_NAME = "scm_csrf"
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_ENABLED = True
    TESTING = False


class TestConfig(Config):
    TESTING = True
    RATELIMIT_ENABLED = False
    SECRET_KEY = "test"
    JWT_SECRET_KEY = "test-jwt-secret-key-that-is-long-enough-32b"

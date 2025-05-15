import os
import uuid
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    ROOT_DIR = Path(os.path.abspath(os.path.dirname(__file__))).parent
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        SECRET_KEY = str(uuid.uuid4())
    JWT_SECRET_KEY = SECRET_KEY
    ENV = os.environ.get("ENV", "development").lower()

    CORS_HEADERS = "Content-Type"

    SESSION_TYPE = "filesystem"
    SESSION_COOKIE_SAMESITE = None
    SESSION_COOKIE_SECURE = True  # Only send cookie over HTTPS
    REMEMBER_COOKIE_SECURE = True  # Same for "remember me" cookie
    SESSION_COOKIE_HTTPONLY = True  # Prevent client-side JS access to cookie

    # Calendar JSON files directory
    CALENDAR_JSON_DIR = os.environ.get(
        "CALENDAR_JSON_DIR", os.path.join(ROOT_DIR, "calendar_data")
    )
    if not os.path.exists(CALENDAR_JSON_DIR):
        os.makedirs(CALENDAR_JSON_DIR)

    # These are in UTC
    WORK_START_HOUR = 15
    WORK_END_HOUR = 23


class DevelopmentConfig(Config):
    ENV = "development"
    DEBUG = True

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(Config.ROOT_DIR, "app.db")


class ProductionConfig(Config):
    ENV = "production"
    DEBUG = False

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(Config.ROOT_DIR, "app.db")

    CACHE_TYPE = "FileSystemCache"
    CACHE_DIR = os.path.join(os.getenv("TEMP", "/tmp"), "flask_cache")


class TestingConfig(Config):
    ENV = "testing"
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

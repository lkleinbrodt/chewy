import json
import os
import uuid
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

    SETTINGS_FILE = os.path.join(ROOT_DIR, "_settings.json")
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "w") as f:
            json.dump({}, f)

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

import json

from backend.config import Config


def get_settings():
    with open(Config.SETTINGS_FILE, "r") as f:
        return json.load(f)


def set_settings(settings):
    with open(Config.SETTINGS_FILE, "w") as f:
        json.dump(settings, f)


def get_setting(key, default=None):
    settings = get_settings()
    return settings.get(key, default)


def set_setting(key, value):
    settings = get_settings()
    settings[key] = value
    set_settings(settings)


def set_calendar_dir(calendar_dir):
    set_setting("calendar_dir", calendar_dir)


def get_calendar_dir():
    return get_setting("calendar_dir", Config.DEFAULT_CALENDAR_DIR)


def set_export_dir(export_dir_path: str):
    """Set the task export directory path in settings."""
    set_setting("task_export_dir", export_dir_path)


def get_export_dir() -> str | None:
    """Get the task export directory path from settings."""
    return get_setting("task_export_dir", Config.DEFAULT_EXPORT_DIR)

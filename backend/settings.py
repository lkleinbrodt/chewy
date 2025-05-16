import json

from backend.config import Config


def get_settings():
    with open(Config.SETTINGS_FILE, "r") as f:
        return json.load(f)


def set_settings(settings):
    with open(Config.SETTINGS_FILE, "w") as f:
        json.dump(settings, f)


def get_setting(key):
    settings = get_settings()
    return settings.get(key)


def set_setting(key, value):
    settings = get_settings()
    settings[key] = value
    set_settings(settings)


def set_calendar_dir(calendar_dir):
    set_setting("calendar_dir", calendar_dir)


def get_calendar_dir():
    return get_setting("calendar_dir")

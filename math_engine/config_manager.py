# config_manager.py
"""
Configuration management module for the Advanced Python Calculator.

Responsibilities
----------------
- Load and save persistent user settings (from `config.json`)
- Load UI string descriptions / labels (from `ui_strings.json`)
- Provide unified access to single keys or the entire config dictionary

Design Notes
------------
- Uses JSON for readability and easy manual editing by advanced users.
- Returns empty dicts `{}` or default values (0) on missing files or invalid JSON.
- Paths are resolved relative to the project root.
"""

import sys
import configparser
from pathlib import Path
import json

# Absolute paths to configuration files (relative to repository root)
config_json = Path(__file__).resolve().parent / "config.json"
ui_strings = Path(__file__).resolve().parent.parent / "ui_strings.json"


def load_setting_value(key_value):
    """Load a specific setting value or all settings from config.json.

    Parameters
    ----------
    key_value : str
        - "all" → returns the full dictionary
        - otherwise → returns a single value or 0 if not found

    Returns
    -------
    dict | any
        Dictionary of settings or individual value.
        Returns {} on read failure.
    """
    try:
        with open(config_json, 'r', encoding='utf-8') as f:
            settings_dict = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

    if key_value == "all":
        return settings_dict
    else:
        return settings_dict.get(key_value, 0)


def load_setting_description(key_value):
    """Load user-facing string descriptions from ui_strings.json.

    Typically used to populate tooltips or labels in the settings UI.

    Parameters
    ----------
    key_value : str
        - "all" → returns all UI strings
        - otherwise → returns one entry or 0 if not found
    """
    try:
        with open(ui_strings, 'r', encoding='utf-8') as f:
            settings_dict = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

    if key_value == "all":
        return settings_dict
    else:
        return settings_dict.get(key_value, 0)


def save_setting(settings_dict):
    """Persist the given settings dictionary back to config.json.

    Overwrites the existing file with pretty-printed JSON (indent=4).

    Parameters
    ----------
    settings_dict : dict
        Dictionary of settings to write.

    Returns
    -------
    dict
        The same dictionary if successful, or {} on error.
    """
    try:
        with open(config_json, 'w', encoding='utf-8') as f:
            json.dump(settings_dict, f, indent=4)
            return settings_dict
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


if __name__ == "__main__":
    """Manual test block — for standalone verification only."""
    print(load_setting_value("after_paste_enter"))

    all_settings = load_setting_value("all")
    all_settings["darkmode"] = True
    save_setting(all_settings)
    print(load_setting_value("darkmode"))

    all_settings = load_setting_value("all")
    all_settings["darkmode"] = False
    save_setting(all_settings)
    print(load_setting_value("darkmode"))
    print(load_setting_value("all"))

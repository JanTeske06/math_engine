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
from . import error as E

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


def save_setting(key_value, new_value):
    """Persist the given settings back to config.json, with type validation.

    Overwrites the existing file with pretty-printed JSON (indent=4).
    Checks if new_value matches the type of the old value.

    Parameters
    ----------
    key_value : str
        The key (setting name) to update.
    new_value : any
        The new value to assign.

    Returns
    -------
    int
        1 on success, -1 on errpr
    """

    settings = load_setting_value("all")

    # 1. VALIDATE AGAINST THE TYPE OF THE OLD VALUE
    if key_value in settings:
        old_value = settings[key_value]

        # Get the type of the old value
        expected_type = type(old_value)

        # 2. CHECK NEW VALUE TYPE AGAINST EXPECTED TYPE
        if not isinstance(new_value, expected_type):

            # SPECIAL CASE 1: Allowing bool where int is expected (e.g., 0/1 for False/True)
            if expected_type == int and isinstance(new_value, bool):
                # Allowed, as bool is a subclass of int in Python
                pass

                # SPECIAL CASE 2: Allowing int 0/1 where bool is expected
            elif expected_type == bool and isinstance(new_value, int):
                # We only permit 0 or 1, which are the numeric equivalents of bool
                if new_value != 0 and new_value != 1:
                    raise E.ConfigError(f"Type mismatch for '{key_value}'. Expected {expected_type.__name__}, got {type(new_value).__name__} ({new_value}). Only 0 or 1 allowed for boolean type.", code = "5000")


            # GENERAL TYPE MISMATCH
            else:
                raise E.ConfigError(f"Type mismatch for '{key_value}'. Expected {expected_type.__name__}, got {type(new_value).__name__}.", code = "5000")


    else:
        # If the key doesn't exist, we save the new value without type checking
        # (This allows users to add new settings if desired)
        pass

        # 3. SAVE if type check is successful

    allowed_prefix = (
        "dec:", "d:", "decimal:", "int:", "i:", "integer:", "float:", "f:",
        "bool:", "bo:", "boolean:", "hex:", "h:", "hexadecimal:",
        "str:", "s:", "string:", "bin:", "bi:", "binary:", "oc:", "o:", "octal:"
    )

    new_value_str_lower = str(new_value).lower()
    final_prefix = new_value

    prefix_found = False

    try:
        for prefix in allowed_prefix:
            if new_value_str_lower.startswith(prefix):

                prefix_found = True

                if prefix.startswith("s"):
                    final_prefix = "string:"
                elif prefix.startswith("bo"):
                    final_prefix = "boolean:"
                elif prefix.startswith("d"):
                    final_prefix = "decimal:"
                elif prefix.startswith("f"):
                    final_prefix = "float:"
                elif prefix.startswith("i"):
                    final_prefix = "int:"
                elif prefix.startswith("h"):
                    final_prefix = "hexadecimal:"
                elif prefix.startswith("bi"):
                    final_prefix = "binary:"
                elif prefix.startswith("o"):
                    final_prefix = "octal:"
                break


        if not prefix_found:
            if ":" not in new_value_str_lower:
                allowed_pure_names = {p.strip(":") for p in allowed_prefix}

                if new_value_str_lower in allowed_pure_names:
                    final_prefix = new_value_str_lower + ":"
                    prefix_found = True

        if not prefix_found:
            allowed_prefix_str = ', '.join(sorted(allowed_pure_names))  # Sortiere für Lesbarkeit
            raise E.ConfigError(f"'{new_value}' is not a recognized output format. Allowed formats: \n"
                                f"{allowed_prefix_str}", code="5002")

        settings[key_value] = final_prefix

        with open(config_json, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)
            return 1  # Success

    except Exception as e:
        raise E.ConfigError(f"Configuration saving failed: {e}", code="5002")

    settings[key_value] = final_prefix
    try:
        # Use the correct file path (config_json) and dictionary (settings)
        with open(config_json, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)
            return 1  # Success
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise E.ConfigError(f"Could not save configuration file: {e}", code = "5002")


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

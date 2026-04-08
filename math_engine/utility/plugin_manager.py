"""
Plugin loading and registration framework for math_engine.

**Status: Work in progress.**

This module provides an extensible plugin architecture that allows third-party
functions to be registered and made available in the expression parser.

Architecture:
    1. Plugins are Python files placed in the ``plugins/`` directory.
    2. Each file contains a class inheriting from :class:`BasePlugin`.
    3. The class implements ``register_function()`` returning a blueprint dict.
    4. The class implements ``execute(problem)`` for custom evaluation logic.
    5. On load, the function name is added to the tokenizer's function map.
"""

import decimal
from pathlib import Path
from abc import ABC, abstractmethod
import importlib.util
import importlib.machinery
import sys
from typing import Union, Optional
from ..utility import error as E
import inspect
from inspect import isclass

# Reference blueprint showing the expected structure of a plugin registration.
# Every plugin's ``register_function()`` must return a dict with exactly these
# five keys, in the same order and with matching value types.
function_blueprint = {
    # The function name as it appears in expressions, e.g. "ln" for ln(x).
    # Must be a string; parentheses are added automatically during registration.
    "function"              : "ln",
    # How many arguments the function accepts (non-negative integer).
    "number_of_parameters"  : 2,
    # The expected Python type for the arguments (str, Decimal, bool, int, or float).
    "type"                  : int,
    # Character used to separate multiple arguments inside the parentheses.
    # Defaults to ',' if empty/None; '(' and ')' are forbidden.
    "divided_by"            : ",",
    # A reference to the plugin class itself (must be a BasePlugin subclass).
    "implementation_class"  : "BasePlugin"
}

allowed_types = Union[str, decimal.Decimal, bool, int, float]
"""Union of all types a plugin parameter may declare."""

forbidden_division_types = ['(', ')']
"""Characters that cannot be used as argument dividers in plugin functions."""

function_register = {}
"""Global registry of loaded plugin functions.

Keys are function names with a trailing ``(`` (e.g., ``"ln("``).
Values are the validated blueprint dictionaries.
"""



class BasePlugin(ABC):
    """Abstract base class that all math_engine plugins must inherit from.

    Subclasses must implement:
        - ``register_function()``: Return a blueprint dict describing the function.
        - ``execute(problem)``:    Evaluate the custom function for a given input.
    """
    name = "BasePlugin"
    def __init__(self):
        pass

    @abstractmethod
    def register_function(self):
        """Return a function blueprint dictionary.

        The dictionary must follow this structure::

            {
                "function":             "ln",           # function name (str)
                "number_of_parameters": 2,              # param count (int)
                "type":                 int,            # expected param type
                "divided_by":           ",",            # argument separator
                "implementation_class": MyPlugin        # reference to this class
            }
        """
        pass
        # return {
        #         "function"              : "ln",             # required to be in brackets, e.g. : ln(1) and must be string
        #         "number_of_parameters"  : 2,                # Only whole numbers 0 <= allowed
        #         "type"                  : int,              # String, Decimal, Bool, int or float
        #         "divided_by"            : ",",              # Default is ',', but can be adjusted, except '(' or ')'
        #         "implementation_class"  : BasePlugin        # Name of ur Class
        #                                                 }

    @abstractmethod
    def execute(self, problem):
        """Execute the custom function for the given input.

        Args:
            problem: The argument string passed to the function at evaluation time.

        Returns:
            The computed result.
        """
        pass









def validate_registered_function(function):
    """Validate a plugin's function blueprint dictionary.

    Checks that the blueprint has the correct structure, types, and values.
    On success, registers the function in :data:`function_register`.

    Args:
        function: The blueprint dictionary returned by ``register_function()``.

    Raises:
        E.PluginError: If any validation check fails (codes ``9000``–``9011``).
    """
    # --- Rule 1: Must be a dict ---
    if type(function) != dict:
        raise E.PluginError(f"Function is not a dict '{type(function)}'", code = "9000")
    # --- Rule 2: At most 5 keys allowed ---
    elif len(function) > 5:
        raise E.PluginError(f"More than 5 keys in '{function}' registered: {len(function)}", code = "9001")
    else:
        try:
            item_list = list(function.items())

            values_to_check = list(function.values())
            keys_to_check = [item_list[i][0] for i in range(4)]

            # --- Rule 3: All blueprint keys must be strings ---
            if not all(isinstance(key, str) for key in keys_to_check):
                for i, key in enumerate(keys_to_check):
                    if not isinstance(key, str):
                        raise E.PluginError(
                            f"Key of {i + 1}. entry (Index {i}, Key: '{key}') "
                            f"MUST be a String. Received type:: {type(key).__name__}", code="9002"
                        )

            # --- Rule 4: "function" value must be a string ---
            if not isinstance(values_to_check[0], str):
                raise E.PluginError("Function name is not a String.", code = "9003")

            # --- Rule 5: "number_of_parameters" must be an int ---
            if not isinstance(values_to_check[1], int):
                raise E.PluginError(f"Invalid number of arguments type. Valid type: int"
                                    f"received type: {type(values_to_check[1])}", code = "9003")
            # --- Rule 6: "type" must be one of the allowed_types ---
            if values_to_check[2] not in allowed_types.__args__:
                raise E.PluginError(f"Type is not valid. Valid types: {allowed_types.__args__}", code="9003")

            # --- Rule 7: "divided_by" must be a string ---
            if not isinstance(values_to_check[3], str):
                raise E.PluginError(f"Invalid number of arguments type. Valid type: String"
                                    f"received type: {type(values_to_check[3])}", code="9003")

            # --- Rule 8: Default the divider to ',' if empty or None ---
            divider_value = values_to_check[3]
            if divider_value == "" or divider_value is None:
                key_to_update = list(function.keys())[3]

                function[key_to_update] = ","
            # --- Rule 9: '(' and ')' are forbidden as dividers ---
            if divider_value in forbidden_division_types:
                raise E.PluginError(
                    f"Divider '{divider_value}' is forbidden. Forbidden types: {forbidden_division_types}",
                    code="9004"
                )
            # --- Rule 10: "implementation_class" must be a class reference ---
            plugin_class_reference = values_to_check[4]
            if not isclass(plugin_class_reference):
                raise E.PluginError(
                    f"5th must be a class. Received type: {type(plugin_class_reference).__name__}",
                    code="9005")

            # --- Rule 11: The class must inherit from BasePlugin ---
            if not issubclass(plugin_class_reference, BasePlugin):
                raise E.PluginError(f"Class {plugin_class_reference.__name__} must inherit from BasePlugin.",
                                    code="9006")

        except E.PluginError as e:
            code = e.code
            message = e.message
            raise E.MathError(message=message, code=code) from e

    # Ensure the function name ends with '(' so the tokenizer can recognize
    # it as a callable (e.g. "ln" becomes "ln(").
    name = list(function.values())[0]
    if name.endswith("("):
        pass
    elif name.endswith(")"):
        raise E.PluginError("Function names cannot ned with ')'", code = "9011")
    else:
        name = name + "("
    function_register[name] = function
    print(function_register)









def find_plugins():
    """Scan the ``plugins/`` directory for plugin files and load them.

    Iterates over all ``.py`` files in the plugins folder (skipping
    ``__init__.py``), loads each module, extracts the ``BasePlugin``
    subclass, and validates its blueprint.

    Returns:
        list[dict]: A list of validated plugin blueprint dictionaries.

    Raises:
        E.PluginError: If the plugin folder is missing (code ``9011``)
            or a plugin fails to load/validate.
    """
    current_dir = Path(__file__).parent
    plugin_folder = current_dir / "plugins"
    if not plugin_folder.exists():
        raise E.PluginError(
            "Plugin folder 'plugins' not found.",
            code="9011"
        )

    found_blueprints = []

    print(f"Scanning folder: {plugin_folder.absolute()}")

    for file in plugin_folder.glob("*.py"):
        if file.name == "__init__.py":
            continue

        print(f"Plugin file discovered: {file.name}")
        try:
            plugin_blueprint = _load_module_and_extract_class(file)

            if plugin_blueprint:
                found_blueprints.append(plugin_blueprint)

        except E.PluginError as e:
            raise e

    return found_blueprints


def _load_module_and_extract_class(plugin_path: Path) -> Optional[dict]:
    """Dynamically load a plugin module and extract its ``BasePlugin`` subclass.

    Uses ``importlib`` to load the module from the given file path, then
    scans the module's members for a class that inherits from ``BasePlugin``.
    If found, instantiates it, calls ``register_function()``, and validates
    the returned blueprint.

    Args:
        plugin_path: Absolute path to the plugin ``.py`` file.

    Returns:
        dict or None: The validated blueprint dictionary, or ``None`` if no
            ``BasePlugin`` subclass was found in the module.

    Raises:
        E.PluginError: If the module fails to load (code ``9007``),
            instantiation fails (code ``9008``), or validation fails.
    """
    module_name = plugin_path.stem
    full_module_name = f"math_engine.plugins.{module_name}"
    try:
        spec = importlib.util.spec_from_file_location(full_module_name, plugin_path)
        if spec is None:
            raise ImportError(f"Could not load spec for {full_module_name}")

        module = importlib.util.module_from_spec(spec)

        module.__package__ = "math_engine.plugins"
        module.BasePlugin = BasePlugin

        sys.modules[full_module_name] = module
        spec.loader.exec_module(module)

    except Exception as e:
        error_type = type(e).__name__
        raise E.PluginError(f"Error Loading Plugin {module_name} ({error_type}): {e}", code="9007")

    # Search for the first class in the module that inherits from BasePlugin.
    PluginKlasse = None
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if obj != BasePlugin and issubclass(obj, BasePlugin):
            PluginKlasse = obj
            break

    if PluginKlasse is None:
        print(f"WARNUNG: Keine von BasePlugin abgeleitete Klasse in {module_name}.py gefunden.")
        return None

    # Instantiate the discovered plugin class and validate its blueprint.
    try:
        plugin_instanz = PluginKlasse()
    except Exception as e:
        error_type = type(e).__name__
        raise E.PluginError(f"Error instantiating {PluginKlasse.__name__} ({error_type}): {e}", code="9008")
    try:
        plugin_blueprint = plugin_instanz.register_function()
    except NotImplementedError:
        raise E.PluginError(f"Class {PluginKlasse.__name__} must implement register_function.", code="9009")
    except Exception as e:
        error_type = type(e).__name__
        raise E.PluginError(f"register_function in {PluginKlasse.__name__} raised an error ({error_type}): {e}",
                            code="9010")

    validate_registered_function(plugin_blueprint)
    return plugin_blueprint

# if __name__ == "__main__":
#     print(find_plugins())

def load_plugins():
    """Entry point for plugin loading. Calls :func:`find_plugins`."""
    find_plugins()
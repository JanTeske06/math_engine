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

# It doesnt matter how u name the key, as long it is in this order / sequence.
function_blueprint = {
    "function"              : "ln",             # required to be in brackets, e.g. : ln(1) and must be string
    "number_of_parameters"  : 2,                # Only whole numbers 0 <= allowed
    "type"                  : int,              # String, Decimal, Bool, int or float
    "divided_by"            : ",",              # Default is ',', but can be adjusted, except '(' or ')'
    "implementation_class"  : "BasePlugin"
}

allowed_types = Union[str, decimal.Decimal, bool, int, float]
forbidden_division_types = ['(', ')']

function_register = {}



class BasePlugin(ABC):
    name = "BasePlugin"
    def __init__(self):
        pass

    @abstractmethod
    def register_function(self):
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
        pass









def validate_registered_function(function):
    if type(function) != dict:
        raise E.PluginError(f"Function is not a dict '{type(function)}'", code = "9000")
    elif len(function) > 5:
        raise E.PluginError(f"More than 5 keys in '{function}' registered: {len(function)}", code = "9001")
    else:
        try:
            item_list = list(function.items())

            values_to_check = list(function.values())
            keys_to_check = [item_list[i][0] for i in range(4)]

            if not all(isinstance(key, str) for key in keys_to_check):
                for i, key in enumerate(keys_to_check):
                    if not isinstance(key, str):
                        raise E.PluginError(
                            f"Key of {i + 1}. entry (Index {i}, Key: '{key}') "
                            f"MUST be a String. Received type:: {type(key).__name__}", code="9002"
                        )

            if not isinstance(values_to_check[0], str):
                raise E.PluginError("Function name is not a String.", code = "9003")

            if not isinstance(values_to_check[1], int):
                raise E.PluginError(f"Invalid number of arguments type. Valid type: int"
                                    f"received type: {type(values_to_check[1])}", code = "9003")
            if values_to_check[2] not in allowed_types.__args__:
                raise E.PluginError(f"Type is not valid. Valid types: {allowed_types.__args__}", code="9003")

            if not isinstance(values_to_check[3], str):
                raise E.PluginError(f"Invalid number of arguments type. Valid type: String"
                                    f"received type: {type(values_to_check[3])}", code="9003")

            divider_value = values_to_check[3]
            if divider_value == "" or divider_value is None:
                key_to_update = list(function.keys())[3]

                function[key_to_update] = ","
            if divider_value in forbidden_division_types:
                raise E.PluginError(
                    f"Divider '{divider_value}' is forbidden. Forbidden types: {forbidden_division_types}",
                    code="9004"
                )
            plugin_class_reference = values_to_check[4]
            if not isclass(plugin_class_reference):
                raise E.PluginError(
                    f"5th must be a class. Received type: {type(plugin_class_reference).__name__}",
                    code="9005")

            if not issubclass(plugin_class_reference, BasePlugin):
                raise E.PluginError(f"Class {plugin_class_reference.__name__} must inherit from BasePlugin.",
                                    code="9006")

        except E.PluginError as e:
            code = e.code
            message = e.message
            raise E.MathError(message=message, code=code) from e
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

    PluginKlasse = None
    # 3. Klasse finden (ohne sofortige Beendigung)
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if obj != BasePlugin and issubclass(obj, BasePlugin):
            PluginKlasse = obj
            break  # Nur die Schleife beenden

    if PluginKlasse is None:
        print(f"WARNUNG: Keine von BasePlugin abgeleitete Klasse in {module_name}.py gefunden.")
        return None

    # 4. Instanziierung und Validierung
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
    find_plugins()
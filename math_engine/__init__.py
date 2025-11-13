import math_engine.calculator
from . import calculator
from . import config_manager as config_manager
from . import error as E

from typing import Any, Mapping, Optional
from typing import Union
from typing import Any, Mapping

memory = {}

def set_memory(key_value: str, value:str):
    global memory
    memory[key_value] = value

def delete_memory(key_value: str):
    global memory
    try:
        memory.pop(key_value)
    except Exception as e:
        raise E.SyntaxError(f"Entry {key_value} does not exist.", code = "4000")

def show_memory():
    return memory


def change_setting(setting: str, new_value: Union[int, bool]):
    saved_settings = config_manager.save_setting(setting, new_value)

    if saved_settings != -1:
        return 1
    elif saved_settings == -1:
        return -1

def load_all_settings():
    settings = config_manager.load_setting_value("all")
    return settings

def load_one_setting(setting):
    settings = config_manager.load_setting_value(setting)
    return settings


def evaluate(expr: str,
             variables: Optional[Mapping[str, Any]] = None,
             **kwvars: Any) -> Any:
    explanation = False
    if variables is None:
        merged = dict(kwvars)
    else:
        merged = dict(variables)
        merged.update(kwvars)
    global memory
    merged = dict(list(memory.items()) + list(merged.items()))

    result = calculator.calculate(expr, merged)

    if isinstance(result, E.MathError):
        raise result

    return result



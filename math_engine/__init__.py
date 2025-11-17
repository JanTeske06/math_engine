from email import message_from_string

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
        if key_value == "all":
            memory = {}
        else:
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

def load_preset(settings: dict):
    current = config_manager.load_setting_value("all")
    unknown = [k for k in settings.keys() if k not in current]
    if unknown:
        raise E.SyntaxError(f"Unknown settings in preset: {unknown}", code="5003")
    missing = [k for k in current.keys() if k not in settings]
    if missing:
        raise E.SyntaxError(f"Missing settings in preset: {missing}", code="5004")
    current.update(settings)
    config_manager.load_preset(current)
    return 1



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

    result = calculator.calculate(expr, merged,1) # 0 = Validate, 1 = Calculate

    if isinstance(result, E.MathError):
        raise result

    return result


def validate(expr: str,
             variables: Optional[Mapping[str, Any]] = None,
             **kwvars: Any) -> Any:
    try:
        explanation = False
        if variables is None:
            merged = dict(kwvars)
        else:
            merged = dict(variables)
            merged.update(kwvars)
        global memory
        merged = dict(list(memory.items()) + list(merged.items()))

        result = calculator.calculate(expr, merged, 0) # 0 = Validate, 1 = Calculate
        return result

    except E.MathError as e:
        Errormessage = "Errormessage: "
        code = "Code: "
        Equation = "Equation: "
        positon = e.position




        print(Errormessage + str(e.message))
        print(code + str(e.code))
        if positon != -1:
            calc_equation = str(e.equation)
            print(Equation +calc_equation[:positon]+ "\033[4m" + calc_equation[positon] + "\033[0m"+ calc_equation[positon+1:])

            print((positon+len(Equation)) * " " + "^ HERE IS THE PROBLEM (Position: " + str(positon) + ")")
        else:
            print(Equation + str(e.equation))



#
# if __name__ == '__main__':
#     #problem = ("x+1", x=5)
#     print(math_engine.evaluate("x += 5", x=10))
#     config_manager.reset_settings()
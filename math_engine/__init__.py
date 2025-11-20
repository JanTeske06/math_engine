from email import message_from_string

import math_engine.calculator
from . import calculator
from . import config_manager as config_manager
from . import error as E
from . import plugin_manager
from typing import Any, Mapping, Optional
from typing import Union
from typing import Any, Mapping
__version__ = "0.6.3"
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
             is_cli: bool = False,
             **kwvars: Any) -> Any:
    if variables is None:
        merged = dict(kwvars)
    else:
        merged = dict(variables)
        merged.update(kwvars)
    global memory
    merged = dict(list(memory.items()) + list(merged.items()))
    settings = load_all_settings()


    if settings["readable_error"] == False:
        result = calculator.calculate(expr, merged,1) # 0 = Validate, 1 = Calculate
        return result


    elif settings["readable_error"]== True:
        result = -1
        try:
            result = calculator.calculate(expr, merged, 1)  # 0 = Validate, 1 = Calculate
            if isinstance(result, E.MathError):
                raise result

            return result
        except E.MathError as e:
            Errormessage = "Errormessage: "
            code = "Code: "
            Equation = "Equation: "
            positon_start = e.position_start
            positon_end = e.position_end

            if is_cli:
                if positon_start != -1:
                    if positon_end == -1:
                        positon_end = positon_start
                    if positon_start != positon_end:
                        print((round((positon_end - positon_start) / 2) + positon_start + 4) * " " + "^ HERE IS THE PROBLEM (Position: " + str(positon_start) + " - " + str(
                            positon_end) + ")")
                    else:
                        print((positon_start + 4) * " " + "^ HERE IS THE PROBLEM (Position: " + str(
                            positon_start) + ")")
                    print(code + str(e.code))
                    print(Errormessage + str(e.message))
                    print(" ")
                else:
                    print(code + str(e.code))
                    print(Errormessage + str(e.message))
                    print(Equation + str(e.equation))
                    print(" ")
            if is_cli == False:
                print(Errormessage + str(e.message))
                print(code + str(e.code))
                if positon_start != -1:
                    if positon_end == -1:
                        positon_end = positon_start
                    calc_equation = str(e.equation)
                    print(
                        Equation + calc_equation[:positon_start] + "\033[4m" + calc_equation[
                                                                               positon_start:positon_end + 1] + "\033[0m" + calc_equation[
                                                                                                                            positon_end + 1:]
                    )
                    if positon_start != positon_end:
                        print((round((positon_end - positon_start) / 2) + positon_start + len(
                            Equation)) * " " + "^ HERE IS THE PROBLEM (Position: " + str(positon_start) + " - " + str(
                            positon_end) + ")")
                    else:
                        print((positon_start + len(Equation)) * " " + "^ HERE IS THE PROBLEM (Position: " + str(
                            positon_start) + ")")
                else:
                    print(Equation + str(e.equation))



def validate(expr: str,
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
    result = -1
    try:
        result = calculator.calculate(expr, merged, 0)  # 0 = Validate, 1 = Calculate
        return result

    except E.MathError as e:
        Errormessage = "Errormessage: "
        code = "Code: "
        Equation = "Equation: "
        positon_start = e.position_start
        positon_end = e.position_end

        print(Errormessage + str(e.message))
        print(code + str(e.code))
        if positon_start != -1:
            if positon_end == -1:
                positon_end = positon_start
            calc_equation = str(e.equation)
            print(
                Equation + calc_equation[:positon_start] + "\033[4m" + calc_equation[
                                                                       positon_start:positon_end + 1] + "\033[0m" + calc_equation[
                                                                                                                    positon_end + 1:]
            )
            if positon_start != positon_end:
                print((round((positon_end - positon_start) / 2) + positon_start + len(
                    Equation)) * " " + "^ HERE IS THE PROBLEM (Position: " + str(positon_start) + " - " + str(
                    positon_end) + ")")
            else:
                print((positon_start + len(Equation)) * " " + "^ HERE IS THE PROBLEM (Position: " + str(
                    positon_start) + ")")
        else:
            print(Equation + str(e.equation))



def reset_settings():
    config_manager.reset_settings()


if __name__ == '__main__':
    plugin_manager.load_plugins()
    print(evaluate("ln(3)"))
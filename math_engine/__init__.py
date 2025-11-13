from . import calculator
from . import config_manager as config_manager
from . import error as E


from typing import Union

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

def evaluate(problem: str,  custom_variables: Union[dict, None] = None):
    if custom_variables is None:
        custom_variables = {}
    result= calculator.calculate(problem, custom_variables)
    if isinstance(result, E.MathError):
        error_obj = result
        error_code = error_obj.code
        additional_info = f"Details: {error_obj.message}\nEquation: {error_obj.equation}"
        return E.MathError
    return result

def main():
    print(evaluate("2+2"))


if __name__ == "__main__":
    print(evaluate("2+2-level+pi", {"level": 1}))


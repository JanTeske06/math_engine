"""
math_engine — A fast, safe, and configurable mathematical expression evaluator.

This module is the public API surface for the math_engine package. It exposes
high-level functions for evaluating expressions, managing settings, and working
with an in-memory variable store.

Pipeline overview:
    1. Tokenizer  — converts raw input strings into token lists
    2. Parser     — builds an Abstract Syntax Tree (recursive descent)
    3. Evaluator  — numeric evaluation or linear equation solving
    4. Formatter  — renders results in the requested output type

Usage::

    import math_engine

    math_engine.evaluate("2 + 3")              # Decimal('5')
    math_engine.evaluate("hex: 255")            # '0xff'
    math_engine.evaluate("x + 3 = 10")          # Decimal('7')
    math_engine.evaluate("x + 1", x=4)          # Decimal('5')
"""

from . import calculator
from .calculator import ScientificEngine
from .utility import config_manager as config_manager
from .utility import plugin_manager, error as E
from.calculator.calculator import calculate
from .utility import config_manager as config_manager
from typing import Optional
from typing import Union
from typing import Any, Mapping

__version__ = "0.6.6"

# ---------------------------------------------------------------------------
# In-memory variable store
# ---------------------------------------------------------------------------
# Variables stored here are automatically merged into every ``evaluate()``
# call.  Keyword arguments passed directly to ``evaluate()`` take precedence
# over memory entries with the same key.
memory = {}

def set_memory(key_value: str, value:str):
    """Store a key-value pair in the global in-memory variable store.

    Memory variables are automatically included in the evaluation context
    for all subsequent ``evaluate()`` calls.

    Args:
        key_value: The variable name to store (used as identifier in expressions).
        value:     The value to associate with the key.
    """
    global memory
    memory[key_value] = value

def delete_memory(key_value: str):
    """Remove a variable from the in-memory store.

    Args:
        key_value: The key to remove. Pass ``"all"`` to clear the entire store.

    Raises:
        E.SyntaxError: If the key does not exist in memory (code ``4000``).
    """
    global memory
    try:
        if key_value == "all":
            memory = {}
        else:
            memory.pop(key_value)
    except Exception as e:
        raise E.SyntaxError(f"Entry {key_value} does not exist.", code = "4000")

def show_memory():
    """Return the current contents of the in-memory variable store.

    Returns:
        dict: A dictionary mapping variable names to their stored values.
    """
    return memory


def change_setting(setting: str, new_value: Union[int, bool]):
    """Modify a single configuration setting and persist it to disk.

    The new value must match the type of the existing setting (with special
    handling for bool/int interoperability).

    Args:
        setting:   The setting key name (e.g., ``"decimal_places"``).
        new_value: The new value to assign.

    Returns:
        int: ``1`` on success, ``-1`` on failure.
    """
    saved_settings = config_manager.save_setting(setting, new_value)

    if saved_settings != -1:
        return 1
    elif saved_settings == -1:
        return -1

def load_preset(settings: dict):
    """Replace all settings at once with a complete settings dictionary.

    The dictionary must contain exactly the same keys as the current
    configuration — no more, no fewer.

    Args:
        settings: A complete settings dictionary (all keys required).

    Returns:
        int: ``1`` on success.

    Raises:
        E.SyntaxError: If the dictionary contains unknown keys (code ``5003``)
                       or is missing required keys (code ``5004``).
    """
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
    """Return the complete current settings dictionary.

    Returns:
        dict: All configuration key-value pairs.
    """
    settings =  config_manager.load_setting_value("all")
    return settings

def load_one_setting(setting):
    """Return the value of a single configuration setting.

    Args:
        setting: The setting key name.

    Returns:
        The setting value, or ``0`` if the key does not exist.
    """
    settings = config_manager.load_setting_value(setting)
    return settings

def evaluate(expr: str,
             variables: Optional[Mapping[str, Any]] = None,
             is_cli: bool = False,
             **kwvars: Any) -> Any:
    """Evaluate a mathematical expression and return the typed result.

    This is the primary entry point for the library. The expression is
    tokenized, parsed into an AST, evaluated (or solved if it is a linear
    equation), and the result is formatted according to the active settings
    and any output prefix present in the expression.

    Variables can be supplied either as a mapping or as keyword arguments.
    Keyword arguments take precedence over the mapping, and both take
    precedence over values stored in the global memory.

    Args:
        expr:      The expression string (e.g., ``"2 + 3"``, ``"hex: 255"``).
        variables: Optional variable mapping (e.g., ``{"x": 5}``).
        is_cli:    When ``True``, error diagnostics use CLI-style formatting
                   (position pointer above the expression).
        **kwvars:  Additional variables as keyword arguments.

    Returns:
        The evaluation result. The concrete type depends on the expression
        and the active output prefix:

        - ``Decimal`` — default numeric results
        - ``int``     — with ``int:`` prefix
        - ``float``   — with ``float:`` prefix
        - ``bool``    — with ``bool:`` prefix or equality expressions
        - ``str``     — with ``str:``, ``hex:``, ``bin:``, ``oct:`` prefixes
        - ``None``    — when ``readable_error=True`` and an error occurred

    Raises:
        E.MathError: (or a subclass) when ``readable_error=False`` and the
            expression is invalid or cannot be evaluated.
    """
    # Merge variable sources: memory < variables dict < keyword args
    if variables is None:
        merged = dict(kwvars)
    else:
        merged = dict(variables)
        merged.update(kwvars)
    global memory
    merged = dict(list(memory.items()) + list(merged.items()))
    settings = load_all_settings()

    # --- Path 1: Exception mode (readable_error=False) ---
    # Exceptions propagate directly to the caller.
    if settings["readable_error"] == False:
        result = calculate(expr, merged,1) # 0 = Validate, 1 = Calculate
        return result

    # --- Path 2: Visual diagnostics mode (readable_error=True) ---
    # Errors are caught, a human-readable diagnostic is printed to stdout,
    # and the function returns None.
    elif settings["readable_error"]== True:
        result = -1
        try:
            result = calculate(expr, merged, 1)  # 0 = Validate, 1 = Calculate
            if isinstance(result, E.MathError):
                raise result

            return result
        except E.MathError as e:
            # Labels for the diagnostic output
            Errormessage = "Errormessage: "
            code = "Code: "
            Equation = "Equation: "
            positon_start = e.position_start
            positon_end = e.position_end

            # --- CLI-style output: pointer appears above the expression ---
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

            # --- Library-style output: underlined error segment in equation ---
            if is_cli == False:
                print(Errormessage + str(e.message))
                print(code + str(e.code))
                if positon_start != -1:
                    if positon_end == -1:
                        positon_end = positon_start
                    calc_equation = str(e.equation)
                    # Underline the problematic segment using ANSI escape codes
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
    """Parse and validate an expression without performing full evaluation.

    Internally calls the calculator with ``validate=0``, which builds the
    AST but skips the final numeric evaluation for pure expressions.  This
    is useful for checking whether an expression is syntactically valid.

    On error, a visual diagnostic is always printed to stdout (regardless
    of the ``readable_error`` setting).

    Args:
        expr:      The expression string to validate.
        variables: Optional variable mapping.
        **kwvars:  Additional variables as keyword arguments.

    Returns:
        The AST tree on success, or ``None`` if an error was caught.
    """
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
        result = calculate(expr, merged, 0)  # 0 = Validate, 1 = Calculate
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
    """Reset all settings to their factory defaults.

    Overwrites the ``config.json`` file with the hardcoded default values.
    """
    config_manager.reset_settings()


if __name__ == '__main__':
    #plugin_manager.load_plugins()
    print(evaluate("1 + 1"))
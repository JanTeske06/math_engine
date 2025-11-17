from decimal import Decimal
import inspect
from . import error as E
# -----------------------------
# Utilities / small helpers
# -----------------------------

def boolean(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (str, Decimal, int)):
        if value == "True":
            return True
        elif value == "False":
            return False
        elif value == "1" or int(value) == 1:
            return True
        elif value == "0"or int(value) == 1:
            return False
        raise E.ConversionError("Couldnt convert type to bool", code="8003")
    raise E.ConversionError("Couldnt convert type to bool", code="8003")


def isDecimal(value):
    if isinstance(value, Decimal):
        return True
    try:
        Decimal(value)
        return True
    except Exception as e:
        return False


def get_line_number():
    """Return the caller line number (small debug helper)."""
    return inspect.currentframe().f_back.f_lineno


def isInt(number_str):
    """Return True if the given string can be parsed as int; else False."""
    try:
        x = int(number_str)
        return True
    except ValueError:
        return False


def isfloat(number_str):
    """Return True if the given string can be parsed as float; else False.
    Note: tokenization may probe with float; evaluation uses Decimal.
    """
    try:
        x = float(number_str)
        return True
    except ValueError:
        return False


def isScOp(token):
    """Return index of a known scientific operation or -1 if unknown."""
    try:
        from .calculator import Science_Operations
        return Science_Operations.index(token)
    except ValueError:
        return -1


def isOp(token):
    """Return index of a known basic operator or -1 if unknown."""
    try:
        from .calculator import Operations
        return Operations.index(token)
    except ValueError:
        return -1


def isolate_bracket(problem, start_pos):
    """Return substring from the opening '(' at/after start_pos up to its matching ')'.

    This walks forward and counts parentheses depth; raises on missing '('.
    Returns:
        (substring_including_brackets, position_after_closing_paren)
    """
    start = start_pos
    start_klammer_index = problem.find('(', start)
    if start_klammer_index == -1:
        raise E.SyntaxError(f"Multiple missing opening parentheses after function name.", code="3000")
    b = start_klammer_index + 1
    bracket_count = 1
    while bracket_count != 0 and b < len(problem):
        if problem[b] == '(':
            bracket_count += 1
        elif problem[b] == ')':
            bracket_count -= 1
        b += 1
    result = problem[start:b]
    return (result, b)
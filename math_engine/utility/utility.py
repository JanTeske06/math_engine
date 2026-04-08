"""Small helper utilities shared across the math_engine package.

Provides lightweight type-checking and parsing probe functions (``isInt``,
``isfloat``, ``isDecimal``, ``boolean``), operator membership lookups
(``isOp``, ``isScOp``), and a parenthesis isolation helper
(``isolate_bracket``) used by the tokenizer and scientific engine.

All functions are intentionally small and side-effect-free so they can be
called freely during tokenization and evaluation without performance
concerns.
"""

from decimal import Decimal
import inspect
from . import error as E

# ---------------------------------------------------------------------------
# Type conversion helpers
# ---------------------------------------------------------------------------

def boolean(value):
    """Convert a value to a Python ``bool``.

    Accepted truthy representations: ``True``, ``"True"``, ``"1"``, or any
    numeric value whose ``int()`` equals ``1``.
    Accepted falsy representations: ``False``, ``"False"``, ``"0"``, or any
    numeric value whose ``int()`` equals ``0``.

    Args:
        value: The value to convert.  Must be ``bool``, ``str``,
            ``Decimal``, or ``int``.

    Returns:
        bool: The converted boolean.

    Raises:
        E.ConversionError: If *value* is an unsupported type or does not
            match any recognised boolean representation (code ``8003``).
    """
    # Fast path: already a bool
    if isinstance(value, bool):
        return value
    if isinstance(value, (str, Decimal, int)):
        # Check canonical string representations first
        if value == "True":
            return True
        elif value == "False":
            return False
        # Fall back to numeric comparison via int()
        elif value == "1" or int(value) == 1:
            return True
        elif value == "0"or int(value) == 1:
            return False
        raise E.ConversionError("Couldnt convert type to bool", code="8003")
    # Unsupported type (list, dict, etc.)
    raise E.ConversionError("Couldnt convert type to bool", code="8003")


def isDecimal(value):
    """Return ``True`` if *value* is or can be parsed as a ``Decimal``.

    Args:
        value: Any value to test.

    Returns:
        bool: ``True`` if conversion to ``Decimal`` succeeds.
    """
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
    """Check whether *number_str* can be parsed as a Python ``int``.

    This is a non-throwing probe: it never raises, even for ``None`` or
    non-numeric strings.

    Args:
        number_str: The string (or other value) to test.

    Returns:
        bool: ``True`` if ``int(number_str)`` would succeed, ``False``
        otherwise.
    """
    try:
        x = int(number_str)
        return True
    except ValueError:
        return False


def isfloat(number_str):
    """Check whether *number_str* can be parsed as a Python ``float``.

    Used as a quick numeric probe during tokenization.  Note that the
    calculator itself works with ``Decimal`` for precision; this helper is
    only for lightweight membership tests.

    Args:
        number_str: The string (or other value) to test.

    Returns:
        bool: ``True`` if ``float(number_str)`` would succeed, ``False``
        otherwise.
    """
    try:
        x = float(number_str)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Operator / function membership lookups
# ---------------------------------------------------------------------------
# These use deferred imports to avoid circular dependency with calculator.py.

def isScOp(token):
    """Return the index of *token* in the ``Science_Operations`` list, or ``-1``.

    Uses a deferred import from ``calculator.calculator`` to avoid circular
    dependency at module load time.
    """
    try:
        from ..calculator.calculator import Science_Operations
        return Science_Operations.index(token)
    except ValueError:
        return -1


def isOp(token):
    """Return the index of *token* in the ``Operations`` list, or ``-1``.

    Uses a deferred import from ``calculator.calculator`` to avoid circular
    dependency at module load time.
    """
    try:
        from ..calculator.calculator import Operations
        return Operations.index(token)
    except ValueError:
        return -1


# ---------------------------------------------------------------------------
# Bracket isolation
# ---------------------------------------------------------------------------

def isolate_bracket(problem, start_pos):
    """Extract the substring from the opening ``(`` at or after *start_pos* up to its matching ``)``.

    The function searches forward from *start_pos* for the first ``(``,
    then walks character-by-character, tracking nesting depth.  When the
    depth returns to zero the matching ``)`` has been found.

    Args:
        problem:   The full expression string.
        start_pos: Index at which to begin scanning for ``(``.

    Returns:
        tuple[str, int]: A 2-tuple of
            - the substring ``problem[start_pos : end]`` (inclusive of both
              parentheses), and
            - the index immediately after the closing ``)``.

    Raises:
        E.SyntaxError: If no ``(`` exists at or after *start_pos*
            (code ``3000``).
    """
    start = start_pos
    # Locate the opening parenthesis
    start_klammer_index = problem.find('(', start)
    if start_klammer_index == -1:
        raise E.SyntaxError(f"Multiple missing opening parentheses after function name.", code="3000")
    # Walk forward, tracking nesting depth
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
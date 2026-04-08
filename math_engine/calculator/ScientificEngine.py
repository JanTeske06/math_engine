"""
Lightweight scientific function evaluation layer for math_engine.

This module provides numeric evaluators for mathematical constants and
functions used by the expression parser:

- ``isPi()``              — returns the value of pi
- ``isSCT()``             — evaluates sin, cos, tan (with optional degree mode)
- ``isLog()``             — evaluates natural log or log with arbitrary base
- ``isE()``               — evaluates e^x (exponential function)
- ``isRoot()``            — evaluates square root
- ``unknown_function()``  — dispatcher that routes a string to the correct evaluator

All functions accept string inputs of the form ``"sin(1.5)"`` or ``"log(10,2)"``
and return a ``float`` result, ``False`` (not applicable), or an ``"ERROR:..."``
string for handled failures.

The global :data:`degree_setting_sincostan` controls whether trigonometric
functions interpret their arguments as radians (``0``) or degrees (``1``).
"""

import math


# 0 = interpret sin/cos/tan input as radians; 1 = interpret as degrees
degree_setting_sincostan = 0


def isPi(problem):
    """Return math.pi if input denotes π/pi; otherwise False.

    Examples
    --------
    >>> isPi("π")
    3.141592653589793
    >>> isPi("pi")
    3.141592653589793
    >>> isPi("PI")
    3.141592653589793
    >>> isPi("tau")
    False
    """
    if problem == "π" or problem.lower() == "pi":
        return math.pi
    else:
        return False


def isSCT(problem):  # Sin / Cos / Tan
    """Evaluate sin/cos/tan for the numeric content between parentheses.

    Behavior
    --------
    - Detects "sin(", "cos(", or "tan(".
    - Extracts the substring between the first '(' and the first ')'.
    - Interprets the argument in degrees if `degree_setting_sincostan == 1`,
      otherwise in radians.
    - Returns a float result or prints an error hint and falls through.

    Returns
    -------
    float | False
    """
    if "sin" in problem or "cos" in problem or "tan" in problem:
        start_index = problem.find('(')
        end_index = problem.find(')')

        # For all three functions, the number extraction is identical:
        #   substring = problem[start_index+1 : end_index]
        # We keep the repeated code blocks as-is to avoid logic changes.
        if "sin" in problem:
            clean_number = float(problem[start_index + 1: end_index])
            if degree_setting_sincostan == 1:
                clean_number = math.radians(clean_number)
            return math.sin(clean_number)

        elif "cos" in problem:
            clean_number = float(problem[start_index + 1: end_index])
            if degree_setting_sincostan == 1:
                clean_number = math.radians(clean_number)
            return math.cos(clean_number)

        elif "tan" in problem:
            clean_number = float(problem[start_index + 1: end_index])
            if degree_setting_sincostan == 1:
                clean_number = math.radians(clean_number)
            return math.tan(clean_number)

        else:
            # Reached only if one of the substrings matched above but none of the
            # specific branches executed; kept for completeness.
            print("Error. Sin/Cos/tan was detected but could not be assigned.")
    else:
        return False


def isLog(problem):
    """Evaluate natural log or log with base from a 'log(...)' string.

    Accepted forms
    --------------
    - "log(x)"        -> math.log(x)         (natural log)
    - "log(x, b)"     -> math.log(x, b)      (log base b)

    Returns
    -------
    float | str | False
        - float result on success
        - error string starting with "ERROR:" on invalid input
        - False if input does not contain 'log'
    """
    if "log" in problem:
        start_index = problem.find('(')
        end_index = problem.find(')')

        # Basic structural validation for parentheses
        if start_index == -1 or end_index == -1 or start_index >= end_index:
            return "ERROR: Logarithm syntax."

        content = problem[start_index + 1: end_index]

        number = 0.0
        base = 0.0
        ergebnis = "ERROR: Unknown logarithm error."

        try:
            # Optional base via comma separation: log(number, base)
            if "," in content:
                number_str, base_str = content.split(',', 1)
                number = float(number_str.strip())
                base = float(base_str.strip())
            else:
                number = float(content.strip())
                base = 0.0

            # Dispatch to math.log
            if base == 0.0:
                ergebnis = math.log(number)
            else:
                ergebnis = math.log(number, base)

        except ValueError:
            # Non-numeric input, invalid base, negative numbers, etc.
            return "ERROR: Invalid number or base in logarithm."
        except Exception as e:
            # Any other runtime error is returned as a plain string
            return f"ERROR: Logarithm calculation: {e}"

        return ergebnis
    else:
        return False


def isE(problem):
    """Evaluate the exponential function ``e^(x)`` from an ``"e(...)"`` string.

    The function checks whether *problem* contains the character ``"e"``.
    If so, it extracts the numeric substring between the first ``"("`` and
    the first ``")"`` and returns ``math.exp(x)``  (i.e. ``e`` raised to
    that power).

    Parameters
    ----------
    problem : str
        A string such as ``"e(2)"`` or ``"e^(3.5)"``.

    Returns
    -------
    float | False
        The computed ``e^x`` value, or ``False`` if the string does not
        contain ``"e"``.
    """
    if "e" in problem:
        # Locate the parenthesized argument
        start_index = problem.find('(')
        end_index = problem.find(')')

        # Extract the exponent between the parentheses and compute e^x
        clean_number = problem[start_index + 1: end_index]
        ergebnis = math.exp(float(clean_number))
        return ergebnis
    else:
        return False


def isRoot(problem):
    r"""Evaluate the square root from a string containing the radical sign.

    The function checks whether *problem* contains the Unicode radical
    character (U+221A).  If so, it extracts the numeric substring between
    the first ``(`` and the first ``)`` and returns ``math.sqrt(x)``.

    Parameters
    ----------
    problem : str
        A string such as ``"\u221a(9)"`` or ``"sqrt(16)"``.

    Returns
    -------
    float | False
        The computed square root, or ``False`` if the string does not
        contain the radical character.
    """
    if "√" in problem:
        # Locate the parenthesized argument
        start_index = problem.find('(')
        end_index = problem.find(')')

        # Extract the radicand and compute its square root
        clean_number = problem[start_index + 1: end_index]
        ergebnis = math.sqrt(float(clean_number))
        return ergebnis
    else:
        return False


def unknown_function(received_string):
    """Dispatch a received function string to the matching evaluator.

    This acts as the single entry point for all scientific-function
    evaluation.  It inspects *received_string* for known keywords and
    delegates to the appropriate evaluator function.

    The dispatch order matters: more specific checks (e.g. ``"sin"``,
    ``"log"``) are tested before the generic ``"e"`` check so that
    strings like ``"sine"`` do not accidentally match ``isE()``.

    Supported patterns
    ------------------
    - ``"pi"`` / ``"PI"`` / the Unicode character pi -- delegates to :func:`isPi`
    - ``"sin(...)"`` / ``"cos(...)"`` / ``"tan(...)"`` -- delegates to :func:`isSCT`
    - ``"log(...)"`` or ``"log(x, b)"`` -- delegates to :func:`isLog`
    - ``"sqrt(...)"`` or the radical character -- delegates to :func:`isRoot`
    - ``"e(...)"`` -- delegates to :func:`isE`

    Parameters
    ----------
    received_string : str
        The raw function string extracted by the tokenizer.

    Returns
    -------
    float | bool | str
        - Numeric ``float`` on successful evaluation.
        - ``False`` if the operation cannot be determined.
        - An ``"ERROR: ..."`` string for handled errors (e.g., invalid
          logarithm input).
    """
    # --- Dispatch chain (order is significant) ---

    # 1. Pi constant -- exact match on the symbol or the word
    if received_string == "π" or received_string.lower() == "pi":
        ergebnis = isPi()

    # 2. Trigonometric functions
    elif "sin" in received_string or "cos" in received_string or "tan" in received_string:
        ergebnis = isSCT(received_string)

    # 3. Logarithm (natural or with base)
    elif "log" in received_string:
        ergebnis = isLog(received_string)

    # 4. Square root (radical character)
    elif "√" in received_string:
        ergebnis = isRoot(received_string)

    # 5. Exponential -- checked last because "e" is a very common
    #    substring and would match prematurely if tested earlier
    elif "e" in received_string:
        ergebnis = isE(received_string)

    else:
        ergebnis = False

    return  ergebnis




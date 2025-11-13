# ScientificEngine
"""""
Lightweight scientific function layer used by the MathEngine.

Responsibilities
----------------
- Provide numeric results for:
  - π (pi) via `isPi`
  - sin/cos/tan (optionally in degrees) via `isSCT`
  - logarithms (natural or with base) via `isLog`
  - e^x via `isE`
  - square root via `isRoot`
- Offer a single dispatch entry `unknown_function(...)` used by MathEngine.

Notes
-----
- All functions return either a numeric result (float) or `False`/error-string
  to indicate "not applicable" or a handled error.
- Degree handling for sin/cos/tan is controlled by the global
  `degree_setting_sincostan` (0 = radians, 1 = degrees).
- This module intentionally keeps parsing *very* simple: it expects inputs like
  "sin(1.2)" or "log(10, 2)". Validation is minimal by design.
"""""

import math


# 0 = interpret sin/cos/tan input as radians; 1 = interpret as degrees
degree_setting_sincostan = 0  # 0 = number, 1 = degrees


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
    """Evaluate e^(x) from an 'e(... )' string.

    Returns
    -------
    float | False
        float result if input contains 'e', else False
    """
    if "e" in problem:
        start_index = problem.find('(')
        end_index = problem.find(')')

        clean_number = problem[start_index + 1: end_index]
        ergebnis = math.exp(float(clean_number))
        return ergebnis
    else:
        return False


def isRoot(problem):
    """Evaluate square root from a '√(... )' string.

    Returns
    -------
    float | False
        float result if input contains '√', else False
    """
    if "√" in problem:
        start_index = problem.find('(')
        end_index = problem.find(')')

        clean_number = problem[start_index + 1: end_index]
        ergebnis = math.sqrt(float(clean_number))
        return ergebnis
    else:
        return False


def test_main():
    """Very simple console tester for this module (manual ad-hoc checks).

    Note
    ----
    - Diese Funktion ist nur für manuelle Tests gedacht.
    - Es gibt hier bewusst keine Robustheit gegen fehlerhafte Eingaben.
    - Aufruf erwartet Strings wie: "sin(1.2)", "log(10, 2)", "√(9)", "e(1)".
    """
    print("Enter the problem: ")
    received_string = input()

    # Hinweis: Der folgende Aufruf von isPi() ohne Argument ist eine
    # bekannte Inkonsistenz im Testcode – belassen wie gewünscht, um
    # KEINE Logik zu verändern.
    if received_string == "π" or received_string.lower() == "pi":
            ergebnis = isPi()

    elif "sin" in received_string or "cos" in received_string or "tan" in received_string:
            ergebnis = isSCT(received_string)

    elif "log" in received_string:
            ergebnis = isLog(received_string)

    elif "√" in received_string:
            ergebnis = isRoot(received_string)

    elif "e" in received_string:
            ergebnis = isE(received_string)

    else:
        ergebnis = (f"Error. Could not assign an operation. Received String:" + str(received_string))

    print(ergebnis)


def unknown_function(received_string):
    """Dispatch a received function string to the matching evaluator.

    Supported patterns
    ------------------
    - "π" / "pi"
    - "sin(...)" / "cos(...)" / "tan(...)"
    - "log(...)" or "log(x, b)"
    - "√(...)"  (square root)
    - "e(...)"  (exp)

    Returns
    -------
    float | bool | str
        - numeric value on success
        - False if operation cannot be determined
        - or an "ERROR: ..." string for handled errors (g., log input issues)
    """
    if received_string == "π" or received_string.lower() == "pi":
        ergebnis = isPi()

    elif "sin" in received_string or "cos" in received_string or "tan" in received_string:
        ergebnis = isSCT(received_string)

    elif "log" in received_string:
        ergebnis = isLog(received_string)

    elif "√" in received_string:
        ergebnis = isRoot(received_string)

    elif "e" in received_string:
        ergebnis = isE(received_string)

    else:
        ergebnis = False

    return  ergebnis


if __name__ == "__main__":
    test_main()

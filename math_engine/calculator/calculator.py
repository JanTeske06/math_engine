"""
Core calculation engine for math_engine.

This module contains the entire evaluation pipeline from raw string input to
fully typed output value.  Every public calculation request flows through
:func:`calculate`, which delegates to internal stages:

1. **Tokenizer** (:func:`translator`) -- converts a raw input string into a
   flat list of tokens (numbers, operators, parentheses, function names,
   variable placeholders) together with character-level position spans used
   for error reporting.
2. **Parser** (:func:`ast`) -- builds an Abstract Syntax Tree (AST) via
   recursive-descent parsing with full operator-precedence support.  The
   precedence chain (lowest to highest) is:
   ``parse_gleichung`` > ``parse_bor`` > ``parse_bxor`` > ``parse_band``
   > ``parse_shift`` > ``parse_sum`` > ``parse_term`` > ``parse_power``
   > ``parse_unary`` > ``parse_factor``.
3. **Evaluator / Solver** -- either evaluates the AST numerically, solves a
   linear equation for a single variable via :func:`solve`, or performs a
   pure equality check (``==``).
4. **Formatter** (:func:`cleanup`) -- renders results using ``Decimal`` /
   ``Fraction`` precision and the user's ``decimal_places`` /
   ``fractions`` settings.
5. **Output converter** (inside :func:`calculate`) -- applies the output
   prefix (``hex:``, ``int:``, ``bool:``, ``bin:``, ``oct:``, ``str:``,
   ``float:``, ``decimal:``) and returns the final Python-typed value.

Public entry point
------------------
:func:`calculate`
"""

from decimal import Decimal, getcontext, Overflow, DivisionImpossible, InvalidOperation
import fractions
from typing import Union
import re
from ..utility.utility import boolean, isInt, isfloat, isScOp, isOp
from math_engine import config_manager as config_manager
from . import ScientificEngine
from ..utility import error as E
from ..utility.plugin_manager import function_register
from ..utility.non_decimal_utility import int_to_value, value_to_int, non_decimal_scan, apply_word_limit, setbit, bitor, bitand, bitnot, bitxor, shl, shr, clrbit, togbit, testbit
from .AST_Node_Types import Number, BinOp, Variable

# ---------------------------------------------------------------------------
# Module-level constants and configuration
# ---------------------------------------------------------------------------

# Debug toggle — set to True via the ``debug`` setting to print token lists
# and AST trees during evaluation.
debug = False

# Supported operators (used for membership checks in the tokenizer and parser).
Operations = ["+", "-", "*", "/", "=", "^", ">>", "<<", "<", ">", "|","&" ]

# Built-in scientific function names recognized by the tokenizer.
Science_Operations = ["sin", "cos", "tan", "10^x", "log", "e^", "π", "√"]

# Built-in bit manipulation function names recognized by the tokenizer.
Bit_Operations = ["setbit", "bitxor", "shl", "shr", "bitnot", "bitand", "bitor", "clrbit", "togbit", "testbit"]

# Functions registered by plugins at runtime (populated by plugin_manager).
plugin_operations = []

# Global Decimal precision ceiling.  Dynamically adjusted per-calculation in
# ``calculate()`` based on input size and the ``decimal_places`` setting.
getcontext().prec = 10000



# -----------------------------
# Tokenizer
# -----------------------------
# PURE_FUNCTION_NAMES = {
#     'sin', 'cos', 'tan', 'log', 'setbit', 'bitnot', 'bitand',
#     'bitor', 'bitxor', 'shl', 'shr', 'clrbit', 'togbit', 'testbit'
# }

# Maps textual function prefixes to their internal token names.
# Entries ending with ``(`` represent callable functions (require parentheses);
# entries without (like ``"pi"``) represent constants.
RAW_FUNCTION_MAP = {
    "sin(": 'sin',
    "cos(": 'cos',
    "tan(": 'tan',
    "log(": 'log',
    "e^(": 'e^',
    "√(": '√',
    "sqrt(": "√",
    "pi" : "π",
    "PI" : "π",
    "Pi" : "π",
    "setbit(":"setbit",
    "bitnot(":"bitnot",
    "bitand(":"bitand",
    "bitor(":"bitor",
    "bitxor(": "bitxor",
    "shl(": "shl",
    "shr(": "shr",
    "clrbit(": "clrbit",
    "togbit(" : "togbit",
    "testbit(": "testbit"
}

# Set of all function token names that require an opening parenthesis.
# Used to detect bare function names without ``(`` (e.g., ``sin 5`` → error).
PURE_FUNCTION_NAMES = {
    token for start_str, token in RAW_FUNCTION_MAP.items()
    if start_str.endswith('(')
}

# Pre-computed lookup: ``{prefix_string: (token_name, prefix_length)}``.
# Enables O(1) function recognition during tokenization.
FUNCTION_STARTS_OPTIMIZED = {
    start_str: (token, len(start_str))
    for start_str, token in RAW_FUNCTION_MAP.items()
}


def update_function_globals():
    """Rebuild ``PURE_FUNCTION_NAMES`` and ``FUNCTION_STARTS_OPTIMIZED`` from
    ``RAW_FUNCTION_MAP``.

    Called after a plugin registers a new function to ensure the tokenizer
    recognizes the newly added function name.
    """
    global RAW_FUNCTION_MAP
    global PURE_FUNCTION_NAMES
    global FUNCTION_STARTS_OPTIMIZED

    PURE_FUNCTION_NAMES.clear()
    for start_str, token in RAW_FUNCTION_MAP.items():
        if start_str.endswith('('):
            PURE_FUNCTION_NAMES.add(token)

    FUNCTION_STARTS_OPTIMIZED.clear()
    for start_str, token in RAW_FUNCTION_MAP.items():
        FUNCTION_STARTS_OPTIMIZED[start_str] = (token, len(start_str))


def translator(problem, custom_variables, settings):
    """Tokenize a raw mathematical expression into a flat token list.

    Converts the input string into a list of tokens suitable for the
    recursive-descent parser.  Each token is one of:

    * ``Decimal`` -- a numeric literal (integer, float, or scientific notation)
    * ``str`` operator -- ``'+', '-', '*', '/', '**', '=', '<<', '>>', '|', '&', '^'``
    * ``str`` punctuation -- ``'(', ')', ','``
    * ``str`` function name -- ``'sin', 'cos', 'tan', 'log', 'e^', 'sqrt', ...``
    * ``str`` variable placeholder -- ``'var0', 'var1', ...``

    Processing phases (executed in order during a single left-to-right scan):

    1. **Function matching** -- longest-prefix lookup against
       ``FUNCTION_STARTS_OPTIMIZED`` (includes plugin-registered functions).
    2. **Number parsing** -- handles integers, decimals, scientific notation
       (``1.5e-3``), and non-decimal bases (``0x``, ``0b``, ``0o``) when the
       corresponding ``only_*`` setting is active.
    3. **Operator recognition** -- single- and double-char operators
       (``*`` vs ``**``, ``<`` vs ``<<``).
    4. **Hex-mode digit collection** -- when ``only_hex`` is active, bare
       ``A-F`` characters are collected as hex digits.
    5. **Pi constant** -- the ``'pi'`` literal is resolved here as well as the
       Unicode ``'pi'`` glyph.
    6. **Variable fallback** -- any remaining single alpha character is
       assigned a ``var<N>`` placeholder; multi-character unknowns raise an error.
    7. **Implicit multiplication pass** -- a second sweep inserts ``'*'`` between
       adjacent tokens that imply multiplication (e.g., ``2(3)``, ``x y``,
       ``)(``).

    The function also maps the Unicode ``'approx'`` sign (``U+2248``) to ``'='`` so the
    rest of the pipeline handles approximate equality uniformly.

    Args:
        problem:          The raw expression string (no prefix).
        custom_variables: Mapping of user-defined variable names to their values.
        settings:         Dictionary of active engine settings (``only_hex``,
                          ``only_binary``, ``only_octal``, etc.).

    Returns:
        tuple: ``(full_problem, var_counter, token_spans)``

            * *full_problem* -- list of tokens.
            * *var_counter* -- number of distinct variable symbols found.
            * *token_spans* -- parallel list of ``(start_col, end_col, raw_text)``
              tuples for error-position mapping.

    Raises:
        E.SyntaxError: On malformed input (double decimal point, unknown
            character, bare function name without parentheses, etc.).
    """
    global RAW_FUNCTION_MAP
    global plugin_operations

    # --- Hot-register any pending plugin function into the tokenizer maps ---
    # The plugin_manager stores newly registered callables in ``function_register``.
    # On the first call that sees a new entry we inject it into RAW_FUNCTION_MAP
    # and rebuild the optimized lookup tables so subsequent tokenization
    # recognizes the function name.
    if function_register:
        function_name_key = list(function_register.keys())[0]
        function_name_pure = function_name_key.rstrip("(")

        if function_name_key not in RAW_FUNCTION_MAP:
            RAW_FUNCTION_MAP[function_name_key] = function_name_pure
            plugin_operations.append(function_name_pure)

            # Rebuild PURE_FUNCTION_NAMES and FUNCTION_STARTS_OPTIMIZED
            update_function_globals()
            print("Globale Funktionsregister nach Plugin-Registrierung aktualisiert.")
    # --- Tokenizer state initialisation ---
    var_counter = 0
    var_list = [None] * len(problem)  # Track seen variable symbols -> var0, var1, ...
    full_problem = []       # Accumulated output tokens
    token_spans = []        # Parallel position spans for error reporting
    b = 0                   # Current scan position in the input string

    # Build a string-valued copy of custom_variables for inline substitution.
    CONTEXT_VARS = {}
    for var_name, value in custom_variables.items():
        if isinstance(value, (int, float, Decimal)):
            CONTEXT_VARS[var_name] = str(value)
        elif isinstance(value, bool):
            CONTEXT_VARS[var_name] = "1" if value else "0"
        else:
            CONTEXT_VARS[var_name] = str(value)

    # Sort variable names longest-first so that e.g. "ab" is matched before "a".
    sorted_vars = sorted(CONTEXT_VARS.keys(), key=len, reverse=True)
    HEX_DIGITS = "0123456789ABCDEFabcdef"
    temp_problem = problem
    # for var_name in sorted_vars:
    #     value_str = CONTEXT_VARS[var_name]
    #     value_str = value_str
    #     temp_problem = temp_problem.replace(var_name, value_str)

    problem = temp_problem

    # --- Main character-by-character scanning loop ---
    # Each iteration classifies the character(s) at position ``b`` into exactly
    # one token category (function, number, operator, paren, constant, or
    # variable) and advances ``b`` past the consumed characters.
    temp_var = -1
    while b < len(problem):
        found_function = False
        current_char = problem[b]

        # Phase 1: Try to match a known function / constant prefix at this position.
        for start_str, (token, length) in FUNCTION_STARTS_OPTIMIZED.items():
            if problem.startswith(start_str, b):
                full_problem.append(token)
                token_spans.append((b, b+len(token)-1, token))
                if token != "π" and token != "E" and token != "e":
                    full_problem.append("(")
                    token_spans.append((b+len(token), b+len(token), "("))

                b += length - 0
                found_function = True
                break
        if found_function:
            if settings["only_hex"] == True or settings["only_binary"] == True or settings["only_octal"]== True:
                raise E.SyntaxError(f"Function not support with only not decimals.", code="3033")
            continue

        # --- Phase 2: Number parsing (decimal, scientific notation, non-decimal bases) ---
        # First attempts a non-decimal scan (0x, 0b, 0o prefixes).  If that
        # fails, falls back to standard decimal/scientific-notation parsing
        # which handles digits, decimal points, and 'E'/'e' exponents.
        if isInt(current_char) or (b >= 0 and current_char == "."):
            start_index = b
            parsed_value, new_index = non_decimal_scan(problem, b, settings)

            if parsed_value is not None:
                original_str = problem[start_index:new_index]
                token_spans.append((start_index, new_index, original_str))
                full_problem.append(parsed_value)
                b = new_index - 1

            else:

                str_number = current_char
                has_decimal_point = (current_char == '.')
                has_exponent_e = False

                while (b + 1 < len(problem)):
                    next_char = problem[b + 1]

                    # 1. Handle decimal points
                    if next_char == ".":
                        if has_decimal_point:
                            raise E.SyntaxError(f"Double decimal point.", code="3008", position_start=b + 1)
                        has_decimal_point = True

                    # 2. Handle the 'E' or 'e' for exponent
                    elif next_char in ('e', 'E'):
                        if temp_var == b and b > 0:
                            raise E.SyntaxError(f"Multiple digit variables not supported.",
                                                code="3032", position_start=b + 1)
                        if has_exponent_e:
                            # Cannot have two 'e's in a single number
                            raise E.SyntaxError("Double exponent sign 'E'/'e'.", code="3031", position_start=b + 1)
                        has_exponent_e = True

                    # 3. Handle the sign (+ or -) immediately following 'E'/'e'
                    elif next_char in ('+', '-'):
                        # The sign is only valid if it immediately follows 'e' or 'E'
                        if not (problem[b] in ('e', 'E') and has_exponent_e):
                            break

                    # 4. End the loop if the next character is not a number component
                    elif not isInt(next_char):
                        break

                    # If we made it here, the character is a valid part of the number
                    b += 1
                    str_number += problem[b]

                # Validate the final collected string
                if isfloat(str_number) or isInt(str_number):
                    if settings["only_hex"] == True:
                        str_number = value_to_int("0x"+str_number)
                    elif settings["only_binary"] == True:
                        str_number = value_to_int("0b"+str_number)
                    elif settings["only_octal"] == True:
                        str_number = value_to_int("0O"+str_number)
                    token_spans.append((start_index, b, str_number))
                    full_problem.append(Decimal(str_number))
                else:
                    if has_exponent_e and not str_number[-1].isdigit():
                        raise E.SyntaxError("Missing exponent value after 'E'/'e'.", code="3032", position_start=b)

        # --- Phase 3: Operator recognition ---
        # Handles single-char ops (+, -, *, /, =, ^, |, &) and two-char
        # compound ops (**, <<, >>).  Invalid combos like <> or >< raise errors.
        elif isOp(current_char) != -1:
            start_index = b
            if current_char == "*" and b + 1 < len(problem) and problem[b + 1] == "*":
                full_problem.append("**")
                token_spans.append((start_index, b + 1, "**"))
                b += 1
            elif current_char != "<" and current_char != ">":
                full_problem.append(current_char)
                token_spans.append((start_index, b, current_char))
            elif current_char == "<" and b<= len(problem)+1:
                if problem[b+1] == "<":
                    full_problem.append("<<")
                    token_spans.append((start_index, b + 1, "<<"))
                    b+=1
                elif problem[b+1] == ">":
                    raise E.SyntaxError("Invalid shift Operation <>", code = "3040")


            elif current_char == ">" and b <= len(problem) + 1:
                following_char = problem[b + 1]
                if problem[b + 1] == ">":
                    full_problem.append(">>")
                    token_spans.append((b, b+1, ">>"))
                    b += 1
                elif problem[b+1] == "<":
                    raise E.SyntaxError("Invalid shift Operation ><", code = "3040")

            else:
                raise E.SyntaxError("Unknown Error.", code = "9999")




        # --- Whitespace (ignored) ---
        elif current_char == " ":
            pass

        # --- Parentheses ---
        elif current_char == "(":
            full_problem.append("(")
            token_spans.append((b, b, current_char))
        elif current_char == "≈":  # treat as equality
            full_problem.append("=")
            token_spans.append((b, b, current_char))
        elif current_char == ")":
            full_problem.append(")")
            token_spans.append((b, b, current_char))
        elif current_char == ",":
            full_problem.append(",")
            token_spans.append((b, b, current_char))

        # --- Scientific functions and special forms: sin(, cos(, tan(, log(, √(, e^( ---

        # --- Phase 4: Hex-mode bare digit collection ---
        # When ``only_hex`` is active, characters A-F (case-insensitive) that
        # were not already consumed as part of a numeric literal are gathered
        # here and interpreted as hexadecimal digits.
        elif settings.get("only_hex", False) and current_char in HEX_DIGITS:
            str_number = current_char
            start_index = b
            while b + 1 < len(problem) and problem[b + 1] in HEX_DIGITS:
                b += 1
                str_number += problem[b]

            # Jetzt "0x" davorsetzen und in int -> Decimal umwandeln
            try:
                int_value = value_to_int("0x" + str_number)
                full_problem.append(Decimal(int_value))
                token_spans.append((start_index, b, str_number))
            except E.ConversionError as e:
                raise

        # --- Phase 5: Pi constant (Unicode glyph) ---
        elif current_char == 'π':
            if settings["only_hex"] == True or settings["only_binary"] == True or settings["only_octal"]== True:
                raise E.SyntaxError(f"Error with constant π:{result_string}", code="3033", position_start=b)
            result_string = ScientificEngine.isPi(str(current_char))
            try:
                calculated_value = Decimal(result_string)
                full_problem.append(calculated_value)
            except ValueError:
                raise E.CalculationError(f"Error with constant π:{result_string}", code="3219", position_start=b)

                # --- Phase 6: Variable / identifier fallback ---
                # Any remaining alphabetic character is treated as a variable.
                # Multi-char identifiers that are not in ``custom_variables``
                # and not a known function name are rejected.  Single-char
                # unknowns are assigned sequential ``var<N>`` placeholders for
                # the equation solver.
        else:
                start_index = b
                var_name = ""
                while b < len(problem):
                    char = problem[b]
                    if char.isalnum() or char == '_':
                        var_name += char
                        b += 1
                    else:
                        break

                if len(var_name) == 0:
                    raise E.SyntaxError(f"Unexpected token: {current_char}", code="3012", position_start=b)

                for func_name in PURE_FUNCTION_NAMES:
                    if var_name.startswith(func_name):
                        raise E.SyntaxError(
                            f"Function name '{func_name}' must be followed by '('.",
                            code="3010", position_start=start_index + len(func_name) - 1
                        )

                if var_name in custom_variables:
                    val = custom_variables[var_name]
                    if isinstance(val, (int, float)):
                        val = Decimal(val)
                    elif isinstance(val, bool):
                        val = Decimal(1) if val else Decimal(0)

                    full_problem.append(val)
                    token_spans.append((start_index, b, var_name))
                    b = b - 1

                else:
                    # Erst wenn es KEINE bekannte Variable ist, prüfen wir die Länge
                    if len(var_name) > 1:
                        raise E.SyntaxError(f"Unknown function or variable too long: '{var_name}'", code="3011",
                                            position_start=start_index, position_end=b)

                    if var_name in var_list:
                        idx = var_list.index(var_name)
                        full_problem.append("var" + str(idx))
                    else:
                        full_problem.append("var" + str(var_counter))
                        if var_counter >= len(var_list):
                            var_list.append(var_name)
                        else:
                            var_list[var_counter] = var_name
                        var_counter += 1

                    token_spans.append((start_index, b, var_name))
                    b = b - 1

        b = b + 1

    # --- Phase 7: Implicit multiplication pass ---
    # After the main scan, a second left-to-right sweep detects adjacent token
    # pairs that mathematically imply multiplication and inserts an explicit
    # '*' token between them.  The inserted token's span is tagged "*_impl"
    # so downstream code can distinguish it from user-written multiplication
    # if needed.
    #
    # Pairs that trigger insertion (current -> successor):
    #   number/variable/')' followed by '(' / number / variable / function
    #
    # Examples:  "2x" -> "2 * x",  "3(4)" -> "3 * (4)",  ")(x" -> ") * (x"
    b = 0
    while b < len(full_problem):

        if b + 1 < len(full_problem):

            current_element = full_problem[b]
            successor = full_problem[b + 1]
            insertion_needed = False

            # Classify the current and next tokens for the multiplication check.
            is_function_name = isScOp(successor) != -1
            is_number_or_variable = isinstance(current_element, (int, float, Decimal)) or (
                        "var" in str(current_element) and
                        isinstance(current_element, str))
            is_paren_or_variable_or_number = (
                        successor == '(' or ("var" in str(successor) and isinstance(successor, str)) or
                        isinstance(successor, (int, float, Decimal)) or is_function_name)
            is_not_an_operator = current_element not in Operations and successor not in Operations

            # Only insert '*' when both sides are value-like and neither is
            # already an operator.
            if (is_number_or_variable or current_element == ')') and \
                    (is_paren_or_variable_or_number or successor == '(') and \
                    is_not_an_operator:

                if current_element in ['*', '+', '-', '/'] or successor in ['*', '+', '-', '/']:
                    insertion_needed = False
                elif current_element == ')' and successor == '(':
                    insertion_needed = True
                elif current_element != '(' and successor != ')':
                    insertion_needed = True

            if insertion_needed:
                next_pos = token_spans[b + 1][0] if b + 1 < len(token_spans) else b
                token_spans.insert(b + 1, (next_pos, next_pos, "*_impl"))
                full_problem.insert(b + 1, '*')

        b += 1
    return full_problem, var_counter, token_spans


# -----------------------------
# Parser (recursive descent)
# -----------------------------

def ast(received_string, settings, custom_variables):
    """Parse a raw expression into an Abstract Syntax Tree using recursive descent.

    The function first tokenizes the input via :func:`translator`, then runs
    a series of pre-parse validations and rewrites before invoking the
    recursive-descent parser.

    **Pre-parse validations / rewrites:**

    * Multiple ``=`` signs that are not adjacent (``==``) are rejected.
    * Adjacent ``==`` sets the ``expected_bool`` flag so the caller knows the
      user intended a boolean equality check.
    * A leading or trailing ``=`` without a variable is silently stripped.
    * A leading ``*`` or ``/`` raises a "Missing Number" error.
    * **Augmented assignment rewriting** -- when ``allow_augmented_assignment``
      is ``True`` and the token stream contains ``<op>=`` (e.g., ``+=``), the
      sequence is rewritten into ``= (<original_lhs> <op> <rhs>)`` so that
      ``5 += 3`` becomes ``= (5 + 3)``.

    **Operator-precedence chain** (lowest to highest):

    ========== ===================== ==================================
    Level      Function              Operators
    ========== ===================== ==================================
    1 (lowest) ``parse_gleichung``   ``=``  (equation / equality)
    2          ``parse_bor``         ``|``  (bitwise OR)
    3          ``parse_bxor``        ``^``  (bitwise XOR)
    4          ``parse_band``        ``&``  (bitwise AND)
    5          ``parse_shift``       ``<<``, ``>>``
    6          ``parse_sum``         ``+``, ``-``
    7          ``parse_term``        ``*``, ``/``
    8          ``parse_power``       ``**`` (right-associative)
    9          ``parse_unary``       unary ``+`` / ``-``
    10 (highest) ``parse_factor``    numbers, variables, ``(...)``, functions
    ========== ===================== ==================================

    Args:
        received_string:  The raw expression string (no output prefix).
        settings:         Engine settings dictionary.
        custom_variables: User-supplied variable bindings.

    Returns:
        tuple: ``(final_tree, cas, var_counter, expected_bool)``

            * *final_tree* -- root AST node (``Number``, ``BinOp``, or
              ``Variable``).
            * *cas* -- ``True`` if the expression contains ``=`` (equation mode).
            * *var_counter* -- number of distinct variable placeholders.
            * *expected_bool* -- ``True`` if ``==`` was detected (equality check).

    Raises:
        E.SyntaxError:       On structural issues (empty input, missing numbers).
        E.CalculationError:  On semantic issues (augmented assignment with
                             variables, trailing operators, etc.).
    """
    analysed, var_counter, token_spans = translator(received_string, custom_variables, settings)
    d = 0
    mutliple_equalsign = False
    temp_position = -2
    expected_bool = False
    token_spans = list(token_spans)

    # --- Pre-scan: detect multiple / adjacent '=' signs ---
    # * Two non-adjacent '=' signs (e.g., "a = b = c") -> error.
    # * Two adjacent '=' signs (i.e., "==") -> set ``expected_bool`` so the
    #   caller treats the expression as an equality check returning bool.
    while d < len(analysed):
        if analysed[d] == "=":
            if temp_position != -2 and temp_position != d - 1:
                # Second '=' found at a non-adjacent position -- ambiguous equation
                err_pos = token_spans[d][0]
                raise E.CalculationError("Multiple Equal signs in one Problem.", code="3036", position_start=err_pos)
            elif temp_position == -2 and temp_position != d - 1:
                temp_position = d
            elif temp_position != -2 and temp_position == d - 1:
                # Adjacent '=' ('==') -- treat as boolean equality test
                expected_bool = True
                temp_position = d
        d += 1

    if analysed == []:
        raise E.SyntaxError("Empty String", code="3034")

    # Normalize spurious leading/trailing '='
    if analysed and analysed[0] == "=" and not "var0" in analysed:
        analysed.pop(0)
        token_spans.pop(0)  # Sync

    if analysed and analysed[-1] == "=" and not "var0" in analysed:
        analysed.pop()
        token_spans.pop()  # Sync

    # Guard against starting with '*' or '/'
    if analysed and (analysed[0] == "*" or analysed[0] == "/"):
        raise E.CalculationError("Missing Number.", code="3028", position_start=token_spans[0][0])

    # --- Pre-parse validations and augmented-assignment rewriting ---
    # Walk the token list to detect and handle:
    #   - Augmented assignment (e.g., "+=" rewritten to "= ( ... + ... )")
    #   - Operators adjacent to '=' without AA enabled -> error
    #   - Trailing operators with no right-hand operand -> error
    if analysed:
        b = 0
        while b < len(analysed) - 1:
            # Case 1: operator directly followed by '=' (e.g., "+=") without AA allowed
            if (len(analysed) != b + 1) and (analysed[b + 1] == "=" and (analysed[b] in Operations)) and (
                    settings["allow_augmented_assignment"] == False):
                raise E.CalculationError("Missing Number before '='.", code="3028",
                                         position_start=token_spans[b + 1][0])

            # Case 1a: Augmented assignment rewriting (AA enabled, no variables)
            # Transform "A += B" into "A = (A + B)":
            #   1. Append a closing ')' at the end of the token list.
            #   2. Insert an opening '(' right after the '=' position.
            #   3. Remove the original '=' token (the operator before it
            #      becomes the infix operator inside the parentheses).
            elif ((len(analysed) != b + 1 or len(analysed) != b + 2) and (
                    analysed[b + 1] == "=" and (analysed[b] in Operations)) and (
                          settings["allow_augmented_assignment"] == True) and not "var0" in analysed):
                current_span = token_spans[b]
                analysed.append(")")
                token_spans.append((token_spans[-1][1], token_spans[-1][1], ")"))

                analysed.insert(b + 2, "(")
                token_spans.insert(b + 2, (token_spans[b + 1][1], token_spans[b + 1][1], "("))

                analysed.pop(b + 1)
                token_spans.pop(b + 1)

            # Case 1b: AA with variables
            elif ((len(analysed) != b + 1 or len(analysed) != b + 2) and (
                    analysed[b + 1] == "=" and (analysed[b] in Operations)) and (
                          settings["allow_augmented_assignment"] == True) and "var0" in analysed):
                raise E.CalculationError("Augmented assignment not allowed with variables.", code="3030",
                                         position_start=token_spans[b][0])

            # Case 2: '=' precedes an operator
            elif (b > 0) and (analysed[b + 1] == "=" and (analysed[b] in Operations)):
                raise E.CalculationError("Missing Number after '='.", code="3028", position_start=token_spans[b + 1][0])

            # Expression ends with an operator
            elif analysed[-1] in Operations:
                token_index_of_error = len(analysed) - 1
                char_index_of_error = token_spans[token_index_of_error][1]
                raise E.CalculationError(f"Missing Number after {analysed[-1]}", code="3029",
                                         position_start=char_index_of_error)

            # operator followed by '=' (AA disabled)
            elif (analysed[b] in Operations and (analysed[b + 1] == "=" and (
                    settings["allow_augmented_assignment"] == False))) and not "var0" in analysed:
                raise E.CalculationError(f"Missing Number after {analysed[b]}", code="3029",
                                         position_start=token_spans[b][1])

            b += 1

    # '=' at start/end while a variable exists
    if ((analysed and analysed[-1] == "=") or (analysed and analysed[0] == "=")) and "var0" in analysed:
        pos = token_spans[0][0] if analysed[0] == "=" else token_spans[-1][0]
        raise E.CalculationError(f"{received_string}", code="3025", position_start=pos)

    if debug == True:
        print(analysed)

    # ---- Parsing functions in precedence order ----

    def parse_factor(tokens, token_spans):
        """Parse an atomic expression (highest precedence level).

        Handles:
        * Numeric literals (``Decimal``, ``int``, ``float``) -> ``Number`` node.
        * Variable placeholders (``var0``, ``var1``, ...) -> ``Variable`` node.
        * Parenthesised sub-expressions -> recursively parsed via ``parse_bor``.
        * Scientific functions (``sin``, ``cos``, ``tan``, ``log``, ``e^``,
          ``sqrt``) -> evaluated eagerly and returned as ``Number`` nodes.
        * Bit-manipulation functions (``setbit``, ``bitnot``, ...) -> evaluated
          eagerly; two-argument variants consume a comma-separated second arg.
        """
        list(token_spans)
        if len(tokens) > 0:
            token = tokens.pop(0)
            pos = token_spans.pop(0)
        else:
            raise E.CalculationError(f"Missing Number.", code="3027")

        if token == "(":
            l_paren_pos = pos
            subtree_in_paren = parse_bor(tokens, token_spans)
            if not tokens or tokens[0] != ')':
                err_pos = l_paren_pos[0]
                raise E.SyntaxError("Missing closing parenthesis ')'", code="3009", position_start=err_pos)
            tokens.pop(0)
            token_spans.pop(0)
            return subtree_in_paren

        # elif token in plugin_operations:
        #     if not tokens or tokens[0] != '(':
        #         err_pos = token_spans[0][0] if token_spans else pos[1]
        #         raise E.SyntaxError(f"Missing opening parenthesis after bit function {token}", code="3010",
        #                             position_start=err_pos)
        #
        #     tokens.pop(0)
        #     l_paren_pos = token_spans.pop(0)
        #
        #     argument_subtree = parse_bor(tokens, token_spans)
        #
        #     def get_second_arg_and_close():
        #         if not tokens or tokens[0] != ',':
        #             err_pos = token_spans[0][0] if token_spans else l_paren_pos[0]
        #             raise E.SyntaxError(f"Missing comma after first argument in '{token}'", code="3009",
        #                                 position_start=err_pos)
        #         tokens.pop(0)
        #         token_spans.pop(0)
        #
        #         base_sub = parse_bor(tokens, token_spans)
        #
        #         if not tokens or tokens[0] != ')':
        #             raise E.SyntaxError(f"Missing closing parenthesis after '{token}' arguments.", code="3009",
        #                                 position_start=l_paren_pos[0])
        #         tokens.pop(0)
        #         end_pos = token_spans.pop(0)
        #         return base_sub, end_pos
        #
        #     def close_only():
        #         if not tokens or tokens[0] != ')':
        #             raise E.SyntaxError(f"Missing closing parenthesis after function '{token}'", code="3009",
        #                                 position_start=l_paren_pos[0])
        #         tokens.pop(0)
        #         token_spans.pop(0)
        #         if tokens and tokens[0] == ',':
        #             err_pos = token_spans[0][0]
        #             raise E.SyntaxError(f"Comma in '{token}'", code="8008", position_start=err_pos)
        #
        #         if not tokens or tokens[0] != ')':
        #             err_pos = token_spans[0][0] if token_spans else pos[1] + 1
        #             raise E.SyntaxError(f"Missing closing parenthesis after function '{token}'", code="3009",
        #                                 position_start=err_pos)
        #         tokens.pop(0)
        #         end_paren_span = token_spans.pop(0)
        #
        #         argument_value = argument_subtree.evaluate()
        #         if argument_value % 1 != 0:
        #             arg_start = argument_subtree.position_start if argument_subtree.position_start != -1 else pos[0]
        #             arg_end = argument_subtree.position_end if argument_subtree.position_end != -1 else end_paren_span[
        #                 1]
        #
        #             raise E.CalculationError("Bit functions require integer values.", code="3041",
        #                                      position_start=arg_start, position_end=arg_end)
        #
        #         try:
        #             return Number(bitnot(argument_value))
        #         except Exception as e:
        #             raise E.SyntaxError(f"Error in {token}: {e}", code="8007", position_start=pos[0])
        #     if token == "ln":
        #         if tokens and tokens[0] == ',':
        #             err_pos = token_spans[0][0]
        #             raise E.SyntaxError(f"Comma in '{token}'", code="8008", position_start=err_pos)
        #
        #         if not tokens or tokens[0] != ')':
        #             err_pos = token_spans[0][0] if token_spans else pos[1] + 1
        #             raise E.SyntaxError(f"Missing closing parenthesis after function '{token}'", code="3009",
        #                                 position_start=err_pos)
        #     tokens.pop(0)
        #     end_paren_span = token_spans.pop(0)
        #
        #     argument_value = argument_subtree.evaluate()
        #     if argument_value % 1 != 0:
        #         arg_start = argument_subtree.position_start if argument_subtree.position_start != -1 else pos[0]
        #         arg_end = argument_subtree.position_end if argument_subtree.position_end != -1 else end_paren_span[
        #             1]
        #
        #         raise E.CalculationError("Bit functions require integer values.", code="3041",
        #                                  position_start=arg_start, position_end=arg_end)
        #
        #     try:
        #         return Number(bitnot(argument_value))
        #     except Exception as e:
        #         raise E.SyntaxError(f"Error in {token}: {e}", code="8007", position_start=pos[0])


        elif token in Science_Operations:
            if token == 'π':
                result = ScientificEngine.isPi(token)
                try:
                    calculated_value = Decimal(result)
                    return Number(calculated_value, position_start=pos[0], position_end=pos[1])
                except ValueError:
                    raise E.SyntaxError(f"Error with constant π: {result}", code="3219", position_start=pos[0])
            else:
                if not tokens or tokens[0] != '(':
                    err_pos = token_spans[0][0] if token_spans else pos[1]
                    raise E.SyntaxError(f"Missing opening parenthesis after function {token}", code="3010",
                                        position_start=err_pos)

                tokens.pop(0)
                l_paren_pos = token_spans.pop(0)

                argument_subtree = parse_bor(tokens, token_spans)

                if token == 'log' and tokens and tokens[0] == ',':
                    tokens.pop(0)
                    token_spans.pop(0)
                    base_subtree = parse_bor(tokens, token_spans)
                    if not tokens or tokens[0] != ')':
                        raise E.SyntaxError(f"Missing closing parenthesis after logarithm base.", code="3009",
                                            position_start=l_paren_pos[0])
                    tokens.pop(0)
                    token_spans.pop(0)

                    argument_value = argument_subtree.evaluate()
                    base_value = base_subtree.evaluate()
                    ScienceOp = f"{token}({argument_value},{base_value})"
                else:
                    if not tokens or tokens[0] != ')':
                        # Fehler zeigt auf '('
                        raise E.SyntaxError(f"Missing closing parenthesis after function '{token}'", code="3009",
                                            position_start=l_paren_pos[0])
                    tokens.pop(0)
                    token_spans.pop(0)

                    argument_value = argument_subtree.evaluate()
                    ScienceOp = f"{token}({argument_value})"

                if token not in Bit_Operations:
                    result_string = ScientificEngine.unknown_function(ScienceOp)
                    if isinstance(result_string, str) and result_string.startswith("ERROR:"):
                        raise E.SyntaxError(result_string, code="3218", position_start=pos[0])
                    try:
                        return Number(result_string, position_start=pos[0], position_end=pos[1])
                    except ValueError:
                        raise E.SyntaxError(f"Error in scientific function: {result_string}", code="3218",
                                            position_start=pos[0])

        elif token in Bit_Operations:
            if not tokens or tokens[0] != '(':
                err_pos = token_spans[0][0] if token_spans else pos[1]
                raise E.SyntaxError(f"Missing opening parenthesis after bit function {token}", code="3010",
                                    position_start=err_pos)

            tokens.pop(0)
            l_paren_pos = token_spans.pop(0)

            argument_subtree = parse_bor(tokens, token_spans)

            def get_second_arg_and_close():
                """Consume a comma, parse the second argument, and consume the closing ')'.

                Used by two-argument bit functions (e.g., ``setbit(val, bit)``).

                Returns:
                    tuple: ``(second_arg_subtree, closing_paren_span)``
                """
                if not tokens or tokens[0] != ',':
                    err_pos = token_spans[0][0] if token_spans else l_paren_pos[0]
                    raise E.SyntaxError(f"Missing comma after first argument in '{token}'", code="3009",
                                        position_start=err_pos)
                tokens.pop(0)
                token_spans.pop(0)

                base_sub = parse_bor(tokens, token_spans)

                if not tokens or tokens[0] != ')':
                    raise E.SyntaxError(f"Missing closing parenthesis after '{token}' arguments.", code="3009",
                                        position_start=l_paren_pos[0])
                tokens.pop(0)
                end_pos = token_spans.pop(0)
                return base_sub, end_pos

            def close_only():
                """Consume only the closing ')' -- used by single-argument bit functions."""
                if not tokens or tokens[0] != ')':
                    raise E.SyntaxError(f"Missing closing parenthesis after function '{token}'", code="3009",
                                        position_start=l_paren_pos[0])
                tokens.pop(0)
                token_spans.pop(0)

            if token == 'setbit':
                base_subtree, end_pos = get_second_arg_and_close()
                argument_value = argument_subtree.evaluate()
                base_value = base_subtree.evaluate()
                if argument_value % 1 != 0 or base_value % 1 != 0:
                    raise E.CalculationError("Bit functions require integer values.", code="3041",
                                             position_start=pos[0], position_end=end_pos[1])
                try:
                    return Number(setbit(argument_value, base_value), position_start=pos[0],
                                  position_end=end_pos[1])
                except Exception as e:
                    raise E.SyntaxError(f"Error in {token}: {e}", code="8007", position_start=pos[0])


            elif token == 'bitxor':
                    base_subtree, end_pos = get_second_arg_and_close()
                    argument_value = argument_subtree.evaluate()
                    base_value = base_subtree.evaluate()
                    if argument_value % 1 != 0 or base_value % 1 != 0:
                        raise E.CalculationError("Bit functions require integer values.", code="3041",
                                                 position_start=pos[0], position_end=end_pos[1])
                    try:
                        return Number(bitxor(argument_value, base_value), position_start=pos[0],
                                      position_end=end_pos[1])
                    except Exception as e:
                        raise E.SyntaxError(f"Error in {token}: {e}", code="8007", position_start=pos[0])

            elif token == 'clrbit':
                base_subtree, end_pos = get_second_arg_and_close()
                argument_value = argument_subtree.evaluate()
                base_value = base_subtree.evaluate()
                if argument_value % 1 != 0 or base_value % 1 != 0:
                    raise E.CalculationError("Bit functions require integer values.", code="3041",
                                             position_start=pos[0], position_end=end_pos[1])
                try:
                    return Number(clrbit(argument_value, base_value), position_start=pos[0], position_end=end_pos[1])
                except Exception as e:
                    raise E.SyntaxError(f"Error in {token}: {e}", code="8007", position_start=pos[0])

            elif token == 'togbit':
                base_subtree, end_pos = get_second_arg_and_close()
                argument_value = argument_subtree.evaluate()
                base_value = base_subtree.evaluate()
                if argument_value % 1 != 0 or base_value % 1 != 0:
                    raise E.CalculationError("Bit functions require integer values.", code="3041",
                                             position_start=pos[0], position_end=end_pos[1])
                try:
                    return Number(togbit(argument_value, base_value), position_start=pos[0], position_end=end_pos[1])
                except Exception as e:
                    raise E.SyntaxError(f"Error in {token}: {e}", code="8007", position_start=pos[0])

            elif token == 'testbit':
                base_subtree, end_pos = get_second_arg_and_close()
                argument_value = argument_subtree.evaluate()
                base_value = base_subtree.evaluate()
                if argument_value % 1 != 0 or base_value % 1 != 0:
                    raise E.CalculationError("Bit functions require integer values.", code="3041",
                                             position_start=pos[0], position_end=end_pos[1])
                try:
                    result_bool = testbit(argument_value, base_value)
                    val = 1 if result_bool else 0
                    return Number(val, position_start=pos[0], position_end=end_pos[1])
                except Exception as e:
                    raise E.SyntaxError(f"Error in {token}: {e}", code="8007", position_start=pos[0])

            elif token == 'shl':
                base_subtree, end_pos = get_second_arg_and_close()
                argument_value = argument_subtree.evaluate()
                base_value = base_subtree.evaluate()
                if argument_value % 1 != 0 or base_value % 1 != 0:
                    raise E.CalculationError("Bit functions require integer values.", code="3041",
                                             position_start=pos[0], position_end=end_pos[1])
                try:
                    return Number(shl(argument_value, base_value), position_start=pos[0], position_end=end_pos[1])
                except Exception as e:
                    raise E.CalculationError(str(e), code="3041", position_start=pos[0])

            elif token == 'shr':
                base_subtree, end_pos = get_second_arg_and_close()
                argument_value = argument_subtree.evaluate()
                base_value = base_subtree.evaluate()
                if argument_value % 1 != 0 or base_value % 1 != 0:
                    raise E.CalculationError("Bit functions require integer values.", code="3041",
                                             position_start=pos[0], position_end=end_pos[1])
                try:
                    return Number(shr(argument_value, base_value), position_start=pos[0], position_end=end_pos[1])
                except Exception as e:
                    raise E.CalculationError(str(e), code="3041", position_start=pos[0])

            elif token == 'bitand':
                base_subtree, end_pos = get_second_arg_and_close()
                argument_value = argument_subtree.evaluate()
                base_value = base_subtree.evaluate()
                if argument_value % 1 != 0 or base_value % 1 != 0:
                    raise E.CalculationError("Bit functions require integer values.", code="3041",
                                             position_start=pos[0], position_end=end_pos[1])
                try:
                    return Number(bitand(argument_value, base_value), position_start=pos[0], position_end=end_pos[1])
                except Exception as e:
                    raise E.CalculationError(str(e), code="3041", position_start=pos[0])

            elif token == 'bitor':
                base_subtree, end_pos = get_second_arg_and_close()
                argument_value = argument_subtree.evaluate()
                base_value = base_subtree.evaluate()
                if argument_value % 1 != 0 or base_value % 1 != 0:
                    raise E.CalculationError("Bit functions require integer values.", code="3041",
                                             position_start=pos[0], position_end=end_pos[1])
                try:
                    return Number(bitor(argument_value, base_value), position_start=pos[0], position_end=end_pos[1])
                except Exception as e:
                    raise E.CalculationError(str(e), code="3041", position_start=pos[0])

            elif token == "bitnot":
                if tokens and tokens[0] == ',':
                    err_pos = token_spans[0][0]
                    raise E.SyntaxError(f"Comma in '{token}'", code="8008", position_start=err_pos)

                if not tokens or tokens[0] != ')':
                    err_pos = token_spans[0][0] if token_spans else pos[1] + 1
                    raise E.SyntaxError(f"Missing closing parenthesis after function '{token}'", code="3009",
                                        position_start=err_pos)
                tokens.pop(0)
                end_paren_span = token_spans.pop(0)

                argument_value = argument_subtree.evaluate()
                if argument_value % 1 != 0:
                    arg_start = argument_subtree.position_start if argument_subtree.position_start != -1 else pos[0]
                    arg_end = argument_subtree.position_end if argument_subtree.position_end != -1 else end_paren_span[
                        1]

                    raise E.CalculationError("Bit functions require integer values.", code="3041",
                                             position_start=arg_start, position_end=arg_end)

                try:
                    return Number(bitnot(argument_value))
                except Exception as e:
                    raise E.SyntaxError(f"Error in {token}: {e}", code="8007", position_start=pos[0])
            else:
                close_only()
                raise E.SyntaxError(f"Error in bit operation '{token}'", code="8008", position_start=pos[0])

        elif isinstance(token, Decimal):
            return Number(token, position_start=pos[0], position_end=pos[1])
        elif isInt(token):
            return Number(token, position_start=pos[0], position_end=pos[1])
        elif isfloat(token):
            return Number(token, position_start=pos[0], position_end=pos[1])
        elif "var" in str(token):
            return Variable(token, position_start=pos[0], position_end=pos[1])
        else:
            raise E.SyntaxError(f"Unexpected token: {token}", code="3012", position_start=pos[0])

    # --- Precedence level 9: Unary operators ---
    def parse_unary(tokens, token_spans):
        """Handle leading unary ``+`` or ``-``.

        A unary ``-`` is rewritten as ``BinOp(Number(0), '-', operand)`` so
        the evaluator does not need special-case logic.  Unary ``+`` is a
        no-op and simply returns the operand unchanged.  Recursively calls
        itself to allow chained unary operators (e.g., ``--x``).
        """
        if tokens and tokens[0] in ('+', '-'):
            operator = tokens.pop(0)
            pos = token_spans.pop(0)  # Sync
            operand = parse_unary(tokens, token_spans)

            if operator == '-':
                if isinstance(operand, Number):
                    return Number(-operand.evaluate())
                return BinOp(Number('0'), '-', operand)
            else:
                return operand
        return parse_power(tokens, token_spans)

    # --- Precedence level 8: Exponentiation ---
    def parse_power(tokens, token_spans):
        """Parse exponentiation (``**``), which is right-associative.

        If neither operand is a ``Variable``, the power is evaluated eagerly
        and collapsed into a single ``Number`` node to reduce AST depth.
        When a variable is involved, a ``BinOp`` node is produced so the
        equation solver can inspect the structure.
        """
        current_subtree = parse_factor(tokens, token_spans)
        while tokens and (tokens[0] == "**"):
            operator = tokens.pop(0)
            pos = token_spans.pop(0)
            right_part = parse_unary(tokens, token_spans)
            if not isinstance(current_subtree, Variable) and not isinstance(right_part, Variable):
                base = current_subtree.evaluate()
                exponent = right_part.evaluate()
                result = base ** exponent
                current_subtree = Number(result)
            else:
                current_subtree = BinOp(current_subtree, operator, right_part, position_start=pos[0], position_end=pos[1])
                return current_subtree
        return current_subtree

    # --- Precedence level 7: Multiplication and division ---
    def parse_term(tokens, token_spans):
        """Parse multiplication (``*``) and division (``/``).

        Left-associative: ``a * b / c`` is parsed as ``(a * b) / c``.
        """
        current_subtree = parse_unary(tokens, token_spans)
        while tokens and tokens[0] in ("*", "/"):
            operator = tokens.pop(0)
            pos = token_spans.pop(0)  # Sync
            right_part = parse_unary(tokens, token_spans)
            current_subtree = BinOp(current_subtree, operator, right_part, position_start=pos[0], position_end=pos[1])
        return current_subtree

    # --- Precedence level 5: Bit shifts ---
    def parse_shift(tokens, token_spans):
        """Parse bit-shift operators ``<<`` (left shift) and ``>>`` (right shift).

        Left-associative.  Sits between addition/subtraction and bitwise AND
        in the precedence hierarchy.
        """
        current_subtree = parse_sum(tokens, token_spans)
        while tokens and tokens[0] in ("<<", ">>"):
            operator = tokens.pop(0)
            pos = token_spans.pop(0)  # Sync
            right_part = parse_sum(tokens, token_spans)
            current_subtree = BinOp(current_subtree, operator, right_part, position_start=pos[0], position_end=pos[1])
        return current_subtree

    # --- Precedence level 6: Addition and subtraction ---
    def parse_sum(tokens, token_spans):
        """Parse addition (``+``) and subtraction (``-``).

        Left-associative.  Delegates higher-precedence operations to
        ``parse_term``.
        """
        current_subtree = parse_term(tokens, token_spans)
        while tokens and tokens[0] in ("+", "-"):
            operator = tokens.pop(0)
            pos = token_spans.pop(0)  # Sync
            right_part = parse_term(tokens, token_spans)
            current_subtree = BinOp(current_subtree, operator, right_part, position_start=pos[0], position_end=pos[1])
        return current_subtree

    # --- Precedence level 2: Bitwise OR ---
    def parse_bor(tokens, token_spans):
        """Parse bitwise OR (``|``).

        Lowest-precedence binary bitwise operator.  Left-associative.
        """
        current_subtree = parse_bxor(tokens, token_spans)
        while tokens and tokens[0] == "|":
            operator = tokens.pop(0)
            pos = token_spans.pop(0)  # Sync
            right_part = parse_bxor(tokens, token_spans)
            current_subtree = BinOp(current_subtree, operator, right_part, position_start=pos[0], position_end=pos[1])
        return current_subtree

    # --- Precedence level 3: Bitwise XOR ---
    def parse_bxor(tokens, token_spans):
        """Parse bitwise XOR (``^``).  Left-associative."""
        current_subtree = parse_band(tokens, token_spans)
        while tokens and tokens[0] == "^":
            operator = tokens.pop(0)
            pos = token_spans.pop(0)  # Sync
            right_part = parse_band(tokens, token_spans)
            current_subtree = BinOp(current_subtree, operator, right_part, position_start=pos[0], position_end=pos[1])
        return current_subtree

    # --- Precedence level 4: Bitwise AND ---
    def parse_band(tokens, token_spans):
        """Parse bitwise AND (``&``).  Left-associative."""
        current_subtree = parse_shift(tokens, token_spans)
        while tokens and tokens[0] == "&":
            operator = tokens.pop(0)
            pos = token_spans.pop(0)  # Sync
            right_part = parse_shift(tokens, token_spans)
            current_subtree = BinOp(current_subtree, operator, right_part, position_start=pos[0], position_end=pos[1])
        return current_subtree

    # --- Precedence level 1 (lowest): Equation / equality ---
    def parse_gleichung(tokens, token_spans):
        """Parse a top-level equation (``=``) if present.

        If no ``=`` is found the expression is returned as-is.  When ``=``
        is present, a ``BinOp('=', left, right)`` node is constructed so
        that :func:`solve` or the equality checker can inspect both sides.
        """
        left_side = parse_bor(tokens, token_spans)
        if tokens and tokens[0] == "=":
            operator = tokens.pop(0)
            pos = token_spans.pop(0)  # Sync
            right_part = parse_shift(tokens, token_spans)
            return BinOp(left_side, operator, right_part)
        return left_side

    # --- Build the final AST from the full token stream ---
    final_tree = parse_gleichung(analysed, token_spans)

    # Determine whether the expression is an equation (CAS mode).
    # ``cas`` is True whenever the root node is ``BinOp('=')``, regardless of
    # how many variables are present.  The caller uses ``cas`` together with
    # ``var_counter`` to choose between solving, equality checking, or erroring.
    if isinstance(final_tree, BinOp) and final_tree.operator == '=' and var_counter <= 1:
        cas = True
    if isinstance(final_tree, BinOp) and final_tree.operator == '=' and var_counter > 1:
        cas = True

    if debug == True:
        print("Final AST:")
        print(final_tree)

    # `cas` may or may not be set above; default to False
    cas = locals().get('cas', False)
    return final_tree, cas, var_counter, expected_bool


# -----------------------------
# Linear solver (one variable)
# -----------------------------

def solve(tree, var_name):
    """Solve a linear equation ``(A*x + B) = (C*x + D)`` for *x*.

    Uses ``collect_term()`` on both sides of the ``=`` node to decompose
    the expression into ``(factor, constant)`` pairs, then computes:

        x = (D - B) / (A - C)

    Args:
        tree:     The root ``BinOp`` node with ``operator='='``.
        var_name: The internal variable name (e.g., ``"var0"``).

    Returns:
        Decimal: The solution value.
        str:     ``"Inf. Solutions"`` if A==C and B==D.
        str:     ``"No Solution"`` if A==C and B!=D.

    Raises:
        E.SolverError: If the tree is not a valid equation (code ``3012``).
    """
    if not isinstance(tree, BinOp) or tree.operator != '=':
        raise E.SolverError("No valid equation to solve.", code="3012")
    (A, B) = tree.left.collect_term(var_name)
    (C, D) = tree.right.collect_term(var_name)
    denominator = A - C
    numerator = D - B
    if denominator == 0:
        if numerator == 0:
            return "Inf. Solutions"
        else:
            return "No Solution"
    return numerator / denominator


# -----------------------------
# Result formatting
# -----------------------------

def cleanup(result):
    """Format a raw numeric result according to the active settings.

    Processing order:
        1. If ``fractions=True`` and result is ``Decimal``: converts to a
           ``Fraction``, rendered as a mixed number (e.g., ``"1 1/2"``)
           or simple fraction (e.g., ``"1/3"``).
        2. If result is ``Decimal`` integer: returned as-is.
        3. If result is ``Decimal`` non-integer: rounded to ``decimal_places``.
        4. Legacy ``int``/``float`` handling for non-Decimal results.

    Args:
        result: The raw evaluation result (typically ``Decimal``).

    Returns:
        tuple: ``(formatted_value, rounding_flag)`` where *rounding_flag*
               is ``True`` if decimal rounding was applied.
    """
    rounding = locals().get('rounding', False)

    target_decimals = config_manager.load_setting_value("decimal_places")
    target_fractions = config_manager.load_setting_value("fractions")

    # Try Fraction rendering if enabled and the result is Decimal
    if target_fractions == True and isinstance(result, Decimal):
        try:
            fraction_result = fractions.Fraction.from_decimal(result)
            simplified_fraction = fraction_result.limit_denominator(100000)
            numerator = simplified_fraction.numerator
            denominator = simplified_fraction.denominator
            if abs(numerator) > denominator:
                # Mixed fraction form (e.g., 3/2 -> "1 1/2")
                integer_part = numerator // denominator
                remainder_numerator = numerator % denominator

                if remainder_numerator == 0:
                    return str(integer_part), rounding
                else:
                    # Adjust for negatives so that the remainder part is positive
                    if integer_part < 0 and remainder_numerator > 0:
                        integer_part += 1
                        remainder_numerator = abs(denominator - remainder_numerator)
                    return f"{integer_part} {remainder_numerator}/{denominator}", rounding

            return str(simplified_fraction), rounding

        except Exception as e:
            # Surface as CalculationError (preserves UI error handling)
            raise E.CalculationError(f"Warning: Fraction conversion failed: {e}", code="3024")

    if isinstance(result, Decimal):

        # --- Smarter Rounding Logic ---
        #
        # Handles rounding for Decimal results with dynamic precision.
        # Integers are returned as-is (just normalized),
        # while non-integers are rounded to 'target_decimals'.
        #
        # A temporary precision boost (prec=128) prevents
        # Decimal.InvalidOperation during quantize() for long or repeating numbers.
        # After rounding, precision is reset to the global standard (50).
        #

        if result % 1 == 0:
            # Integer result – return normalized without rounding
            return result, rounding
        else:
            # Non-integer result (e.g. 1/3 or repeating decimals)
            getcontext().prec = 10000  # Prevent quantize overflow

            if target_decimals >= 0:
                rounding_pattern = Decimal('1e-' + str(target_decimals))
            else:
                rounding_pattern = Decimal('1')

            rounded_result = result.quantize(rounding_pattern)
            getcontext().prec = 10000  # Restore standard precision

            if rounded_result != result:
                rounding = True

            return rounded_result, rounding


    # Legacy float/int handling (in case evaluation produced non-Decimal)
    elif isinstance(result, (int, float)) and not isinstance(result, bool):
        if result == int(result):
            return int(result), rounding

        else:
            s_result = str(result)
            if '.' in s_result:
                decimal_index = s_result.find('.')
                actual_decimals = len(s_result) - decimal_index - 1
                if actual_decimals > target_decimals:
                    rounding = True
                    new_number = round(result, target_decimals)
                    return new_number, rounding

                return result, rounding
            return result, rounding

    # Fallback: unknown type, return as-is
    return result, rounding




# -----------------------------
# Public entry point
# -----------------------------

def calculate(problem: str, custom_variables: Union[dict, None] = None, validate : int = 0):
    """Main calculation entry point: parse, evaluate, format, and return.

    This is the function called by :func:`math_engine.evaluate`.  It
    orchestrates the entire pipeline:

    1. Dynamic Decimal precision scaling based on input sizes
    2. Output prefix extraction and normalization (e.g., ``hex:`` → ``hexadecimal:``)
    3. AST construction via :func:`ast`
    4. Evaluation path selection (numeric / solve / equality check)
    5. Result formatting via :func:`cleanup` and :func:`apply_word_limit`
    6. Output type conversion based on the prefix
    7. Exception normalization (all exceptions wrapped as ``MathError``)

    Args:
        problem:          The expression string (prefix already included).
        custom_variables: Variable context dictionary, or ``None``.
        validate:         ``0`` = parse only (return AST), ``1`` = full evaluate.

    Returns:
        The typed result (``Decimal``, ``int``, ``float``, ``bool``, ``str``),
        or the AST tree when ``validate=0``.

    Raises:
        E.MathError: (or subclass) on any parsing, evaluation, or conversion failure.
    """
    if custom_variables is None:
        custom_variables = {}
    # Guard precision locally before each calculation (UI may adjust as well)
    getcontext().prec = 10000
    settings = config_manager.load_setting_value("all")  # pass UI settings down to parser
    global debug
    debug = settings.get("debug", False)
    target_places = settings.get("decimal_places", 2)

    # -------------------------------------------------------------------
    # Dynamic Decimal precision scaling
    # -------------------------------------------------------------------
    # The global Decimal context precision is tuned per-calculation so that
    # it is always large enough to represent the input numbers and the
    # desired output decimal places without silent truncation, yet not
    # wastefully large (capped at 10 000 to avoid excessive memory use).
    #
    # The formula: needed = max(MIN_PRECISION,
    #                           max_input_digits + BUFFER,
    #                           max_variable_digits + BUFFER,
    #                           target_decimal_places + BUFFER)
    # -------------------------------------------------------------------
    input_numbers = re.findall(r'\d+(?:\.\d+)?', problem)

    max_input_length = len(max(input_numbers, key=len)) if input_numbers else 0

    MAX_DIGIT_LIMIT = 20000
    if max_input_length > MAX_DIGIT_LIMIT:
        raise E.CalculationError(
            f"Input number exceeds limit of {MAX_DIGIT_LIMIT} digits.",
            code="3026",
            equation=problem
        )

    # Also account for the digit length of variable values supplied by the caller.
    max_var_length = 0
    for val in custom_variables.values():
        s_val = str(val)
        clean_len = len(s_val.replace('.', '').replace('-', ''))
        if clean_len > max_var_length:
            max_var_length = clean_len

    SAFETY_BUFFER = 50
    MIN_PRECISION = 100

    needed_precision = max(
        MIN_PRECISION,
        max_input_length + SAFETY_BUFFER,
        max_var_length + SAFETY_BUFFER,
        target_places + SAFETY_BUFFER
    )

    needed_precision = min(needed_precision, 10000)
    getcontext().prec = needed_precision

    if debug == True:
        print(f"[DEBUG] Precision set to: {needed_precision} (Input: {max_input_length}, Target: {target_places})")
    # -------------------------------------------------------------------
    # Output prefix extraction and normalization
    # -------------------------------------------------------------------
    # The user can prepend a type-prefix to the expression to control the
    # Python type of the return value (e.g., "hex:255" -> "0xFF").
    # Short aliases ("h:", "d:", "f:", ...) are normalised to their full
    # canonical form ("hexadecimal:", "decimal:", "float:", ...).
    # After detection the prefix is stripped from ``problem`` so the
    # tokenizer receives a clean mathematical expression.
    # -------------------------------------------------------------------
    var_list = []
    allowed_prefix = (
        "dec:", "d:", "Decimal:",
        "int:", "i:", "integer:",
        "float:", "f:",
        "bool:", "bo", "boolean:",
        "hex:", "h:", "hexadecimal:",
        "str:", "s:", "string:",
        "bin:", "bi:", "binary:",
        "oc:", "o:", "octal:"
    )
    output_prefix = ""
    problem_lower = problem.lower()
    try:
        # Try each known prefix (case-insensitive) and normalise to canonical form.
        for prefix in allowed_prefix:
            if problem_lower.startswith(prefix):
                if prefix.startswith("s")or prefix.startswith("S"):
                    output_prefix = "string:"
                elif prefix.startswith("bo")or prefix.startswith("Bo"):
                    output_prefix = "boolean:"
                elif prefix.startswith("d") or prefix.startswith("D"):
                    output_prefix = "decimal:"
                elif prefix.startswith("f") or prefix.startswith("F"):
                    output_prefix = "float:"
                elif prefix.startswith("i") or prefix.startswith("I"):
                    output_prefix = "int:"
                elif prefix.startswith("h") or prefix.startswith("H"):
                    output_prefix = "hexadecimal:"
                elif prefix.startswith("bi") or prefix.startswith("Bi"):
                    output_prefix = "binary:"
                elif prefix.startswith("o") or prefix.startswith("O"):
                    output_prefix = "octal:"

                # Strip the prefix (including the ':') from the expression.
                start = problem.index(":")
                problem = problem[start+1:]
                break


        # --- AST construction ---
        final_tree, cas, var_counter, expected_bool = ast(problem, settings, custom_variables)

        # --- Reconcile expected_bool with user-specified prefix ---
        # When '==' was detected (expected_bool=True) but the user supplied a
        # non-boolean prefix, behaviour depends on the ``correct_output_format``
        # setting: if False -> error; if True -> silently override to boolean.
        if output_prefix != "boolean:" and expected_bool == True and output_prefix != "" and settings["correct_output_format"]== False:
            raise E.SyntaxError("Couldnt convert result into the given prefix", code="3037")

        elif output_prefix != "boolean:" and expected_bool == True and output_prefix == "":
            output_prefix = "boolean:"

        elif output_prefix != "boolean:" and expected_bool == True and settings["correct_output_format"]== True:
            output_prefix = "boolean:"

        # When ``only_*`` mode is active and no explicit prefix was provided,
        # default the output to the corresponding base representation.
        if output_prefix == "" and settings["only_hex"] == True:
            output_prefix = "hexadecimal:"
        elif output_prefix == "" and settings["only_binary"] == True:
            output_prefix = "binary:"
        elif output_prefix == "" and settings["only_octal"] == True:
            output_prefix = "octal:"

        if validate == 0:
            result = final_tree

        # -------------------------------------------------------------------
        # Evaluation path decision tree
        # -------------------------------------------------------------------
        # The combination of ``cas`` (equation detected) and ``var_counter``
        # (number of distinct variables) determines which evaluation strategy
        # is used:
        #
        #   cas=True,  var_counter>0  -> SOLVE:  linear equation solver
        #   cas=False, var_counter==0 -> EVALUATE: pure numeric evaluation
        #   cas=True,  var_counter==0 -> EQUALITY CHECK: compare both sides
        #   (other)                   -> ERROR: invalid combination
        # -------------------------------------------------------------------
        if cas and var_counter > 0:
            # --- Path 1: Solve linear equation for the first variable ---
            var_name_in_ast = "var0"
            if settings["only_hex"] == True or settings["only_binary"] == True or settings["only_octal"] == True:
                raise E.SolverError("Variables not supported with only_hex, only_binary or only_octal mode.",
                                    code="3038")
            if validate == 1:
                result = solve(final_tree, var_name_in_ast)

        elif not cas and var_counter == 0:
            # --- Path 2: Pure numeric evaluation (no equation, no variables) ---
            if validate == 1:
                result = final_tree.evaluate()

        elif cas and var_counter == 0:
            # --- Path 3: Pure equality check (equation but no variables) ---
            # Evaluates both sides independently and compares them.
            if output_prefix == "":
                output_prefix = "boolean:"
            left_val = final_tree.left.evaluate()
            right_val = final_tree.right.evaluate()
            output_string = "True" if left_val == right_val else "False"
            if validate == 1:
                result = (left_val == right_val)
            if output_prefix != "boolean:" and output_prefix != "string:" and output_prefix != "":
                raise E.ConversionOutputError("Couldnt convert result into the given prefix", code = "8006")
            if output_prefix == "boolean:":
                try:
                    boolean(output_string)
                    #return boolean(output_string)
                except Exception as e:
                    raise E.ConversionError("Couldnt convert type to" + str(output_prefix), code="8003")

        else:
            # --- Path 4: Invalid / unsupported combinations ---
            if cas:
                raise E.SolverError("The solver was used on a non-equation", code="3005")
            elif not cas and not "=" in problem:
                if settings["only_hex"] == True or settings["only_binary"] == True or settings["only_octal"] == True:
                    raise E.SolverError("Variables not supported with only_hex, only_binary or only_octal mode.", code="3038")
                raise E.SolverError("No '=' found, although a variable was specified.", code="3012")
            elif cas and "=" in problem and (
                    problem.index("=") == 0 or problem.index("=") == (len(problem) - 1)):
                raise E.SolverError("One of the sides is empty: " + str(problem), code="3022")
            elif cas and var_counter>1:
                raise E.SolverError("Multiple Variables found.", error = "")
            else:
                raise E.CalculationError("The calculator was called on an equation.", code="3015")

        # --- Result formatting ---
        # Pass the raw numeric result through cleanup() for fraction rendering
        # and decimal rounding, then enforce any configured word/bit limit.
        if validate == 1:
            result, rounding = cleanup(result)
            result = apply_word_limit(result, settings)
        approx_sign = "\u2248"  # "approx" sign used when rounding was applied
        if validate == 1:
            # ---------------------------------------------------------------
            # Output type conversion based on the extracted prefix
            # ---------------------------------------------------------------
            # Converts the (possibly rounded) result into the Python type
            # requested by the user's prefix.  Each branch attempts the
            # conversion and wraps failures in ``ConversionOutputError``.
            # ---------------------------------------------------------------
            if isinstance(result, str) and '/' in result:
                output_string = result

            elif isinstance(result, Decimal):
                # Threshold for scientific notation: 1 Billion (1e9)
                scientific_threshold = Decimal('1e9')
                output_string = result
                if result.is_zero():
                    output_string = "0"

            else:
                output_string = result
            # Fall back to the engine's configured default output format when
            # no explicit prefix was specified by the user.
            if output_prefix == "":
                output_prefix = settings["default_output_format"]
            if output_prefix == "decimal:":
                try:
                    Decimal(output_string)
                    return Decimal(output_string)
                except Exception as e:
                    raise E.ConversionOutputError("Couldnt convert type to" + str(output_prefix), code="8003")

            elif output_prefix == "string:":
                try:
                    return str(output_string)
                except Exception as e:
                    raise E.ConversionOutputError("Couldnt convert type to" + str(output_prefix), code="8003")

            elif output_prefix == "hexadecimal:":
                try:
                    int_to_value(output_string, output_prefix, settings)
                    return int_to_value(output_string, output_prefix, settings)
                except Exception as e:
                    raise E.ConversionOutputError("Couldnt convert type to" + str(output_prefix), code="8003")

            elif output_prefix == "binary:":
                try:
                    int_to_value(output_string, output_prefix, settings)
                    return int_to_value(output_string, output_prefix, settings)
                except Exception as e:
                    raise E.ConversionOutputError("Couldnt convert type to" + str(output_prefix), code="8003")
            elif output_prefix == "octal:":
                try:
                    int_to_value(output_string, output_prefix, settings)
                    return int_to_value(output_string, output_prefix, settings)
                except Exception as e:
                    raise E.ConversionOutputError("Couldnt convert type to" + str(output_prefix), code="8003")

            elif output_prefix == "boolean:":
                try:
                    boolean(output_string)
                    return boolean(output_string)
                except Exception as e:
                    raise E.ConversionOutputError("Couldnt convert type to" + str(output_prefix), code = "8003")


            elif output_prefix == "int:":
                try:
                    int_value = int(output_string)
                    float_value = float(output_string)
                    if int_value != float_value:
                        raise E.ConversionOutputError(
                            f"Cannot convert non-integer value '{output_string}' to exact integer.",
                            code="8005"
                        )
                    else:
                        return int(output_string)
                except Exception as e:
                    raise E.ConversionOutputError("Couldnt convert type to" + str(output_prefix), code="8003")

            elif output_prefix == "float:":
                try:
                    float(output_string)
                    return float(output_string)
                except Exception as e:
                    raise E.ConversionOutputError("Couldnt convert type to" + str(output_prefix), code="8003")

            else:
                raise E.SyntaxError("Unknown Error", code = "9999")
        else:
            return result


    # -------------------------------------------------------------------
    # Exception wrapping
    # -------------------------------------------------------------------
    # All exceptions raised during the pipeline above are caught here and
    # normalised into the project's ``E.MathError`` hierarchy so that
    # callers only need to handle one base exception type.
    #
    # Layer 1: Decimal arithmetic overflow / invalid operations -> CalculationError
    # Layer 2: Output-format conversion failures -> ConversionError
    # Layer 3: Domain-specific MathError subclasses -> re-raised with the
    #          source equation attached for diagnostics.
    # Layer 4: Any other Python built-in exception -> wrapped in MathError
    #          with code "9999" (unknown error) or the embedded 4-digit code
    #          if the message string already starts with one.
    # -------------------------------------------------------------------
    except (Overflow, DivisionImpossible, InvalidOperation) as e:
        raise E.CalculationError(
            message="Number too large or invalid operation (Arithmetic overflow).",
            code="3026",
            equation=problem
        )
    except E.ConversionOutputError as e:
            raise E.ConversionError(
                f"Couldnt convert result '{output_string}' into '{output_prefix}'",
                code="8006"
            )
    except E.MathError as e:
        # Attach the original expression for downstream error reporting.
        e.equation = problem
        raise e
    except (ValueError, SyntaxError, ZeroDivisionError, TypeError, Exception) as e:
        # Catch-all: wrap any unexpected Python exception as MathError.
        error_message = str(e).strip()
        parts = error_message.split(maxsplit=1)
        code = "9999"
        message = error_message

        # If the error string already begins with a 4-digit code, extract it.
        if parts and parts[0].isdigit() and len(parts[0]) == 4:
            code = parts[0]
            if len(parts) > 1:
                message = parts[1]
        raise E.MathError(message=message, code=code, equation=problem)


def test_main():
    """Simple recursive REPL for manual testing of the calculation engine.

    Reads an expression from stdin, evaluates it, prints the result,
    and loops.  Only intended for standalone development testing.
    """
    print("Enter the problem: ")
    problem = input()
    result = calculate(problem)
    print(result)
    test_main()  # recursive call disabled

if __name__ == "__main__":
    test_main()
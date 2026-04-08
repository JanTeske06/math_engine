"""
Standalone tokenizer module (earlier / alternative version).

This module contains a self-contained implementation of the tokenizer that
mirrors the logic found in :func:`calculator.calculator.translator`.  It is
**not imported** by any other module in the current production codebase and
is retained for reference, debugging, and standalone testing via its
``__main__`` block.

The tokenizer converts a raw mathematical expression string (e.g.
``"2x + sin(3.14)"``) into a flat list of tokens -- ``Decimal`` numbers,
operator strings, parentheses, internal variable placeholders (``"var0"``,
``"var1"``, ...), and scientific-function names.  It also records the
source-position span of every token so that later stages can produce
accurate error messages.

Key data structures defined at module level
-------------------------------------------
- :data:`Operations` -- single- and double-character arithmetic / bitwise
  operator strings recognised during tokenization.
- :data:`Science_Operations` -- scientific function and constant names
  (informational; the actual matching uses :data:`RAW_FUNCTION_MAP`).
- :data:`Bit_Operations` -- named bitwise-operation functions.
- :data:`RAW_FUNCTION_MAP` -- maps the literal prefix that appears in the
  input (e.g. ``"sin("``) to the canonical token name (e.g. ``"sin"``).
- :data:`PURE_FUNCTION_NAMES` -- set of canonical tokens that represent
  callable functions (derived from entries in ``RAW_FUNCTION_MAP`` whose
  prefix ends with ``"("``).
- :data:`FUNCTION_STARTS_OPTIMIZED` -- pre-computed ``{prefix: (token,
  prefix_length)}`` dict for O(1) prefix look-ups inside the main loop.

See :func:`calculator.calculator.translator` for the actively-used version
of the tokenizer.
"""

from decimal import Decimal
from math_engine.utility.utility import isInt, isfloat, isScOp, isOp
from math_engine import config_manager as config_manager
from math_engine.calculator import ScientificEngine
from ..utility import error as E
from math_engine.utility.non_decimal_utility import value_to_int, non_decimal_scan

# ---------------------------------------------------------------------------
# Token classification lists
# ---------------------------------------------------------------------------

# Arithmetic and bitwise operator characters recognised by the tokenizer.
Operations = ["+", "-", "*", "/", "=", "^", ">>", "<<", "<", ">", "|","&" ]

# Scientific function / constant names (informational reference list).
Science_Operations = ["sin", "cos", "tan", "10^x", "log", "e^", "π", "√"]

# Named bitwise-operation functions (e.g. setbit, bitnot, shl, ...).
Bit_Operations = ["setbit", "bitxor", "shl", "shr", "bitnot", "bitand", "bitor", "clrbit", "togbit", "testbit"]

# Reserved for dynamically-registered plugin operations (currently unused).
plugin_operations = []

# Maps the literal prefix as it appears in the raw input string to the
# canonical token name emitted into the token list.  Entries whose key
# ends with '(' are "callable" functions; the opening parenthesis is
# re-emitted as a separate '(' token by the main loop.
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

# Set of canonical token names that are callable functions (i.e. require
# a parenthesized argument list).  Derived from RAW_FUNCTION_MAP entries
# whose prefix key ends with '('.
PURE_FUNCTION_NAMES = {
    token for start_str, token in RAW_FUNCTION_MAP.items()
    if start_str.endswith('(')
}

# Pre-computed look-up dict: maps each prefix string to a (token, length)
# tuple so the main scanning loop can match and advance in O(1) per prefix.
FUNCTION_STARTS_OPTIMIZED = {
    start_str: (token, len(start_str))
    for start_str, token in RAW_FUNCTION_MAP.items()
}


def translator(problem, custom_variables, settings):
    """Convert a raw mathematical expression string into a token list.

    The tokenizer scans *problem* left-to-right in a single pass (Phase 1),
    producing a flat list of tokens (``Decimal`` numbers, operator strings,
    parentheses, function names, and internal variable placeholders like
    ``"var0"``).  A second pass (Phase 2) inserts implicit multiplication
    tokens wherever two adjacent tokens imply multiplication (e.g.
    ``"5x"`` becomes ``[Decimal('5'), '*', 'var0']``).

    Parameters
    ----------
    problem : str
        The raw input expression (e.g. ``"2x + sin(3.14)"``).
    custom_variables : dict
        Mapping of user-defined variable names to their values.  Known
        variables are substituted with their numeric value during
        tokenization; unknown single-character names become internal
        ``"varN"`` placeholders for the solver.
    settings : dict
        Runtime settings dict.  Relevant keys include ``"only_hex"``,
        ``"only_binary"``, and ``"only_octal"`` which control the
        numeric base used when parsing bare digit sequences.

    Returns
    -------
    tuple[list, int, list[tuple]]
        - ``full_problem`` -- ordered list of tokens.
        - ``var_counter``  -- number of distinct unknown variables found.
        - ``token_spans``  -- list of ``(start, end, raw_text)`` tuples
          recording the source position of each token (used for error
          reporting).

    Notes
    -----
    - The Unicode character ``'\\u2248'`` (approximately equal) is
      silently mapped to ``'='`` so the rest of the pipeline can handle
      equality uniformly.
    - Implicit multiplication is inserted between a number/variable/')'
      and an opening '(' / number / variable / function name.
    """

    # ------------------------------------------------------------------ #
    #  Initialisation
    # ------------------------------------------------------------------ #
    var_counter = 0
    var_list = [None] * len(problem)  # Track seen variable symbols -> var0, var1, ...
    full_problem = []    # Accumulates the output token list
    token_spans = []     # Parallel list of (start_pos, end_pos, raw_text)
    b = 0                # Current scan index into *problem*

    # ------------------------------------------------------------------ #
    #  Pre-processing: build a look-up of context variables
    # ------------------------------------------------------------------ #
    # Convert all caller-supplied variable values to string form so they
    # can be compared / substituted during the scan.
    CONTEXT_VARS = {}
    for var_name, value in custom_variables.items():
        if isinstance(value, (int, float, Decimal)):
            CONTEXT_VARS[var_name] = str(value)
        elif isinstance(value, bool):
            CONTEXT_VARS[var_name] = "1" if value else "0"
        else:
            CONTEXT_VARS[var_name] = str(value)

    # Sort by descending length so that longer variable names are matched
    # before shorter prefixes (e.g. "xy" before "x").
    sorted_vars = sorted(CONTEXT_VARS.keys(), key=len, reverse=True)
    HEX_DIGITS = "0123456789ABCDEFabcdef"
    temp_problem = problem
    # (Commented-out block: inline variable substitution was moved to the
    #  per-token variable look-up below.)
    # for var_name in sorted_vars:
    #     value_str = CONTEXT_VARS[var_name]
    #     value_str = value_str
    #     temp_problem = temp_problem.replace(var_name, value_str)

    problem = temp_problem

    # ================================================================== #
    #  PHASE 1 -- Main left-to-right character scan
    # ================================================================== #
    # Each iteration classifies the character(s) at position *b* and
    # emits the corresponding token(s) into *full_problem*.  The order
    # of the checks below matters: function-prefix matching is attempted
    # first, then numeric literals, operators, whitespace, parentheses,
    # hex digits (when in hex-only mode), the pi constant, and finally
    # the variable / unknown-identifier fallback.
    temp_var = -1
    while b < len(problem):
        found_function = False
        current_char = problem[b]

        # --- Function-prefix matching (sin(, cos(, log(, sqrt(, ...) ---
        # Try each known prefix against the current position.  On match,
        # emit the canonical token and, for callable functions, also emit
        # a separate '(' token.
        for start_str, (token, length) in FUNCTION_STARTS_OPTIMIZED.items():
            if problem.startswith(start_str, b):
                full_problem.append(token)
                token_spans.append((b, b+len(token)-1, token))
                # Constants like pi do not get an opening parenthesis;
                # functions like sin/log do.
                if token != "π" and token != "E" and token != "e":
                    full_problem.append("(")
                    token_spans.append((b+len(token), b+len(token), "("))

                b += length - 0
                found_function = True
                break
        if found_function:
            # Scientific functions are not available in non-decimal modes
            if settings["only_hex"] == True or settings["only_binary"] == True or settings["only_octal"]== True:
                raise E.SyntaxError(f"Function not support with only not decimals.", code="3033")
            continue

        # --- Numeric literal scanning ---
        # Handles integers, floats, and scientific (exponential) notation
        # such as "1.5e-3".  First tries a non-decimal (hex/bin/oct) scan;
        # if that returns None, falls back to the general decimal scanner.
        if isInt(current_char) or (b >= 0 and current_char == "."):
            start_index = b

            # Attempt non-decimal (hex/binary/octal prefix) scan first
            parsed_value, new_index = non_decimal_scan(problem, b, settings)

            if parsed_value is not None:
                # Non-decimal literal recognised (e.g. 0xFF, 0b1010)
                original_str = problem[start_index:new_index]
                token_spans.append((start_index, new_index, original_str))
                full_problem.append(parsed_value)
                b = new_index - 1

            else:
                # General decimal number scanner -- accumulates digits,
                # at most one decimal point, and optional exponent part.
                str_number = current_char
                has_decimal_point = (current_char == '.')
                has_exponent_e = False

                while (b + 1 < len(problem)):
                    next_char = problem[b + 1]

                    # 1. Decimal point -- only one allowed per number
                    if next_char == ".":
                        if has_decimal_point:
                            raise E.SyntaxError(f"Double decimal point.", code="3008", position_start=b + 1)
                        has_decimal_point = True

                    # 2. Exponent indicator 'E' / 'e' -- only one allowed
                    elif next_char in ('e', 'E'):
                        if temp_var == b and b > 0:
                            raise E.SyntaxError(f"Multiple digit variables not supported.",
                                                code="3032", position_start=b + 1)
                        if has_exponent_e:
                            raise E.SyntaxError("Double exponent sign 'E'/'e'.", code="3031", position_start=b + 1)
                        has_exponent_e = True

                    # 3. Sign character ('+'/'-') is valid only immediately
                    #    after the exponent indicator
                    elif next_char in ('+', '-'):
                        if not (problem[b] in ('e', 'E') and has_exponent_e):
                            break

                    # 4. Any non-digit character ends the number
                    elif not isInt(next_char):
                        break

                    # Character is a valid continuation of this number
                    b += 1
                    str_number += problem[b]

                # Convert the accumulated string to a Decimal token,
                # applying base conversion if a non-decimal mode is active
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
                    # Incomplete exponent notation (e.g. "3e" with no digits)
                    if has_exponent_e and not str_number[-1].isdigit():
                        raise E.SyntaxError("Missing exponent value after 'E'/'e'.", code="3032", position_start=b)

        # --- Operator scanning ---
        # Recognises single-character operators (+, -, *, /, =, &, |, ^)
        # and two-character operators (**, <<, >>).  Invalid combinations
        # like <> or >< are rejected.
        elif isOp(current_char) != -1:
            start_index = b
            # Check for the two-character power operator '**'
            if current_char == "*" and b + 1 < len(problem) and problem[b + 1] == "*":
                full_problem.append("**")
                token_spans.append((start_index, b + 1, "**"))
                b += 1
            elif current_char != "<" and current_char != ">":
                # Single-character operator (e.g. +, -, *, /, =, &, |, ^)
                full_problem.append(current_char)
                token_spans.append((start_index, b, current_char))
            elif current_char == "<" and b<= len(problem)+1:
                # Left shift '<<' or invalid '<>'
                if problem[b+1] == "<":
                    full_problem.append("<<")
                    token_spans.append((start_index, b + 1, "<<"))
                    b+=1
                elif problem[b+1] == ">":
                    raise E.SyntaxError("Invalid shift Operation <>", code = "3040")

            elif current_char == ">" and b <= len(problem) + 1:
                # Right shift '>>' or invalid '><'
                following_char = problem[b + 1]
                if problem[b + 1] == ">":
                    full_problem.append(">>")
                    token_spans.append((b, b+1, ">>"))
                    b += 1
                elif problem[b+1] == "<":
                    raise E.SyntaxError("Invalid shift Operation ><", code = "3040")

            else:
                raise E.SyntaxError("Unknown Error.", code = "9999")




        # --- Whitespace (ignored -- simply skip) ---
        elif current_char == " ":
            pass

        # --- Parentheses and special single characters ---
        elif current_char == "(":
            full_problem.append("(")
            token_spans.append((b, b, current_char))
        elif current_char == "≈":
            # Map the "approximately equal" sign to plain '=' so the
            # downstream parser handles equality uniformly.
            full_problem.append("=")
            token_spans.append((b, b, current_char))
        elif current_char == ")":
            full_problem.append(")")
            token_spans.append((b, b, current_char))
        elif current_char == ",":
            # Comma separator (used inside function calls like log(x, b))
            full_problem.append(",")
            token_spans.append((b, b, current_char))

        # --- Hex-digit accumulation (only in hex-only mode) ---
        # When the settings enforce hexadecimal input, bare A-F / a-f
        # characters are consumed as part of a hex literal.
        elif settings.get("only_hex", False) and current_char in HEX_DIGITS:
            # Collect all consecutive hex-digit characters (e.g. "FF", "1A3")
            str_number = current_char
            start_index = b
            while b + 1 < len(problem) and problem[b + 1] in HEX_DIGITS:
                b += 1
                str_number += problem[b]

            # Prefix with "0x" and convert to int, then wrap as Decimal
            try:
                int_value = value_to_int("0x" + str_number)
                full_problem.append(Decimal(int_value))
                token_spans.append((start_index, b, str_number))
            except E.ConversionError as e:
                raise

        # --- Pi constant (standalone character) ---
        elif current_char == 'π':
            if settings["only_hex"] == True or settings["only_binary"] == True or settings["only_octal"]== True:
                raise E.SyntaxError(f"Error with constant π:{result_string}", code="3033", position_start=b)
            result_string = ScientificEngine.isPi(str(current_char))
            try:
                calculated_value = Decimal(result_string)
                full_problem.append(calculated_value)
            except ValueError:
                raise E.CalculationError(f"Error with constant π:{result_string}", code="3219", position_start=b)

        # --- Variable / unknown-identifier fallback ---
        # If none of the above branches matched, treat the current
        # position as the start of a variable name or unknown identifier.
        # Accumulate consecutive alphanumeric / underscore characters,
        # then decide whether it is a known custom variable (substitute
        # its value) or a new unknown (assign an internal "varN" name).
        else:
                start_index = b
                var_name = ""
                # Greedily collect the full identifier
                while b < len(problem):
                    char = problem[b]
                    if char.isalnum() or char == '_':
                        var_name += char
                        b += 1
                    else:
                        break

                if len(var_name) == 0:
                    # Not even a single valid identifier character found
                    raise E.SyntaxError(f"Unexpected token: {current_char}", code="3012", position_start=b)

                # Guard: reject identifiers that start with a known
                # function name but are missing the required '('.
                for func_name in PURE_FUNCTION_NAMES:
                    if var_name.startswith(func_name):
                        raise E.SyntaxError(
                            f"Function name '{func_name}' must be followed by '('.",
                            code="3010", position_start=start_index + len(func_name) - 1
                        )

                if var_name in custom_variables:
                    # Known variable -- substitute its numeric value
                    val = custom_variables[var_name]
                    if isinstance(val, (int, float)):
                        val = Decimal(val)
                    elif isinstance(val, bool):
                        val = Decimal(1) if val else Decimal(0)

                    full_problem.append(val)
                    token_spans.append((start_index, b, var_name))
                    b = b - 1

                else:
                    # Unknown variable -- only single-character names are
                    # accepted as solver unknowns; longer names are errors.
                    if len(var_name) > 1:
                        raise E.SyntaxError(f"Unknown function or variable too long: '{var_name}'", code="3011",
                                            position_start=start_index, position_end=b)

                    # Re-use existing internal name if the same symbol was
                    # already encountered, otherwise assign a new "varN".
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

    # ================================================================== #
    #  PHASE 2 -- Implicit multiplication insertion
    # ================================================================== #
    # Walk the token list and insert a '*' token between any two adjacent
    # tokens that mathematically imply multiplication.  Examples:
    #   "5x"      ->  5  *  var0        (number followed by variable)
    #   "2(3)"    ->  2  *  (  3  )     (number followed by open paren)
    #   "(a)(b)"  ->  )  *  (           (close paren followed by open paren)
    #   "x sin"   ->  var0  *  sin      (variable followed by function name)
    #
    # The inserted token is tracked in token_spans as "*_impl" so that
    # debugging / error reporting can distinguish it from user-written '*'.
    b = 0
    while b < len(full_problem):

        if b + 1 < len(full_problem):

            current_element = full_problem[b]
            successor = full_problem[b + 1]
            insertion_needed = False

            # Classify the current and next tokens
            is_function_name = isScOp(successor) != -1
            is_number_or_variable = isinstance(current_element, (int, float, Decimal)) or (
                        "var" in str(current_element) and
                        isinstance(current_element, str))
            is_paren_or_variable_or_number = (
                        successor == '(' or ("var" in str(successor) and isinstance(successor, str)) or
                        isinstance(successor, (int, float, Decimal)) or is_function_name)
            is_not_an_operator = current_element not in Operations and successor not in Operations

            # Implicit multiplication is needed when the left token is a
            # "value-like" token (number, variable, ')') and the right
            # token is also "value-like" (number, variable, '(', function).
            if (is_number_or_variable or current_element == ')') and \
                    (is_paren_or_variable_or_number or successor == '(') and \
                    is_not_an_operator:

                # Exclude cases where an explicit operator already separates
                # the two tokens, or where the pair is '(' ... ')'.
                if current_element in ['*', '+', '-', '/'] or successor in ['*', '+', '-', '/']:
                    insertion_needed = False
                elif current_element == ')' and successor == '(':
                    insertion_needed = True
                elif current_element != '(' and successor != ')':
                    insertion_needed = True

            if insertion_needed:
                # Insert the implicit '*' into both the token list and the
                # span list so indices stay synchronised.
                next_pos = token_spans[b + 1][0] if b + 1 < len(token_spans) else b
                token_spans.insert(b + 1, (next_pos, next_pos, "*_impl"))
                full_problem.insert(b + 1, '*')

        b += 1
    return full_problem, var_counter, token_spans

# ---------------------------------------------------------------------------
#  Standalone test harness
# ---------------------------------------------------------------------------
# Run this file directly (``python -m math_engine.calculator.translator``)
# to tokenize a hard-coded test expression and print the resulting tokens,
# variable count, and source-position spans.
if __name__ == '__main__':
    settings = config_manager.load_setting_value("all")
    parameters = {"Level": 3}
    full_problem, var_counter, token_spans = translator("1 + 1", parameters, settings)
    print("Full Problem: " + str(full_problem))
    print("Variable Counter: " + str(var_counter))
    print("Token Spans: " + str(token_spans))
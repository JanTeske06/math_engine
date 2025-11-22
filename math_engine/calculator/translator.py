from decimal import Decimal
from math_engine.utility.utility import isInt, isfloat, isScOp, isOp
from math_engine import config_manager as config_manager
from math_engine.calculator import ScientificEngine
from ..utility import error as E
from math_engine.utility.non_decimal_utility import value_to_int, non_decimal_scan

Operations = ["+", "-", "*", "/", "=", "^", ">>", "<<", "<", ">", "|","&" ]
Science_Operations = ["sin", "cos", "tan", "10^x", "log", "e^", "π", "√"]
Bit_Operations = ["setbit", "bitxor", "shl", "shr", "bitnot", "bitand", "bitor", "clrbit", "togbit", "testbit"]
plugin_operations = []
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

PURE_FUNCTION_NAMES = {
    token for start_str, token in RAW_FUNCTION_MAP.items()
    if start_str.endswith('(')
}
FUNCTION_STARTS_OPTIMIZED = {
    start_str: (token, len(start_str))
    for start_str, token in RAW_FUNCTION_MAP.items()
}


def translator(problem, custom_variables, settings):
    """Convert raw input string into a token list (numbers, ops, parens, variables, functions).

    Notes:
    - Inserts implicit multiplication where needed (e.g., '5x' -> '5', '*', 'var0').
    - Maps '≈' to '=' so the rest of the pipeline can handle equality uniformly.
    """

    var_counter = 0
    var_list = [None] * len(problem)  # Track seen variable symbols → var0, var1, ...
    full_problem = []
    token_spans = []
    b = 0



    CONTEXT_VARS = {}
    for var_name, value in custom_variables.items():
        if isinstance(value, (int, float, Decimal)):
            CONTEXT_VARS[var_name] = str(value)
        elif isinstance(value, bool):
            CONTEXT_VARS[var_name] = "1" if value else "0"
        else:
            CONTEXT_VARS[var_name] = str(value)

    sorted_vars = sorted(CONTEXT_VARS.keys(), key=len, reverse=True)
    HEX_DIGITS = "0123456789ABCDEFabcdef"
    temp_problem = problem
    # for var_name in sorted_vars:
    #     value_str = CONTEXT_VARS[var_name]
    #     value_str = value_str
    #     temp_problem = temp_problem.replace(var_name, value_str)

    problem = temp_problem

    temp_var = -1
    while b < len(problem):
        found_function = False
        current_char = problem[b]


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

        # --- Numbers: digits and decimal separator (EXPONENTIAL NOTATION SUPPORT ADDED) ---
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

        # --- Operators ---
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

        elif settings.get("only_hex", False) and current_char in HEX_DIGITS:
            # Sammle alle aufeinanderfolgenden Hex-Zeichen (z.B. "FF", "1A3")
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

        # --- Constant π ---
        elif current_char == 'π':
            if settings["only_hex"] == True or settings["only_binary"] == True or settings["only_octal"]== True:
                raise E.SyntaxError(f"Error with constant π:{result_string}", code="3033", position_start=b)
            result_string = ScientificEngine.isPi(str(current_char))
            try:
                calculated_value = Decimal(result_string)
                full_problem.append(calculated_value)
            except ValueError:
                raise E.CalculationError(f"Error with constant π:{result_string}", code="3219", position_start=b)

                # --- Variables (fallback) ---
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

    # --- Implicit multiplication pass ---
    # Insert '*' between adjacent tokens that imply multiplication:
    # number/variable/')' followed by '(' / number / variable / function name
    b = 0
    while b < len(full_problem):

        if b + 1 < len(full_problem):

            current_element = full_problem[b]
            successor = full_problem[b + 1]
            insertion_needed = False

            is_function_name = isScOp(successor) != -1
            is_number_or_variable = isinstance(current_element, (int, float, Decimal)) or (
                        "var" in str(current_element) and
                        isinstance(current_element, str))
            is_paren_or_variable_or_number = (
                        successor == '(' or ("var" in str(successor) and isinstance(successor, str)) or
                        isinstance(successor, (int, float, Decimal)) or is_function_name)
            is_not_an_operator = current_element not in Operations and successor not in Operations

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

if __name__ == '__main__':
    settings = config_manager.load_setting_value("all")
    parameters = {"Level": 3}
    full_problem, var_counter, token_spans = translator("1 + 1", parameters, settings)
    print("Full Problem: " + str(full_problem))
    print("Variable Counter: " + str(var_counter))
    print("Token Spans: " + str(token_spans))
# calculator.py
"""
Core calculation engine for the Advanced Python Calculator.

Pipeline
--------
1) Tokenizer: converts a raw input string into a flat list of tokens.
2) Parser (AST): builds an Abstract Syntax Tree (recursive-descent, precedence aware).
3) Evaluator / Solver:
   - Evaluate pure numeric expressions
   - Solve linear equations with a single variable (e.g. 'x')
4) Formatter: renders results using Decimal/Fraction and user preferences.
"""

from decimal import Decimal, getcontext, Overflow
import fractions
import inspect
from typing import Union
import math
from . import config_manager as config_manager
from . import ScientificEngine
from . import error as E

# Debug toggle for optional prints in this module
debug = False

# Supported operators / functions (kept as simple lists for quick membership checks)
Operations = ["+", "-", "*", "/", "=", "^"]
Science_Operations = ["sin", "cos", "tan", "10^x", "log", "e^", "π", "√"]

# Global Decimal precision used by this module (UI may also enforce this before calls)
getcontext().prec = 10000


# -----------------------------
# Utilities / small helpers
# -----------------------------

def boolean(value):
    try:
        if isinstance(value, (str, bool)):
            if value == "True" or value == True:
                return True
            elif value == "False" or value == False:
                return False
            else:
                raise E.ConversionError("Couldnt convert type to bool", code = "8003")
    except Exception as e:
        raise E.ConversionError("Couldnt convert type to bool", code = "8003")

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
        return Science_Operations.index(token)
    except ValueError:
        return -1


def isOp(token):
    """Return index of a known basic operator or -1 if unknown."""
    try:
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


# -----------------------------
# AST node types
# -----------------------------

class Number:
    """AST node for numeric literal backed by Decimal."""

    def __init__(self, value):
        # Always normalize input to Decimal via string to avoid float artifacts
        if not isinstance(value, Decimal):
            value = str(value)
        self.value = Decimal(value)

    def evaluate(self):
        """Return Decimal value for this literal."""
        return self.value

    def collect_term(self, var_name):
        """Return (factor_of_var, constant) for linear collection."""
        return (0, self.value)

    def __repr__(self):
        # Helpful for debugging/printing the AST
        try:
            display_value = self.value.to_normal_string()
        except AttributeError:
            # Fallback for older Decimal versions
            display_value = str(self.value)
        return f"Number({display_value})"


class Variable:
    """AST node representing a single symbolic variable (e.g. 'var0')."""

    def __init__(self, name):
        self.name = name

    def evaluate(self):
        """Variables cannot be directly evaluated without solving."""
        raise E.SolverError(f"Non linear problem.", code="3005")

    def collect_term(self, var_name):
        """Return (1, 0) if this variable matches var_name; else error."""
        if self.name == var_name:
            return (1, 0)
        else:
            # Only one variable supported in the linear solver
            raise E.SolverError(f"Multiple variables found: {self.name}", code="3002")
            return (0, 0)

    def __repr__(self):
        return f"Variable('{self.name}')"


class BinOp:
    """AST node for a binary operation: left <operator> right."""

    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

    def evaluate(self):
        """Evaluate numeric subtree and apply the binary operator."""
        left_value = self.left.evaluate()
        right_value = self.right.evaluate()

        if self.operator == '+':
            return left_value + right_value
        elif self.operator == '-':
            return left_value - right_value
        elif self.operator == '*':
            return left_value * right_value
        elif self.operator == '^':
            return left_value ** right_value
        elif self.operator == '/':
            if right_value == 0:
                raise E.CalculationError("Division by zero", code="3003")
            return left_value / right_value
        elif self.operator == '=':
            # Equality is evaluated to a boolean (used for "= True/False" responses)
            return left_value == right_value
        else:
            raise E.CalculationError(f"Unknown operator: {self.operator}", code="3004")

    def collect_term(self, var_name):
        """Collect linear terms on this subtree into (factor_of_var, constant).

        Only linear combinations are allowed; non-linear forms raise Solver/Syntax errors.
        """
        (left_factor, left_constant) = self.left.collect_term(var_name)
        (right_factor, right_constant) = self.right.collect_term(var_name)

        if self.operator == '+':
            result_factor = left_factor + right_factor
            result_constant = left_constant + right_constant
            return (result_factor, result_constant)

        elif self.operator == '-':
            result_factor = left_factor - right_factor
            result_constant = left_constant - right_constant
            return (result_factor, result_constant)

        elif self.operator == '*':
            # Only constant * (A*x + B) is allowed. (A*x + B)*(C*x + D) would be non-linear.
            if left_factor != 0 and right_factor != 0:
                raise E.SyntaxError("x^x Error.", code="3005")

            elif left_factor == 0:
                # B * (C*x + D) = (B*C)*x + (B*D)
                result_factor = left_constant * right_factor
                result_constant = left_constant * right_constant
                return (result_factor, result_constant)

            elif right_factor == 0:
                # (A*x + B) * D = (A*D)*x + (B*D)
                result_factor = right_constant * left_factor
                result_constant = right_constant * left_constant
                return (result_factor, result_constant)

            elif left_factor == 0 and right_factor == 0:
                # Pure constant multiplication
                result_factor = 0
                result_constant = right_constant * left_constant
                return (result_factor, result_constant)

        elif self.operator == '/':
            # (A*x + B) / D is allowed; division by (C*x + D) is non-linear
            if right_factor != 0:
                raise E.SolverError("Non-linear equation. (Division by x)", code="3006")
            elif right_constant == 0:
                raise E.SolverError("Solver: Division by zero", code="3003")
            else:
                # (A*x + B) / D = (A/D)*x + (B/D)
                result_factor = left_factor / right_constant
                result_constant = left_constant / right_constant
                return (result_factor, result_constant)

        elif self.operator == '^':
            # Powers generate non-linear terms (e.g., x^2)
            raise E.SolverError("Powers are not supported by the linear solver.", code="3007")

        elif self.operator == '=':
            # '=' only belongs at the root for solving; not inside collection
            raise E.SolverError("Should not happen: '=' inside collect_terms", code="3720")

        else:
            raise E.CalculationError(f"Unknown operator: {self.operator}", code="3004")

    def __repr__(self):
        return f"BinOp({self.operator!r}, left={self.left}, right={self.right})"


# -----------------------------
# Tokenizer
# -----------------------------

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
    "Pi" : "π"
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

    temp_problem = problem
    for var_name in sorted_vars:
        value_str = CONTEXT_VARS[var_name]
        temp_problem = temp_problem.replace(var_name, value_str)

    problem = temp_problem


    while b < len(problem):
        found_function = False
        current_char = problem[b]


        for start_str, (token, length) in FUNCTION_STARTS_OPTIMIZED.items():
            if problem.startswith(start_str, b):
                full_problem.append(token)
                if token != "π" and token != "E" and token != "e":
                    full_problem.append("(")
                b += length - 0
                found_function = True
                break
        if found_function:
            continue


        # --- Numbers: digits and decimal separator (EXPONENTIAL NOTATION SUPPORT ADDED) ---
        if isInt(current_char) or (b >= 0 and current_char == "."):
            str_number = current_char
            has_decimal_point = False  # Only one dot allowed in a numeric literal
            has_exponent_e = False  # Only one 'e' or 'E' allowed
            if b <= len(problem)+1:
                if problem[b+1] == "x":
                    allowed_char = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F", "a", "b", "c", "d","e", "f"}
                    forbidden_char = {".", ","}
                    hex_number = "0x"
                    if int(current_char) == 0 and problem[b+1] == "x" and settings["allow_hex"] == True:
                        a =b+2
                        while (a < len(problem)):
                            if problem[a] in forbidden_char:
                                raise E.ConversionError("Unexpected token in hex:" + str(problem[a]), code="8004")
                            elif problem[a] in allowed_char:
                                hex_number += problem[a]
                            else:
                                break
                            a += 1

                        str_number = hex_to_int(str(hex_number))
                        current_char = str_number
                        b=a-1
                        #full_problem.append(Decimal(str_number))




                    else:
                    # Continue reading the number part
                        while (b + 1 < len(problem)):
                            next_char = problem[b + 1]


                            # 1. Handle decimal points
                            if next_char == ".":
                                if has_decimal_point:
                                    raise E.SyntaxError("Double decimal point.", code="3008")
                                has_decimal_point = True

                            # 2. Handle the 'E' or 'e' for exponent
                            elif next_char in ('e', 'E'):
                                if has_exponent_e:
                                    # Cannot have two 'e's in a single number
                                    raise E.SyntaxError("Double exponent sign 'E'/'e'.", code="3031")
                                has_exponent_e = True

                            # 3. Handle the sign (+ or -) immediately following 'E'/'e'
                            elif next_char in ('+', '-'):
                                # The sign is only valid if it immediately follows 'e' or 'E'
                                if not (problem[b] in ('e', 'E') and has_exponent_e):
                                    # If it's not following 'e'/'E', it's a separate unary operator.
                                    # Break the loop to treat it as an operator in the next iteration.
                                    break

                            # 4. End the loop if the next character is not a number component
                            elif not isInt(next_char):
                                break

                            # If we made it here, the character is a valid part of the number (digit, dot, E/e, or sign after E/e)
                            b += 1
                            str_number += problem[b]

            # Validate the final collected string
            if isfloat(str_number) or isInt(str_number):
                full_problem.append(Decimal(str_number))
            else:
                # This handles cases like '5E' without an exponent after it
                if has_exponent_e and not str_number[-1].isdigit():
                    raise E.SyntaxError("Missing exponent value after 'E'/'e'.", code="3032")
                # If it's not a valid number, let the fallback handle it as a variable
                # or raise an error in the original logic. We rely on the 'else' below.


        # --- Operators ---
        elif isOp(current_char) != -1:
            full_problem.append(current_char)

        # --- Whitespace (ignored) ---
        elif current_char == " ":
            pass

        # --- Parentheses ---
        elif current_char == "(":
            full_problem.append("(")
        elif current_char == "≈":  # treat as equality
            full_problem.append("=")
        elif current_char == ")":
            full_problem.append(")")
        elif current_char == ",":
            full_problem.append(",")

        # --- Scientific functions and special forms: sin(, cos(, tan(, log(, √(, e^( ---





        # --- Constant π ---
        elif current_char == 'π':
            result_string = ScientificEngine.isPi(str(current_char))
            try:
                calculated_value = Decimal(result_string)
                full_problem.append(calculated_value)
            except ValueError:
                raise E.CalculationError(f"Error with constant π:{result_string}", code="3219")

        # --- Variables (fallback) ---
        else:
            # Map each new variable symbol to var{n} to keep internal representation uniform
            if current_char in var_list:
                full_problem.append("var" + str(var_list.index(current_char)))
            else:
                full_problem.append("var" + str(var_counter))
                var_list[var_counter] = current_char
                var_counter += 1

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
                full_problem.insert(b + 1, '*')

        b += 1

    return full_problem, var_counter


# -----------------------------
# Parser (recursive descent)
# -----------------------------

def ast(received_string, settings, custom_variables):
    """Parse a token stream into an AST.
    Implements precedence via nested functions: factor → unary → power → term → sum → equation.

    NEW: `settings` is used to control UI-driven parsing behavior (e.g. allowing
    augmented assignment patterns like `12+=6`):
      - settings["allow_augmented_assignment"] → influences pre-parse validation/rewrites.
    """
    analysed, var_counter = translator(received_string, custom_variables, settings)

    # Normalize spurious leading/trailing '=' if there's no variable; keep equations intact
    if analysed and analysed[0] == "=" and not "var0" in analysed:
        analysed.pop(0)

    if analysed and analysed[-1] == "=" and not "var0" in analysed:
        analysed.pop()

    # NEW: Guard against starting with '*' or '/' which implies a missing left operand.
    if analysed and (analysed[0] == "*" or analysed[0] == "/"):
        raise E.CalculationError("Missing Number.", code="3028")

    # NEW: Additional pre-parse validations / rewrites to support augmented assignment.
    if analysed:
        b = 0

        while b < len(analysed) - 1:

            # Case 1: operator directly followed by '=' (e.g., "+=") without AA allowed → error
            if (len(analysed) != b + 1) and (analysed[b + 1] == "=" and (analysed[b] in Operations)) and (
                    settings["allow_augmented_assignment"] == False):
                raise E.CalculationError("Missing Number before '='.", code="3028")

            # Case 1a (NEW): If AA is allowed and there is NO variable in the expression,
            # rewrite "A += B" into "A = (A + B)":
            #   - insert '(' after '='
            #   - append ')' at the end
            #   - remove the original '=' right after operator (so it becomes an infix '=')
            elif ((len(analysed) != b + 1 or len(analysed) != b + 2) and (
                    analysed[b + 1] == "=" and (analysed[b] in Operations)) and (
                          settings["allow_augmented_assignment"] == True) and not "var0" in analysed):
                analysed.append(")")
                analysed.insert(b + 2, "(")
                analysed.pop(b + 1)

            # Case 1b (NEW): If AA is attempted while variables exist, forbid it
            # to avoid ambiguous solver semantics.
            elif ((len(analysed) != b + 1 or len(analysed) != b + 2) and (
                    analysed[b + 1] == "=" and (analysed[b] in Operations)) and (
                          settings["allow_augmented_assignment"] == True) and "var0" in analysed):
                raise E.CalculationError("Augmented assignment not allowed with variables.", code="3030")

            # Case 2: '=' precedes an operator (e.g., "=+") → number missing after '='
            elif (b > 0) and (analysed[b + 1] == "=" and (analysed[b] in Operations)):
                raise E.CalculationError("Missing Number after '='.", code="3028")

            # NEW: Expression ends with an operator → explicit "missing number" after that operator.
            elif analysed[-1] in Operations:
                raise E.CalculationError(f"Missing Number after {analysed[-1]}", code="3029")

            # NEW: operator followed by '=' (AA disabled) and no variables → still "missing number after <op>"
            elif (analysed[b] in Operations and (analysed[b + 1] == "=" and (
                    settings["allow_augmented_assignment"] == False))) and not "var0" in analysed:
                raise E.CalculationError(f"Missing Number after {analysed[b]}", code="3029")

            b += 1

    # '=' at start/end while a variable exists → malformed equation
    if ((analysed and analysed[-1] == "=") or (analysed and analysed[0] == "=")) and "var0" in analysed:
        raise E.CalculationError(f"{received_string}", code="3025")

    if debug == True:
        print(analysed)

    # ---- Parsing functions in precedence order ----

    def parse_factor(tokens):
        """Numbers, variables, sub-expressions in '()', and scientific functions."""
        if len(tokens) > 0:
            token = tokens.pop(0)
        else:
            # NEW: explicit "missing number" when a factor is required but tokens are exhausted.
            raise E.CalculationError(f"Missing Number.", code="3027")

        # Parenthesized sub-expression
        if token == "(":
            subtree_in_paren = parse_sum(tokens)
            if not tokens or tokens.pop(0) != ')':
                raise E.SyntaxError("Missing closing parenthesis ')'", code="3009")
            return subtree_in_paren

        # Scientific functions / constants
        elif token in Science_Operations:

            if token == 'π':
                result = ScientificEngine.isPi(token)
                try:
                    calculated_value = Decimal(result)
                    return Number(calculated_value)
                except ValueError:
                    raise E.SyntaxError(f"Error with constant π: {result}", code="3219")

            else:
                # function must be followed by '('
                if not tokens or tokens.pop(0) != '(':
                    raise E.SyntaxError(f"Missing opening parenthesis after function {token}", code="3010")

                argument_subtree = parse_sum(tokens)

                # Special case: log(number, base)
                if token == 'log' and tokens and tokens[0] == ',':
                    tokens.pop(0)
                    base_subtree = parse_sum(tokens)
                    if not tokens or tokens.pop(0) != ')':
                        raise E.SyntaxError(f"Missing closing parenthesis after logarithm base.", code="3009")
                    argument_value = argument_subtree.evaluate()
                    base_value = base_subtree.evaluate()
                    ScienceOp = f"{token}({argument_value},{base_value})"
                else:
                    if not tokens or tokens.pop(0) != ')':
                        raise E.SyntaxError(f"Missing closing parenthesis after function '{token}'", code="3009")
                    argument_value = argument_subtree.evaluate()
                    ScienceOp = f"{token}({argument_value})"

                # Delegate to scientific engine; keep result as-is for Number()
                result_string = ScientificEngine.unknown_function(ScienceOp)
                if isinstance(result_string, str) and result_string.startswith("ERROR:"):
                    # Wenn ScientificEngine einen Fehler meldet, werfe ihn als SyntaxError
                    raise E.SyntaxError(result_string, code="3218")
                try:
                    calculated_value = result_string
                    return Number(calculated_value)
                except ValueError:
                    raise E.SyntaxError(f"Error in scientific function: {result_string}", code="3218")

        # Literals / variables
        elif isinstance(token, Decimal):
            return Number(token)
        elif isInt(token):
            return Number(token)
        elif isfloat(token):
            return Number(token)
        elif "var" in str(token):
            return Variable(token)
        else:
            raise E.SyntaxError(f"Unexpected token: {token}", code="3012")

    def parse_unary(tokens):
        """Handle leading '+'/'-' (unary minus becomes 0 - operand)."""
        if tokens and tokens[0] in ('+', '-'):
            operator = tokens.pop(0)
            operand = parse_unary(tokens)

            if operator == '-':
                # Optimize for literal: -Number → Number(-value)
                if isinstance(operand, Number):
                    return Number(-operand.evaluate())
                return BinOp(Number('0'), '-', operand)
            else:
                return operand
        return parse_power(tokens)

    def parse_power(tokens):
        """Exponentiation '^' (handled before * and +)."""
        current_subtree = parse_factor(tokens)
        while tokens and tokens[0] in ("^"):
            operator = tokens.pop(0)
            right_part = parse_unary(tokens)
            if not isinstance(current_subtree, Variable) and not isinstance(right_part, Variable):
                # Pre-evaluate when both sides are numeric
                base = current_subtree.evaluate()
                exponent = right_part.evaluate()
                result = base ** exponent
                current_subtree = Number(result)
            else:
                # Keep as symbolic BinOp otherwise
                current_subtree = BinOp(current_subtree, operator, right_part)
        return current_subtree

    def parse_term(tokens):
        """Multiplication and division."""
        current_subtree = parse_unary(tokens)
        while tokens and tokens[0] in ("*", "/"):
            operator = tokens.pop(0)
            right_part = parse_unary(tokens)
            current_subtree = BinOp(current_subtree, operator, right_part)
        return current_subtree

    def parse_sum(tokens):
        """Addition and subtraction."""
        current_subtree = parse_term(tokens)
        while tokens and tokens[0] in ("+", "-"):
            operator = tokens.pop(0)
            if debug == True:
                print("Currently at:" + str(operator) + "in parse_sum")
            right_side = parse_term(tokens)
            current_subtree = BinOp(current_subtree, operator, right_side)
        return current_subtree

    def parse_gleichung(tokens):
        """Optional '=' at the top level: build BinOp('=') when present."""
        left_side = parse_sum(tokens)
        if tokens and tokens[0] == "=":
            operator = tokens.pop(0)
            right_side = parse_sum(tokens)
            return BinOp(left_side, operator, right_side)
        return left_side

    # Build the final AST
    final_tree = parse_gleichung(analysed)

    # Decide if this is a CAS-style equation with <= 1 variable
    if isinstance(final_tree, BinOp) and final_tree.operator == '=' and var_counter <= 1:
        cas = True

    if debug == True:
        print("Final AST:")
        print(final_tree)

    # `cas` may or may not be set above; default to False
    cas = locals().get('cas', False)

    return final_tree, cas, var_counter


# -----------------------------
# Linear solver (one variable)
# -----------------------------

def solve(tree, var_name):
    """Solve (A*x + B) = (C*x + D) for x, or detect no/inf. solutions."""
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
    """Format a numeric result as Fraction or Decimal depending on settings.

    Returns:
        (rendered_value, rounding_flag)
    where rounding_flag indicates whether Decimal rounding occurred.
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

def hex_to_int(hex):
    if not isinstance(hex, str):
        raise E.ConversionError("Converter didnt receive string: " + str(type(hex)), code="8002")
    else:
        try:
            hex = int(hex, 0)
            return hex

        except ValueError as e:
            raise E.ConversionError(f"Couldnt convert hex to int: {e}", code="8000")

        except Exception as e:
            raise E.ConversionError(f"Unexpected conversion error: {e}", code="8001")



def convert_to_hex(number):
    if isinstance(number, (Decimal, float, int)) and number % 1 != 0:
        raise E.ConversionError("Cannot convert non-integer value to hex.", code="8003")
    try:
        if isinstance(number, Decimal):
            number = int(number.to_integral_value())
        else:
            number = int(number)
    except Exception:
        raise E.ConversionError("Input could not be converted to a Python integer.", code="8004")

    if not isinstance(number, int):
        raise E.ConversionError("Converter didnt receive int: " + str(type(number)), code="8002")

    try:
        hex_string = hex(number)
        return hex_string

    except Exception as e:
        # Spezifische Fehler (z.B. bei extrem großen Zahlen)
        raise E.ConversionError(f"Couldnt convert int to hex: {e}", code="8001")


# -----------------------------
# Public entry point
# -----------------------------

def calculate(problem: str, custom_variables: Union[dict, None] = None):
    if custom_variables is None:
        custom_variables = {}

    """Main API: parse → (evaluate | solve | equality-check) → format → render string."""
    # Guard precision locally before each calculation (UI may adjust as well)
    getcontext().prec = 10000
    settings = config_manager.load_setting_value("all")  # pass UI settings down to parser
    global debug
    debug = settings.get("debug", False)
    var_list = []
    allowed_prefix = (
        "dec:", "d:", "Decimal:",
        "int:", "i:", "integer:",
        "float:", "f:",
        "bool:", "b:", "boolean:",
        "hex:", "h:", "hexadecimal:",
        "str:", "s:", "string:"
    )
    output_prefix = ""
    problem_lower = problem.lower()
    try:
        for prefix in allowed_prefix:
            if problem_lower.startswith(prefix):
                if prefix.startswith("s")or prefix.startswith("S"):
                    output_prefix = "string:"
                elif prefix.startswith("b")or prefix.startswith("B"):
                    output_prefix = "boolean:"
                elif prefix.startswith("d") or prefix.startswith("D"):
                    output_prefix = "decimal:"
                elif prefix.startswith("f") or prefix.startswith("F"):
                    output_prefix = "float:"
                elif prefix.startswith("i") or prefix.startswith("I"):
                    output_prefix = "int:"
                elif prefix.startswith("h") or prefix.startswith("H"):
                    output_prefix = "hexadecimal:"
                problem = problem[len(prefix):]
                break


        final_tree, cas, var_counter = ast(problem, settings, custom_variables)  # NEW: settings param enables AA handling
        if debug == True:
            print(final_tree)
        # Decide evaluation mode
        if cas and var_counter > 0:
            # Solve linear equation for first variable symbol in the token stream
            var_name_in_ast = "var0"
            result = solve(final_tree, var_name_in_ast)

        elif not cas and var_counter == 0:
            # Pure numeric evaluation
            result = final_tree.evaluate()

        elif cas and var_counter == 0:
            # Pure equality check (no variable): returns "= True/False"
            left_val = final_tree.left.evaluate()
            right_val = final_tree.right.evaluate()
            output_string = "True" if left_val == right_val else "False"
            result = (left_val == right_val)
            if output_prefix != "boolean:" and output_prefix != "string:" and output_prefix != "":
                raise E.ConversionOutputError("Couldnt convert result into the given prefix", code = "8006")
            if output_prefix == "boolean:":
                try:
                    boolean(output_string)
                    return boolean(output_string)
                except Exception as e:
                    raise E.ConversionError("Couldnt convert type to" + str(output_prefix), code="8003")

        else:
            # Mixed/invalid states with or without '=' and variables
            if cas:
                raise E.SolverError("The solver was used on a non-equation", code="3005")
            elif not cas and not "=" in problem:
                raise E.SolverError("No '=' found, although a variable was specified.", code="3012")
            elif cas and "=" in problem and (
                    problem.index("=") == 0 or problem.index("=") == (len(problem) - 1)):
                raise E.SolverError("One of the sides is empty: " + str(problem), code="3022")
            else:
                raise E.CalculationError("The calculator was called on an equation.", code="3015")

        # Render result based on settings (fractions/decimals, rounding flag)

        result, rounding = cleanup(result)
        approx_sign = "\u2248"  # "≈"

        # --- START OF MODIFIED BLOCK FOR EXPONENTIAL NOTATION CONTROL ---

        # Convert normalized result to string (Decimal supports to_normal_string)
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

        if output_prefix == "" or output_prefix == "decimal:":
            try:
                Decimal(output_string)
                return Decimal(output_string)
            except Exception as e:
                raise E.ConversionOutputError("Couldnt convert type to" + str(output_prefix), code="8003")

        elif output_prefix == "string:":
            try:
                #str(output_string)
                return str(output_string)
            except Exception as e:
                raise E.ConversionOutputError("Couldnt convert type to" + str(output_prefix), code="8003")

        elif output_prefix == "hexadecimal:":
            try:
                convert_to_hex(output_string)
                return convert_to_hex(output_string)
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
                int(output_string)
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


    # Known numeric overflow
    except Overflow as e:
        raise E.CalculationError(
            message="Number too large (Arithmetic overflow).",
            code="3026",
            equation=problem
        )
    # Fallback to next best format
        # calculator.py (Except Block, um Zeile 1037)

    except E.ConversionOutputError as e:
        fallback_versuche = [ "decimal:", "boolean:", "string:"]
        if settings["correct_output_format"] == True:
            for versuch in fallback_versuche:
                try:
                    if versuch == "decimal:":
                        if isDecimal(output_string) != False:
                            return Decimal(output_string)

                    elif versuch == "boolean:":
                        bool_result = boolean(output_string)
                        if bool_result in (True, False):
                            return bool_result

                    elif versuch == "string:":
                        print("x")
                        return str(output_string)

                except Exception as e:
                    continue
        else:
            raise E.ConversionError(
                f"Couldnt convert result '{output_string}' into '{output_prefix}'",
                code="8007"
            )
    # Re-raise our domain errors after attaching the source equation
    except E.MathError as e:
        e.equation = problem
        raise e
    # Convert unexpected Python exceptions to our unified error type
    except (ValueError, SyntaxError, ZeroDivisionError, TypeError, Exception) as e:
        error_message = str(e).strip()
        parts = error_message.split(maxsplit=1)
        code = "9999"
        message = error_message

        # If an error string already begins with a 4-digit code, respect it
        if parts and parts[0].isdigit() and len(parts[0]) == 4:
            code = parts[0]
            if len(parts) > 1:
                message = parts[1]
        raise E.MathError(message=message, code=code, equation=problem)


def test_main():
    """Simple REPL-like runner for manual testing of the engine."""
    print("Enter the problem: ")
    problem = input()
    result = calculate(problem)
    print(result)
    test_main()  # recursive call disabled

if __name__ == "__main__":
    test_main()
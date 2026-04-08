"""
Custom exception hierarchy and error code catalog for math_engine.

Exception Hierarchy
-------------------
::

    Exception
      +-- MathError                  # Base — carries message, code, equation, positions
           +-- SyntaxError           # Parsing / tokenization / structural issues
           +-- CalculationError      # Runtime numeric issues (e.g., division by zero)
           +-- SolverError           # Algebraic solver issues (nonlinear, multiple vars)
           +-- ConversionError       # Type conversion failures during evaluation
           +-- ConversionOutputError # Output format conversion failures
           +-- ConfigError           # Configuration read/write failures
           +-- PluginError           # Plugin loading and validation failures

Error Code Structure
--------------------
Each code is a 4-digit string.  The first digit identifies the error family:

    1xxx  Missing Files
    2xxx  Scientific Calculation
    3xxx  Calculator / Parser / Solver
    4xxx  Memory
    5xxx  Configuration
    6xxx  Communication
    7xxx  Runtime
    8xxx  Conversion
    9xxx  Plugin / Catch-All

Note
----
This module defines its own ``SyntaxError`` class, intentionally shadowing
Python's built-in.  Always import via ``from math_engine.utility import error
as E`` and reference ``E.SyntaxError`` to avoid ambiguity.
"""

class MathError(Exception):
    """Base error for all calculator failures.

    Attributes:
        message (str): human-readable explanation
        code (str): 4-digit error code (see ERROR_MESSAGES)
        equation (str|None): original user input that caused the error
    """
    def __init__(self, message, code="9999", equation=None, position_start: int = -1,position_end: int = -1):
        """Initialise a MathError.

        Args:
            message:        Human-readable explanation of the failure.
            code:           4-digit error code string (default ``"9999"``).
            equation:       The original user input that triggered the error,
                            or ``None`` if unavailable.
            position_start: 0-based character index where the error begins
                            inside *equation* (``-1`` = unknown).
            position_end:   0-based character index where the error ends.
                            Defaults to *position_start* when not provided.
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.equation = equation
        self.position_start = position_start
        if position_end == -1:
            self.position_end = self.position_start
        self.position_end = position_end

class SyntaxError(MathError):
    """Raised for parsing, tokenization, parenthesis-matching, or structural issues.

    This covers malformed expressions, missing brackets, unexpected tokens,
    and any other problem detected before or during tokenization.

    Typical codes: 3008--3042.

    Note:
        This class intentionally shadows the built-in ``SyntaxError``.
        Always reference it via the module alias (``E.SyntaxError``) to
        avoid confusion.
    """
    pass


class CalculationError(MathError):
    """Raised for numeric or runtime calculation issues.

    Examples include division by zero, numeric overflow, numbers too large
    to represent, and missing operands.

    Typical codes: 3003, 3026--3029.
    """
    pass


class SolverError(MathError):
    """Raised when the algebraic equation solver cannot proceed.

    Common causes are non-linear terms (variable in a denominator or
    exponent), multiple unknown variables, or infinite/no solutions.

    Typical codes: 3002, 3005--3007, 3013--3014.
    """
    pass


class ConversionError(MathError):
    """Raised when type conversion fails during input parsing or evaluation.

    Covers failures such as invalid hex digits, inability to convert a
    string to ``int``/``Decimal``, and incompatible operand types for
    bit operations.

    Typical codes: 8000--8008.
    """
    pass


class ConversionOutputError(MathError):
    """Raised when the computed result cannot be formatted into the requested output base.

    For example, a non-integer result cannot be represented as a binary or
    hexadecimal literal.

    Typical codes: 8003, 8006.
    """
    pass


class ConfigError(MathError):
    """Raised for configuration read, write, or validation failures.

    This includes missing config files, invalid setting values, and
    I/O errors when persisting configuration.

    Typical codes: 5000--5004.
    """
    pass


class PluginError(MathError):
    """Raised for plugin discovery, loading, or validation failures.

    Covers issues such as malformed ``register_function`` dicts, missing
    plugin classes, classes that do not inherit ``BasePlugin``, and runtime
    errors during plugin instantiation.

    Typical codes: 9000--9011.
    """
    pass


# ---------------------------------------------------------------------------
# Error-family lookup
# ---------------------------------------------------------------------------
# Maps the first digit of a 4-digit error code to a human-readable family
# name.  Used for quick categorization in logs and telemetry dashboards.
# The actual end-user messages live in ERROR_MESSAGES below.
# ---------------------------------------------------------------------------
Error_Dictionary = {
    "1": "Missing Files",
    "2": "Scientific Calculation Error",
    "3": "Calculator Error",
    "4": "Memory Error",
    "5": "Configuration Error",
    "6": "Communication Error",
    "7": "Runtime Error",
    "8" : "Conversion Error",
    "9" : "Plugin Error"
}

# ---------------------------------------------------------------------------
# Error message catalog
# ---------------------------------------------------------------------------
# Every entry maps a 4-digit string code to a short, user-facing message.
#
# Code structure:
#   1st digit  -> main error family (see Error_Dictionary above)
#   2nd digit  -> sub-area or component within the family
#   3rd & 4th  -> specific error sequence number
#
# For example, code "3008":
#   3 = Calculator family, 0 = core parser, 08 = "more than one '.' in a number"
#
# Conventions:
# - Messages ending with ": " expect the caller to append extra context
#   (e.g., the offending operator or sub-expression).
# - Do not renumber existing codes: they are referenced by the UI and by
#   external log parsers.
# ---------------------------------------------------------------------------
ERROR_MESSAGES = {
    # 2xxx — scientific/processing/config related
    "2000": "Sin/Cos/tan was recognized, but couldnt be assigned in processing.",
    "2001": "Logarithm Syntax.",
    "2002": "Invalid Number or Base in Logarithm.",
    "2003": "Logarithm result error: ",          # + calculated result
    "2004": "Unable to identify given Operation: ",  # + given problem
    "2505": "Loading Configurations for degree setting.",
    "2706": "Process already running",

    # 3xxx — core calculator / parsing / solver
    "3000": "Missing Opening Bracket: ",         # + given problem
    "3001": "Missing Solver.",
    "3002": "Multiple Variables in problem: ",   # + given problem
    "3003": "Division by Zero",
    "3004": "Invalid Operator: ",                # + operator
    "3005": "Non linear problem. ",
    "3006": "Non linear problem (Division by Variable)",
    "3007": "Non linear problem (Potenz)",
    "3008": "More than one '.' in one number.",
    "3009": "Missing ')'. ",
    "3010": "Missing '('. ",
    "3011": "Unexpected Token: ",                # + token
    "3012": "Invalid equation:  ",               # + equation
    "3013": "Infinit Solutions.",
    "3014": "No Solution",
    "3015": "Normal Calculator on Equation.",
    "3216": "Missing ')'",                       # after logarithm base
    "3217": "Missing ')' after function",
    "3218": "Error with Scientific function: ",  # + problem
    "3219": "π",
    "3720": "'=' in collect_terms",
    "3721": "Process already running",
    "3022": "One of the equation sides is empty",# + equation
    "3023": "Missing '()':",                     # + equation
    "3024": "Invalid fraction",
    "3025": "One of the sides is empty.",
    "3026": "Number too big.",
    "3027": "Missing Number after an operator",
    "3028": "Missing Number before an operator",
    "3029": "Missing Operator",
    "3030": "Augmented assignment not allowed with variables.",
    "3031": "Boolean in equation",
    "3032": "Multiple digit variables not supported.",
    "3033": "Function not support with only not decimals.",
    "3034": "Empty string.", # + string
    "3035": "Incomplete number.",
    "3036" : "Two or more equal signs.",
    "3037" : "Two equal signs after another, but another type of output was forced.",
    "3038" : "Variables not supported with only_hex, only_binary or only_octal mode.",
    "3039" : "Multiple Variables",
    "3040" : "Invalid shift operation", # +operation
    "3041" : "Bitshift requires int.",
    "3042" : "XOR requires Integers",

    "4000" : "Couldnt find memory entry.",

    "5000" : "Missmatch of values.", # +Error
    "5001" : "File not Found.",
    "5002" : "Could not save config file.",
    "5003" : "Invalid word size",
    "5004" : "Whole numbers needed.",
    
    "8000": "Error converting int to hex.",
    "8001": "Error converting hex to int.",
    "8002": "Received wrong type: ", # + type
    "8003" : "Error Converting.",
    "8004" : "Input could not be converted to a Python integer.",
    "8005" : "Forbidden value in Hex", # + value
    "8006" : "Result value not compatible with output prefix",
    "8007": "Failed Bit Operation",
    "8008": "Comma in BitNot",

    # 9xxx — Plugin Error
    "9000" : "Registered function is not a dict.",
    "9001" : "Too many keys in function",
    "9002" : "Wrong registered type",
    "9003" : "Invalid value type",
    "9004" : "Invalid Divider.",
    "9005" : "Couldnt find referenced class",
    "9006" : "Class not child from BasePlugin",
    "9007" : "Error loading plugin",
    "9008" : "Instancing Error",
    "9009" : "register_function not found",
    "9010" : "register_function raised an error",
    "9011" : "Function cant end with ')'",

    # 9999 catch all
    "9999": "Unexpected Error: ",                # + error
}

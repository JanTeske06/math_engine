# error.py
"""""
Custom error types and error message catalog for the Advanced Python Calculator.

- MathError is the common base class that carries:
  - message: human-readable description
  - code: 4-digit string (see ERROR_MESSAGES)
  - equation: the input expression/equation that triggered the error

- Specialized subclasses let the rest of the code catch specific categories
  (SyntaxError, CalculationError, SolverError) while keeping a unified shape.

- ERROR_MESSAGES maps error codes to short, user-facing messages.
  The UI composes the final dialog text using these templates.
"""""

# Note: This module defines its own SyntaxError class on purpose.
# It shadows Python's built-in SyntaxError *within this module/import path*,
# but keeps a consistent error API with (message, code, equation).

class MathError(Exception):
    """Base error for all calculator failures.

    Attributes:
        message (str): human-readable explanation
        code (str): 4-digit error code (see ERROR_MESSAGES)
        equation (str|None): original user input that caused the error
    """
    def __init__(self, message, code="9999", equation=None, position_start: int = -1,position_end: int = -1):
        super().__init__(message)
        self.message = message
        self.code = code
        self.equation = equation
        self.position_start = position_start
        if position_end == -1:
            self.position_end = self.position_start
        self.position_end = position_end

class SyntaxError(MathError):
    """Parsing/tokenization/parentheses or general syntax issues."""
    pass


class CalculationError(MathError):
    """Numeric/runtime calculation issues (g., division by zero)."""
    pass


class SolverError(MathError):
    """Algebraic solver issues (g., non-linear, multiple variables)."""
    pass

class ConversionError(MathError):
    pass

class ConversionOutputError(MathError):
    pass

class ConfigError(MathError):
    pass


# ---------------------------------------------------------------------------
# Error families (first digit) for quick categorization in logs/telemetry.
# This dictionary is informational; actual user strings come from
# ERROR_MESSAGES below.
# ---------------------------------------------------------------------------
Error_Dictionary = {
    "1": "Missing Files",
    "2": "Scientific Calculation Error",
    "3": "Calculator Error",
    "4": "Memory Error",
    "5": "Configuration Error",
    "6": "Communication Error",
    "7": "Runtime Error",
    "8" : "Conversion Error"
}

# Error code structure:
#   1st digit  -> main error family (see Error_Dictionary)
#   2nd digit  -> sub-area / component
#   3rd & 4th  -> specific error number
#
# Notes:
# - Some messages expect concatenation with extra context by the caller
#   (g., operator/problem string). Keep the base text short and neutral.
# - Do not change codes lightly; they are used across UI/dialogs and logs.
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

    # 9xxx — catch-all
    "9999": "Unexpected Error: ",                # + error
}

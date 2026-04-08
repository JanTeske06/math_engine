"""
Abstract Syntax Tree (AST) node types for the math_engine expression parser.

The parser (:func:`calculator.calculator.ast`) builds a tree from three node
types:

- :class:`Number`   — numeric literals (backed by ``decimal.Decimal``)
- :class:`Variable` — symbolic variable placeholders (e.g., ``"var0"``)
- :class:`BinOp`    — binary operations with a left subtree, operator, and
  right subtree

Each node implements:

- ``evaluate()``          — recursively compute the numeric value
- ``collect_term(var)``   — decompose the subtree into
  ``(factor_of_var, constant)`` for the linear equation solver
"""

from decimal import Decimal
from ..utility import error as E

class Number:
    """AST node representing a numeric literal, backed by ``decimal.Decimal``.

    A ``Number`` is always a leaf node in the AST.  It stores a single
    ``Decimal`` value and carries optional source-position information so
    that error messages can point back to the original input string.

    Attributes:
        value (Decimal): The numeric value of the literal.
        position_start (int): Character index where this literal begins
            in the source string (``-1`` when unknown).
        position_end (int): Character index where this literal ends
            in the source string (``-1`` when unknown).
    """

    def __init__(self, value, position_start=-1, position_end=-1):
        """Create a Number node.

        Args:
            value: Any numeric type.  Non-Decimal values are first
                converted to ``str`` before being passed to the ``Decimal``
                constructor so that floating-point artifacts (e.g.
                ``Decimal(0.1)`` producing ``0.1000000000000000055...``)
                are avoided.
            position_start: Start index in the source string.
            position_end: End index in the source string.
        """
        # Always normalize input to Decimal via string to avoid float artifacts
        if not isinstance(value, Decimal):
            value = str(value)
        self.value = Decimal(value)
        self.position_start = position_start
        self.position_end = position_end

    def evaluate(self):
        """Return the stored ``Decimal`` value.

        Because a ``Number`` is a leaf, no recursion is required.

        Returns:
            Decimal: The numeric value of this literal.
        """
        return self.value

    def collect_term(self, var_name):
        """Decompose this node for the linear equation solver.

        A numeric literal contains no variable term, so the factor is
        always ``0`` and the constant is the literal's value.

        Args:
            var_name (str): The variable name being collected (unused
                for ``Number`` nodes, but required by the interface).

        Returns:
            tuple[int, Decimal]: ``(0, self.value)`` -- zero coefficient
            for the variable and the literal as the constant part.
        """
        # A plain number contributes nothing to the variable factor
        # and its full value to the constant term.
        return (0, self.value)

    def __repr__(self):
        """Return a human-readable representation, e.g. ``Number(3.14)``."""
        try:
            display_value = self.value.to_normal_string()
        except AttributeError:
            display_value = str(self.value)
        return f"Number({display_value})"


class Variable:
    """AST node representing a single symbolic variable (e.g. ``"var0"``).

    A ``Variable`` is a leaf node that acts as a placeholder for an
    unknown value.  The tokenizer assigns internal names like ``"var0"``,
    ``"var1"``, etc. -- these are the names stored in :attr:`name`.

    Attributes:
        name (str): Internal variable identifier assigned by the tokenizer
            (e.g. ``"var0"``).
        position_start (int): Character index where this variable begins
            in the source string (``-1`` when unknown).
        position_end (int): Character index where this variable ends
            in the source string (``-1`` when unknown).
    """

    def __init__(self, name, position_start=-1, position_end=-1):
        """Create a Variable node.

        Args:
            name: Internal variable identifier (e.g. ``"var0"``).
            position_start: Start index in the source string.
            position_end: End index in the source string.
        """
        self.name = name
        self.position_start = position_start
        self.position_end = position_end

    def evaluate(self):
        """Attempt to numerically evaluate this variable.

        Variables have no numeric value on their own -- they must be
        solved for via the equation solver.  Calling ``evaluate()`` on a
        ``Variable`` therefore always raises ``SolverError``.

        Raises:
            E.SolverError: Always raised (code ``3005``), indicating
                that a numeric evaluation path encountered an unresolved
                variable.
        """
        raise E.SolverError(f"Non linear problem.", code="3005", position_start=self.position_start)

    def collect_term(self, var_name):
        """Decompose this variable for the linear equation solver.

        If this variable matches the one being solved for, it
        contributes a coefficient of ``1`` and a constant of ``0``.
        If it does *not* match, the expression contains multiple
        distinct unknowns, which the linear solver cannot handle.

        Args:
            var_name (str): The internal variable name being collected
                (e.g. ``"var0"``).

        Returns:
            tuple[int, int]: ``(1, 0)`` when ``self.name == var_name``.

        Raises:
            E.SolverError: When ``self.name != var_name`` (code ``3002``),
                meaning the expression has more than one distinct variable.
        """
        if self.name == var_name:
            # This is the variable we are solving for: coefficient = 1, constant = 0
            return (1, 0)
        else:
            # A second, different variable was encountered -- not solvable linearly
            raise E.SolverError(f"Multiple variables found: {self.name}", code="3002", position_start=self.position_start)

    def __repr__(self):
        """Return a human-readable representation, e.g. ``Variable('var0')``."""
        return f"Variable('{self.name}')"


class BinOp:
    """AST node for a binary operation: ``left <operator> right``.

    Attributes:
        left:           Left subtree (Number, Variable, or BinOp).
        operator:       Operator string (``"+"``, ``"-"``, ``"*"``, ``"/"``,
                        ``"**"``, ``"="``, ``"&"``, ``"|"``, ``"^"``,
                        ``"<<"``, ``">>"``)
        right:          Right subtree.
        position_start: Character index of the operator in the source string.
        position_end:   End index of the operator in the source string.
    """

    def __init__(self, left, operator, right, position_start=-1, position_end=-1):
        """Create a BinOp node.

        Args:
            left: Left-hand subtree (``Number``, ``Variable``, or ``BinOp``).
            operator (str): The operator string (e.g. ``"+"``, ``"*"``).
            right: Right-hand subtree (``Number``, ``Variable``, or ``BinOp``).
            position_start (int): Start index of the operator in the source.
            position_end (int): End index of the operator in the source.
        """
        self.left = left
        self.operator = operator
        self.right = right
        self.position_start = position_start
        self.position_end = position_end

    def evaluate(self):
        """Recursively evaluate both subtrees and apply the binary operator.

        Arithmetic operators (``+``, ``-``, ``*``, ``/``, ``**``) work on
        ``Decimal`` values.  Bitwise operators (``&``, ``|``, ``^``, ``<<``,
        ``>>``) require integer operands and return ``Decimal`` results.
        The equality operator (``=``) returns a Python ``bool``.

        Returns:
            Decimal or bool: The computed result.

        Raises:
            E.CalculationError: Division by zero (code ``3003``), non-integer
                operands for bitwise ops (code ``3042``), or unknown operator
                (code ``3004``).
        """
        # Recursively evaluate both child subtrees first (post-order traversal)
        left_value = self.left.evaluate()
        right_value = self.right.evaluate()

        def check_int(val_l, val_r):
            """Guard: bitwise operators require both operands to be integers."""
            if val_l % 1 != 0 or val_r % 1 != 0:
                raise E.CalculationError(f"Operator '{self.operator}' requires integers.", code="3042", position_start=self.position_start)

        # --- Arithmetic operators (Decimal -> Decimal) ---
        if self.operator == '+':
            return left_value + right_value

        elif self.operator == '-':
            return left_value - right_value

        # --- Bitwise operators (int -> Decimal) ---
        elif self.operator == '&':
            check_int(left_value, right_value)
            return Decimal(int(left_value) & int(right_value))

        elif self.operator == '|':
            check_int(left_value, right_value)
            return Decimal(int(left_value) | int(right_value))

        elif self.operator == '^':
            check_int(left_value, right_value)
            return Decimal(int(left_value) ^ int(right_value))

        elif self.operator == '<<':
            check_int(left_value, right_value)
            return Decimal(int(left_value) << int(right_value))

        elif self.operator == '>>':
            check_int(left_value, right_value)
            return Decimal(int(left_value) >> int(right_value))

        # --- Multiplicative / power operators ---
        elif self.operator == '*':
            return left_value * right_value

        elif self.operator == '**':
            return left_value ** right_value

        elif self.operator == '/':
            if right_value == 0:
                raise E.CalculationError("Division by zero", code="3003", position_start=self.position_start)
            return left_value / right_value

        # --- Equality (returns bool, not Decimal) ---
        elif self.operator == '=':
            return left_value == right_value
        else:
            raise E.CalculationError(f"Unknown operator: {self.operator}", code="3004", position_start=self.position_start)

    def collect_term(self, var_name):
        """Collect linear terms on this subtree into ``(factor_of_var, constant)``.

        Used by the linear equation solver.  The subtree is decomposed into
        the form ``factor * var_name + constant``.

        Supported operators:
            - ``+``, ``-``: factors and constants are added/subtracted
            - ``*``: only ``constant * linear`` is allowed (not ``linear * linear``)
            - ``/``: divisor must be constant (no division by variable)
            - ``**``: always raises (non-linear)
            - ``=``: should never appear inside a subtree

        Args:
            var_name: The internal variable name to collect (e.g., ``"var0"``).

        Returns:
            tuple: ``(factor, constant)`` where ``factor`` is the coefficient
                   of *var_name* and ``constant`` is the numeric remainder.

        Raises:
            E.SyntaxError:  Non-linear multiplication (code ``3005``).
            E.SolverError:  Division by variable (``3006``), division by
                            zero (``3003``), power (``3007``), or ``=``
                            inside subtree (``3720``).
        """
        # ---- Linear decomposition core ----
        # Each subtree is expressed as:  factor * var_name + constant
        # where "factor" is the coefficient of the unknown variable and
        # "constant" is the purely numeric part.
        #
        # Example:  the subtree (2*x + 3) yields (factor=2, constant=3).
        (left_factor, left_constant) = self.left.collect_term(var_name)
        (right_factor, right_constant) = self.right.collect_term(var_name)

        # --- Addition: (a*x + b) + (c*x + d) = (a+c)*x + (b+d) ---
        if self.operator == '+':
            return (left_factor + right_factor, left_constant + right_constant)

        # --- Subtraction: (a*x + b) - (c*x + d) = (a-c)*x + (b-d) ---
        elif self.operator == '-':
            return (left_factor - right_factor, left_constant - right_constant)

        # --- Multiplication ---
        # (a*x + b) * (c*x + d) is linear ONLY when at most one side
        # contains the variable.  If both sides have a non-zero factor
        # the product introduces an x^2 term, which is non-linear.
        elif self.operator == '*':
            if left_factor != 0 and right_factor != 0:
                # Both sides depend on x  =>  x * x = x^2  =>  non-linear
                raise E.SyntaxError("x^x Error (Non-linear).", code="3005", position_start=self.position_start)

            elif left_factor == 0:
                # Left side is a pure constant k.
                # k * (c*x + d) = (k*c)*x + (k*d)
                return (left_constant * right_factor, left_constant * right_constant)

            elif right_factor == 0:
                # Right side is a pure constant k.
                # (a*x + b) * k = (k*a)*x + (k*b)
                return (right_constant * left_factor, right_constant * left_constant)

            elif left_factor == 0 and right_factor == 0:
                # Both sides are pure constants (no variable at all).
                # 0*x + b * 0*x + d = 0*x + b*d
                return (0, right_constant * left_constant)

        # --- Division ---
        # (a*x + b) / (c*x + d) is linear only when the divisor is a
        # pure constant (c == 0).  Division BY the variable would make
        # the expression non-linear (1/x term).
        elif self.operator == '/':
            if right_factor != 0:
                # Divisor contains the variable => non-linear (e.g. 1/x)
                raise E.SolverError("Non-linear equation (Division by variable).", code="3006", position_start=self.position_start)
            elif right_constant == 0:
                # Division by zero in the constant divisor
                raise E.SolverError("Solver: Division by zero", code="3003", position_start=self.position_start)
            else:
                # Divisor is a non-zero constant k.
                # (a*x + b) / k = (a/k)*x + (b/k)
                return (left_factor / right_constant, left_constant / right_constant)

        # --- Exponentiation: always non-linear for the solver ---
        elif self.operator == '**':
            raise E.SolverError("Powers are not supported by the linear solver.", code="3007", position_start=self.position_start)

        # --- Equality inside a subtree should never occur ---
        # The '=' is handled at the top level by the solver, not
        # inside a recursive collect_term call.
        elif self.operator == '=':
            raise E.SolverError("Should not happen: '=' inside collect_terms", code="3720", position_start=self.position_start)

        else:
            raise E.CalculationError(f"Unknown operator: {self.operator}", code="3004", position_start=self.position_start)

    def __repr__(self):
        """Return a human-readable representation of the BinOp tree."""
        return f"BinOp({self.operator!r}, left={self.left}, right={self.right})"
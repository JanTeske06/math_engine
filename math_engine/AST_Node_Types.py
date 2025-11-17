from decimal import Decimal, getcontext, Overflow
from . import error as E

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

        elif self.operator == '&':
            if left_value % 1 != 0 or right_value % 1 != 0:
                raise E.CalculationError("Bitwise AND requires integers.", code="3042")
            return Decimal(int(left_value) & int(right_value))

        elif self.operator == '|':
            if left_value % 1 != 0 or right_value % 1 != 0:
                raise E.CalculationError("Bitwise OR requires integers.", code="3042")
            return Decimal(int(left_value) | int(right_value))

        elif self.operator == '^':
            if left_value % 1 != 0 or right_value % 1 != 0:
                raise E.CalculationError("XOR requires integers.", code="3042")
            return Decimal(int(left_value) ^ int(right_value))

        elif self.operator == '<<':
            if left_value % 1 != 0 or right_value % 1 != 0:
                raise E.CalculationError("Bitshift requires integers.", code="3041")
            return Decimal(int(left_value) << int(right_value))

        elif self.operator == '>>':
            if left_value % 1 != 0 or right_value % 1 != 0:
                raise E.CalculationError("Bitshift requires integers.", code="3041")
            return Decimal(int(left_value) >> int(right_value))

        elif self.operator == '*':
            return left_value * right_value

        elif self.operator == '**':
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

        elif self.operator == '**':
            # Powers generate non-linear terms (e.g., x^2)
            raise E.SolverError("Powers are not supported by the linear solver.", code="3007")

        elif self.operator == '=':
            # '=' only belongs at the root for solving; not inside collection
            raise E.SolverError("Should not happen: '=' inside collect_terms", code="3720")

        else:
            raise E.CalculationError(f"Unknown operator: {self.operator}", code="3004")

    def __repr__(self):
        return f"BinOp({self.operator!r}, left={self.left}, right={self.right})"

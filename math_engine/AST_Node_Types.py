from decimal import Decimal, getcontext, Overflow
from . import error as E

# -----------------------------
# AST node types
# -----------------------------

class Number:
    """AST node for numeric literal backed by Decimal."""

    def __init__(self, value, position_start=-1, position_end=-1):
        # Always normalize input to Decimal via string to avoid float artifacts
        if not isinstance(value, Decimal):
            value = str(value)
        self.value = Decimal(value)
        self.position_start = position_start
        self.position_end = position_end

    def evaluate(self):
        """Return Decimal value for this literal."""
        return self.value

    def collect_term(self, var_name):
        """Return (factor_of_var, constant) for linear collection."""
        return (0, self.value)

    def __repr__(self):
        try:
            display_value = self.value.to_normal_string()
        except AttributeError:
            display_value = str(self.value)
        return f"Number({display_value})"


class Variable:
    """AST node representing a single symbolic variable (e.g. 'var0')."""

    def __init__(self, name, position_start=-1, position_end=-1):
        self.name = name
        self.position_start = position_start
        self.position_end = position_end

    def evaluate(self):
        """Variables cannot be directly evaluated without solving."""
        raise E.SolverError(f"Non linear problem.", code="3005", position_start=self.position_start)

    def collect_term(self, var_name):
        """Return (1, 0) if this variable matches var_name; else error."""
        if self.name == var_name:
            return (1, 0)
        else:
            raise E.SolverError(f"Multiple variables found: {self.name}", code="3002", position_start=self.position_start)

    def __repr__(self):
        return f"Variable('{self.name}')"


class BinOp:
    """AST node for a binary operation: left <operator> right."""

    def __init__(self, left, operator, right, position_start=-1, position_end=-1):
        self.left = left
        self.operator = operator
        self.right = right
        self.position_start = position_start
        self.position_end = position_end

    def evaluate(self):
        """Evaluate numeric subtree and apply the binary operator."""
        left_value = self.left.evaluate()
        right_value = self.right.evaluate()
        def check_int(val_l, val_r):
            if val_l % 1 != 0 or val_r % 1 != 0:
                raise E.CalculationError(f"Operator '{self.operator}' requires integers.", code="3042", position_start=self.position_start)

        if self.operator == '+':
            return left_value + right_value

        elif self.operator == '-':
            return left_value - right_value

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

        elif self.operator == '*':
            return left_value * right_value

        elif self.operator == '**':
            return left_value ** right_value

        elif self.operator == '/':
            if right_value == 0:
                raise E.CalculationError("Division by zero", code="3003", position_start=self.position_start)
            return left_value / right_value

        elif self.operator == '=':
            return left_value == right_value
        else:
            raise E.CalculationError(f"Unknown operator: {self.operator}", code="3004", position_start=self.position_start)

    def collect_term(self, var_name):
        """Collect linear terms on this subtree into (factor_of_var, constant)."""
        (left_factor, left_constant) = self.left.collect_term(var_name)
        (right_factor, right_constant) = self.right.collect_term(var_name)

        if self.operator == '+':
            return (left_factor + right_factor, left_constant + right_constant)

        elif self.operator == '-':
            return (left_factor - right_factor, left_constant - right_constant)

        elif self.operator == '*':
            # Only constant * (A*x + B) is allowed.
            if left_factor != 0 and right_factor != 0:
                raise E.SyntaxError("x^x Error (Non-linear).", code="3005", position_start=self.position_start)

            elif left_factor == 0:
                return (left_constant * right_factor, left_constant * right_constant)

            elif right_factor == 0:
                return (right_constant * left_factor, right_constant * left_constant)

            elif left_factor == 0 and right_factor == 0:
                return (0, right_constant * left_constant)

        elif self.operator == '/':
            if right_factor != 0:
                raise E.SolverError("Non-linear equation (Division by variable).", code="3006", position_start=self.position_start)
            elif right_constant == 0:
                raise E.SolverError("Solver: Division by zero", code="3003", position_start=self.position_start)
            else:
                return (left_factor / right_constant, left_constant / right_constant)

        elif self.operator == '**':
            raise E.SolverError("Powers are not supported by the linear solver.", code="3007", position_start=self.position_start)

        elif self.operator == '=':
            raise E.SolverError("Should not happen: '=' inside collect_terms", code="3720", position_start=self.position_start)

        else:
            raise E.CalculationError(f"Unknown operator: {self.operator}", code="3004", position_start=self.position_start)

    def __repr__(self):
        return f"BinOp({self.operator!r}, left={self.left}, right={self.right})"
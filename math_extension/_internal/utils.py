from typing import Union, Literal
from .core import (
    Traceable, Symbol, Expression, Function, Equation
)

# Boolean Expressions

_BoolLike = Union[bool, Literal[0, 1]]
BoolExpr = Union[Expression[_BoolLike], Equation, Symbol, Traceable]

def solve_bool(expr: BoolExpr) -> bool:
    """Solves a boolean expression or equation and returns the result as a boolean."""
    if isinstance(expr, Equation):
        # For an equation, we check if both sides are equal.
        return expr.difference() <= 1e-9  # Using a small tolerance for floating-point comparisons.
    if isinstance(expr, Symbol):
        # For a symbol, we check if it has a value and if that value is truthy.
        return expr.value != 0
    if isinstance(expr, Traceable):
        # For a traceable object, we calculate its value and interpret it as a boolean.
        value = expr.calculate()
        if isinstance(value, bool):
            return value
        elif isinstance(value, (int, float)):
            return value != 0
        else:
            raise ValueError("Traceable object does not evaluate to a boolean or numeric value.")
    if isinstance(expr, Expression):
        # For an expression, we calculate its value and interpret it as a boolean.
        if isinstance(expr, Function):
            value = expr.calculate(expr.symbol.value)
        else:
            value = expr.calculate()
        if isinstance(value, bool):
            return value
        elif isinstance(value, (int, float)):
            return value != 0
        else:
            raise ValueError("Expression does not evaluate to a boolean or numeric value.")
    raise NotImplementedError("Unsupported type for solve_bool. Expected Expression, Equation, Symbol, or Traceable.")

class BooleanExpression:
    """A wrapper class for boolean expressions that can be solved using the solve_bool function. This is useful for users who want to work with boolean expressions in a more structured way."""

    __slots__ = ("real_expr",)
    
    real_expr: BoolExpr

    def __init__(self, expr: BoolExpr) -> None:
        self.real_expr = expr
    
    def solve(self) -> bool:
        """Solves the boolean expression and returns the result as a boolean."""
        return solve_bool(self.real_expr)

# Other Useful Functions

def constant(value: Union[int, float]) -> Traceable:
    """Creates a traceable object that always evaluates to a constant value."""
    if not isinstance(value, (int, float)):
        raise ValueError("Constant value must be an integer or float.")
    return Traceable.wrap(value)
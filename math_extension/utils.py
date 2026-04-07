"""Some utility functions for the math extension. These are often utils that are too foreign for the core module, but are still useful for users of the extension."""

from ._internal.utils import (
    BoolExpr, solve_bool, BooleanExpression, constant
)

__all__ = (
    "BoolExpr", "solve_bool", "BooleanExpression", "constant"
)
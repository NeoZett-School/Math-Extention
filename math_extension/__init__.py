"""Math Extention allow symbols as variables and expressions, functions to use in different type of regression."""

from sys import version_info
from warnings import warn
if version_info < (3, 10):
    warn(
        message = "Math Extention expects a python version >=3.10",
        category = RuntimeWarning
    )
from .core import *
__all__ = core.__all__
# Smoke Test

from math_extension import Canvas, Symbol, Solver, Traceable, Equation

canvas = Canvas()
x = Symbol('x', 2)

expr = Traceable.parse("x^2 + 3*x + 2")
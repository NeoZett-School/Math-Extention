# Smoke Test

from math_extension import Canvas, Symbol, Solver, Traceable, Equation

canvas = Canvas()
x = Symbol('x', 0)

expr = Traceable.parse("x^2 + 3*x + 2")
equa = Equation.parse(expr == Traceable.parse(2))
print(equa.are_equal())
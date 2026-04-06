# Smoke Test

from math_extension import Canvas, Symbol, Solver, parse

canvas = Canvas()
x = Symbol('x', 2)

print(parse('x**2 + 5 == x + 3').difference())
# Smoke Test

from math_extension import Canvas, Symbol, Solver, parse

canvas = Canvas()
x = Symbol('x', 2)

print((x ** 2 + 5 == x + 4).are_equal())
# Smoke Test

from math_extension import Canvas, Symbol, Function

canvas = Canvas()
x = Symbol("x", canvas=canvas)

f = Function(x, (x**2 - 1) / (x - 1))

print(f.callable.limit("x", 1))
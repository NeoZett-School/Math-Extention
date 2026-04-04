# Smoke Test

from math_extension import Canvas, Symbol, Solver

canvas = Canvas()
x = Symbol('x')

expr = x**2 + 1

root = Solver.solve_complex(expr, 0, x, 1j)

print(f"Root: {root}")
# Smoke Test

from math_extension import Canvas, Symbol, Solver

canvas = Canvas()
x = Symbol('x')
i = Symbol('i', 1j)

expr = x**2 + 1 + 5 + 0

print(expr.simplify())

root = Solver.solve_complex(expr, 0, x, 1j)

print(f"Root: {root}")
from math_extention import Canvas, Symbol, Function, Solver, SystemSolver

canvas = Canvas()
x = Symbol("x")
y = Symbol("y")
eq1 = x**2 + y**2 - 1
eq2 = y - x

solver = SystemSolver()
# Guessing 0.5 for both should lead to sqrt(2)/2 (~0.707)
result = solver.solve_nonlinear([eq1, eq2], [x, y], [0.5, 0.5])
print(result)
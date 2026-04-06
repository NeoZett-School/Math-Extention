# Smoke Test

from math_extension import Canvas, Symbol, Equation

canvas = Canvas(thread_safe = True)
x = Symbol('x', 0, canvas=canvas)

equation = Equation.parse('42*x + 3 = 7', canvas=canvas)
print(equation.solve_all(x))
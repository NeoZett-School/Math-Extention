from math_extention import Canvas, Symbol, Function, Solver, SymbolLike

canvas = Canvas()
x = Symbol('x')
f = Function('x', x**3 - 6*x**2 + 9*x + 15)

print("Function:", f.written)

extremes = Solver.find_extrema(expr=f, symbol=x, search_range=(-5, 5))
print("Extremes:", extremes)
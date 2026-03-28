from math_extention import Canvas, Symbol, Function, Solver, SymbolLike

canvas = Canvas()
x = Symbol('x')
f = Function('x', x**3 - 6*x**2 + 9*x + 15)

# 3x**2 - 12x + 9 = 0
# x = 1, x = 3

def extreme(func: Function, symbol: SymbolLike) -> None:
    df = func.get_derivative()
    print(f'Function: {func.written}')
    print(f'First derivative: {df.written}')
    x = Solver.solve(
        expr = df, 
        target = 0, 
        symbol = symbol,
    )
    y = f(x)
    if y > 0:
        print(f'Maximum at x={(x, y)}')
    elif y < 0:
        print(f'Minimum at x={(x, y)}')
    else:
        print(f'Inflection point at x={(x, y)}')

extreme(f, x)
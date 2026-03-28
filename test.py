from math_extention import Canvas, Symbol, RegressionPoly

canvas = Canvas()
x = Symbol('x')

points = [(1, 2), (2, 7), (3, 5), (4, 7)]
regression = RegressionPoly(points, 3)
print("R_squared:", regression.r_squared())
func = regression.create_function(x)
print(func.written)
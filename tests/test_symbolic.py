from math_extension import Canvas, Symbol, Traceable

# For this test, we will use our canvas and try out symbols and 
# traceable objects in a thread-safe alternative. 

canvas = Canvas(thread_safe=True) # We must now provide the canvas to every object we create.
x = Symbol('x', canvas=canvas)

# We can create a traceable object by performing an operation on a symbol.
traceable: Traceable = x + 2
# We can now differentiate that traceable object with respect to x.
derivative = traceable.diff(x)
# We can also integrate it with respect to x.
integral = traceable.integrate(x)
# We can also get the degree of the traceable object with respect to x.
degree = traceable.get_degree(x)
# We can also get the coefficients of the traceable object with respect to x.
coefficients = traceable.get_coefficients(x)


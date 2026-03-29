# Math-Extension
**A Hybrid Symbolic-Numeric Mathematics Engine for Python.**

`Math-Extension` is a powerful library designed to bridge the gap between simple numerical calculators and complex symbolic engines. By using a **Traceable** architecture, it remembers how a formula was built, allowing for automatic differentiation, multi-variable systems solving, and advanced regression—all while maintaining high-speed numerical performance through a custom Matrix core.

## 🚀 Key Features
* **Symbolic Traceability**: Every operation is stored in a tree, allowing for `f.diff(x)` (Recursive Automatic Differentiation).
* **Advanced Regressions**: Linear, Polynomial, Exponential, Logarithmic, Power, and Multiple Linear Regression with $R^2$ validation.
* **Omniscient Root Finding**: Automatically detects polynomial degrees and calculates search ranges using Cauchy's Bound—no more manual guessing.
* **Non-Linear System Solver**: Solves systems of equations using a Jacobian-based multi-variable Newton-Raphson method.
* **Matrix Core**: Pure-Python implementation featuring Gaussian Elimination with Partial Pivoting, Inversion, and Determinants.

---

## 🛠 Installation & Setup

To use this in your project, clone the repository:

```batch
git clone https://github.com/NeoZett-School/Math-Extension.git
```

We also have a pypi page. You can download this package using:

```batch
pip install py-math-ext
```

---

## 📖 Quick Start Examples

### 1. Symbolic Differentiation & "Smart" Solving
Solve for the roots of a cubic function. The solver automatically detects the degree (3) and sets the search range using Cauchy's Bound.

```python
from math_extension import Canvas, Symbol, Function, Solver

canvas = Canvas()
x = Symbol('x')

f = Function('x', x**3 - 6*x**2 + 9*x + 15)

# The solver investigates the complexity of 'f' and finds all real roots
roots = Solver.solve_all(f, target=0, symbol=x)
print(f"Roots of {f.written}: {roots}")
```

### 2. Solving Non-Linear Systems (Jacobian Method)
Find the intersection points of a unit circle and a diagonal line.

```python
from math_extension import Canvas, Symbol, RegressionPoly

canvas = Canvas()

x, y = Symbol('x'), Symbol('y')
eq1 = x**2 + y**2 - 1  # Unit Circle equation
eq2 = y - x            # Line y = x

# Uses the multi-variable Newton-Raphson method
result = SystemSolver.solve_nonlinear([eq1, eq2], [x, y], guesses=[0.5, 0.5])
print(f"Intersection Point: {result}")
```

### 3. Data Regression & Goodness of Fit ($R^2$)
Fit a polynomial to data and verify the accuracy of the model.

```python
from math_extension import Canvas, Symbol, RegressionPoly

canvas = Canvas()
x = Symbol("x")

data = [(0, 1), (1, 2.1), (2, 3.9), (3, 9.2)]
reg = RegressionPoly(data, degree=2)

coeffs = reg.calculate() # Returns [a0, a1, a2]
accuracy = reg.r_squared() # Returns the Coefficient of Determination

print(f"Model: {reg.create_function('x').written}")
print(f"R^2 Accuracy: {accuracy:.4f}")
```

---

## 🧪 Technical Architecture

### The `Traceable` Object
Unlike standard Python floats, a `Traceable` object stores its "history." When you perform `x * 2`, it returns a new object that knows its operator was `*` and its parents were `x` and `2`. This allows the engine to perform the **Chain Rule** recursively for differentiation:
* **Power Rule**: Handles $x^n$.
* **Exponential Rule**: Handles $a^x$.
* **General Power Rule**: Handles $f(x)^{g(x)}$.

### The `Matrix` Engine
The `Matrix` class handles the heavy lifting for regressions and system solving.
* **Partial Pivoting**: Ensures numerical stability by selecting the largest available pivot.
* **Normal Equations**: Used in all regression classes to solve $(X^T X)\beta = X^T Y$.

---

## 📈 Roadmap
- [x] Trigonometric support (`sin`, `cos`, `tan`).
- [x] Automatic Complexity (Degree) Detection.
- [x] Multiple Linear Regression.
- [ ] LaTeX String Exporting for documentation.
- [ ] Residual Analysis Plotting.

---
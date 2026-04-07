from typing import (
    Union, Tuple, List, Dict, 
    Optional, Callable, Generic, 
    TypeVar, ClassVar, Self, Any
)
from collections import defaultdict
import cmath
import math

VID = int

T = TypeVar("T")
T1 = TypeVar("T1")

OPERATOR_MAPPING = {
    "+": lambda l, r: l + r,
    "-": lambda l, r: l - r,
    "*": lambda l, r: l * r,
    "/": lambda l, r: l / r,
    "**": lambda l, r: l ** r
}

# Complex numbers, helper function to choose between real and complex math functions based on input type.
def _smart_math_func(real_func: Callable, complex_func: Callable, x: Any, *args: Any, **kwargs: Any) -> Any:
    return complex_func(x, *args, **kwargs) if isinstance(x, complex) else real_func(x, *args, **kwargs)

class Value:
    """A class that represents a value in the canvas. It has a unique identifier (vid) and a value."""

    __slots__ = ("value", "vid")

    def __init__(self, value: Any) -> None:
        self.value = value
        self.vid = id(self)

class Canvas(defaultdict[int, Value]):
    """A class that represents a canvas. It is a dictionary that maps a unique identifier (vid) to a value."""

    __slots__ = ("_symbols", "_thread_safe")

    recent: ClassVar[Optional[Self]] = None

    def __init__(self, thread_safe: bool = False) -> None:
        """A class that represents a canvas. It is a dictionary that maps a unique identifier (vid) to a value."""
        defaultdict.__init__(self, Value)
        self._symbols = dict()

        self._thread_safe = thread_safe 
        # In order to be completely thread_safe, it is required 
        # that the user provides this canvas to symbols, functions, etc.

        if not thread_safe:
            Canvas.recent = self
    
    @property
    def symbols(self) -> List["Symbol"]:
        """A helper method to get all symbols in the canvas as a list."""
        return list(self._symbols.values())

    def create_value(self, value: Any) -> VID:
        v = Value(value)
        self[v.vid] = v
        return v.vid
    
    def get_name(self, vid: VID) -> Optional[str]:
        symbol = self._symbols.get(vid)
        return symbol.name if symbol else None
    
    def find_symbol(self, name: str) -> VID:
        for vid, symbol in self._symbols.items():
            if symbol.name == name:
                return vid
        return None
    
    def get_symbol(self, vid: VID) -> Optional["Symbol"]:
        return self._symbols.get(vid)
    
    def clear_symbols(self) -> None: 
        self._symbols.clear()

class Traceable:
    """A wrapper that builds a string representation and a dynamic callable."""

    __slots__ = ("_func", "name", "op", "left", "right")

    def __init__(self, func: Callable[[], Any], name: str, op: str = "CONST",
                 left: Any = None, right: Any = None) -> None:
        self._func = func  # This is the "live" math
        self.name = name   # This is the "written" math
        self.op = op
        self.left = left
        self.right = right

    def __call__(self) -> Any:
        return self._func()
    
    def calculate(self) -> Any:
        """A helper method to explicitly calculate the value of the expression. It is equivalent to calling the object itself."""
        return self()
    
    evaluate = calculate

    @staticmethod
    def wrap(other: Any) -> Self:
        if isinstance(other, Traceable):
            return other
        
        # If it's a Symbol, we need to decide if it's a variable or a constant/expression
        if hasattr(other, 'value') and hasattr(other, 'name'):
            val = other.value
            # If the Symbol's value is a Function/Expression, wrap its internal callable
            if hasattr(val, 'callable'):
                return Traceable.wrap(val.callable)
            if isinstance(val, Traceable):
                return val
            
            # Otherwise, it's a standard variable (like 'x')
            return Traceable(lambda: other.value, other.name, op="VAR")
            
        # If it's a Function or Expression class, grab its underlying callable
        if hasattr(other, 'callable'):
            return Traceable.wrap(other.callable)
            
        # Raw number
        return Traceable(lambda: other, str(other), op="CONST")
    
    @staticmethod
    def parse(expr: Union[str, 'Traceable', 'Expression', Any], canvas: Optional[Canvas] = None) -> 'Traceable':
        if isinstance(expr, Traceable):
            return expr
        if not isinstance(expr, str):
            return Traceable.wrap(expr)
        if "=" in expr:
            raise ValueError("Equations are not supported in Traceable parsing. Use the 'Equation' class instead.")
        return parse(expr, canvas)
    
    # --- DERIVATION ---
    def diff(self, var: str) -> Self:
        if self.op == "CONST": return Traceable.wrap(0)
        if self.op == "VAR": return Traceable.wrap(1) if self.name == var else Traceable.wrap(0)
        
        if self.op == "+": return self.left.diff(var) + self.right.diff(var)
        if self.op == "-": return self.left.diff(var) - self.right.diff(var)
        
        if self.op == "*": # Product Rule: f'g + fg'
            return (self.left.diff(var) * self.right) + (self.left * self.right.diff(var))
            
        if self.op == "/": # Quotient Rule: (f'g - fg') / g^2
            num = (self.left.diff(var) * self.right) - (self.left * self.right.diff(var))
            return num / (self.right ** 2)

        if self.op == "**": 
            # Case 1: Power Rule (x^n)' = n * x^(n-1) * x'
            if self.right.op == "CONST":
                n = float(self.right.name)
                return Traceable.wrap(n) * (self.left ** (n - 1)) * self.left.diff(var)
            
            # Case 2: Exponential Rule (a^u)' = a^u * ln(a) * u'
            if self.left.op == "CONST":
                a = float(self.left.name)
                # We use our 'LOG' op here: ln(a)
                ln_a = Traceable(lambda: _smart_math_func(math.log, cmath.log, a), f"ln({a})", op="LOG", left=self.left)
                return self * ln_a * self.right.diff(var)

            # Case 3: General Power Rule (f^g)' = f^g * (g' * ln(f) + g * f' / f)
            # This covers cases like x^x
            ln_f = Traceable(lambda: _smart_math_func(math.log, cmath.log, self.left()), f"ln({self.left.name})", op="LOG", left=self.left)
            term1 = self.right.diff(var) * ln_f
            term2 = self.right * (self.left.diff(var) / self.left)
            return self * (term1 + term2)
        
        if self.op == "LOG": # Chain Rule: ln(u)' = u' / u
            return self.left.diff(var) / self.left
        
        if self.op == "SIN":
            # Chain Rule: sin(u)' = cos(u) * u'
            cos_u = Traceable(lambda: _smart_math_func(math.cos, cmath.cos, self.left()), f"cos({self.left.name})", op="COS", left=self.left)
            return cos_u * self.left.diff(var)

        if self.op == "COS":
            # Chain Rule: cos(u)' = -sin(u) * u'
            sin_u = Traceable(lambda: _smart_math_func(math.sin, cmath.sin, self.left()), f"sin({self.left.name})", op="SIN", left=self.left)
            return Traceable.wrap(-1) * sin_u * self.left.diff(var)

        if self.op == "TAN":
            # Chain Rule: tan(u)' = sec^2(u) * u' = (1 / cos^2(u)) * u'
            cos_u = Traceable(lambda: _smart_math_func(math.cos, cmath.cos, self.left()), f"cos({self.left.name})", op="COS", left=self.left)
            return (Traceable.wrap(1) / (cos_u ** 2)) * self.left.diff(var)
        
        raise NotImplementedError(f"Diff for {self.op} not supported.")

    # --- INTEGRATION (Power Rule & Linearity) ---
    def integrate(self, var_obj: Any) -> Self:
        # We need the name string for matching ops, but the object for wrapping
        var_name = var_obj.name if hasattr(var_obj, 'name') else str(var_obj)
        
        if self.op == "CONST": 
            # ∫ c dx = c * x
            # Use wrap(var_obj) to ensure we get a lambda: x.value
            return self * Traceable.wrap(var_obj)
            
        if self.op == "VAR": 
            if self.name == var_name:
                # ∫ x dx = (x^2) / 2
                return (self ** 2) / 2
            # ∫ y dx = y * x (Treating other variables as constants)
            return self * Traceable.wrap(var_obj)

        if self.op == "+": 
            return self.left.integrate(var_obj) + self.right.integrate(var_obj)
        
        if self.op == "-": 
            return self.left.integrate(var_obj) - self.right.integrate(var_obj)

        if self.op == "*":
            # Linear combination: ∫ c * f(x) dx = c * ∫ f(x) dx
            if self.left.op == "CONST": 
                return self.left * self.right.integrate(var_obj)
            if self.right.op == "CONST":
                return self.left.integrate(var_obj) * self.right
            
            # Note: Integration of f(x)*g(x) (Integration by Parts) is not 
            # "quick and dirty" enough for a basic polynomial system.
            raise NotImplementedError("General Product integration not supported.")

        if self.op == "**": 
            # Power Rule: ∫ x^n dx = x^(n+1) / (n+1)
            if self.left.op == "VAR" and self.left.name == var_name and self.right.op == "CONST":
                n = float(self.right.name)
                return (self.left ** (n + 1)) / (n + 1)
        
        if self.op == "LOG":
            if self.left.op == "VAR" and self.left.name == var_name:
                # ∫ ln(x) dx = x*ln(x) - x
                return (self.left * self) - self.left

        raise NotImplementedError(f"Integration for operator '{self.op}' not supported.")
    
    def get_degree(self, var: str) -> int:
        """Recursively finds the highest power of the given variable."""
        if self.op == "CONST": 
            return 0
        if self.op == "VAR": 
            return 1 if self.name == var else 0
        
        if self.op in ("+", "-"):
            return max(self.left.get_degree(var), self.right.get_degree(var))
        
        if self.op == "*":
            # x * x = x^2, so we add degrees for multiplication
            return self.left.get_degree(var) + self.right.get_degree(var)
            
        if self.op == "/":
            # For simplicity, we handle polynomials. 
            # If dividing by x, the degree technically drops, but we'll stick to numerator.
            return self.left.get_degree(var)

        if self.op == "**":
            if self.right.op == "CONST":
                # (x^2)^3 = x^6, so we multiply degrees
                base_degree = self.left.get_degree(var)
                power = int(float(self.right.name))
                return base_degree * power
        
        if self.op in ("SIN", "COS", "TAN"):
            # Trig functions don't have a "degree," but they wiggle a lot.
            # Return a high enough number to force the solver to sample 
            # more intervals within the range.
            return 4
        
        return 1 # Fallback for unknown ops like LOG/EXP/etc.
    
    def get_coefficients(self, var_name: str, canvas: Optional[Canvas] = None) -> List[float]:
        """
        Uses a system of linear equations to find coefficients for a polynomial.
        If f(x) = a2*x^2 + a1*x + a0, it returns [a0, a1, a2].
        """
        deg = self.get_degree(var_name)
        if deg == 0: return [float(self())]
        
        # We need deg + 1 points to solve for deg + 1 unknowns
        # We'll pick x = 0, 1, 2, ..., deg
        A_data = []
        B_data = []
        
        canvas = canvas if canvas is not None else Canvas.recent
        sym = canvas.get_symbol(canvas.find_symbol(var_name))
        if sym is None:
            raise ValueError(f"Unknown variable {var_name}")
        
        original_val = sym.value
        
        for x_val in range(deg + 1):
            # Row in matrix: [x^0, x^1, x^2, ..., x^deg]
            row = [float(x_val**i) for i in range(deg + 1)]
            A_data.append(row)
            
            # Resulting y value
            sym.value = x_val
            B_data.append([float(self())])
            
        sym.value = original_val # Restore canvas state
        
        # Solve the system to get [a0, a1, a2...]
        A = Matrix(A_data)
        B = Matrix(B_data)
        coeffs = A.solve(B)
        
        return [row[0] for row in coeffs.data]
    
    def simplify(self) -> Self:
        # Base cases: constants and variables cannot be simplified further
        if self.op in ("CONST", "VAR"):
            return self

        # Recursively simplify the left and right branches first
        left = self.left.simplify() if isinstance(self.left, Traceable) else self.left
        right = self.right.simplify() if isinstance(self.right, Traceable) else self.right

        # --- NEW: Constant Folding ---
        # If both sides are constants, we can compute the result immediately
        if left.op == "CONST" and right.op == "CONST":
            # Create a temporary Traceable to perform the math and wrap the result
            # This handles (5 + 5) -> 10 or (2 * 5) -> 10
            try:
                # We call them to get their raw numeric values
                val = OPERATOR_MAPPING[self.op](float(left.name), float(right.name))
                return Traceable.wrap(val)
            except (KeyError, ValueError, ZeroDivisionError):
                pass # Fall back to algebraic simplification if math fails

        # --- Algebraic Simplifications (Existing + Improved) ---
        if self.op == "+":
            if left.op == "CONST" and float(left.name) == 0: return right
            if right.op == "CONST" and float(right.name) == 0: return left
            if left.name == right.name: return Traceable.wrap(2) * left

        if self.op == "-":
            if right.op == "CONST" and float(right.name) == 0: return left
            if left.name == right.name: return Traceable.wrap(0)

        if self.op == "*":
            if left.op == "CONST":
                val = float(left.name)
                if val == 0: return left
                if val == 1: return right
            if right.op == "CONST":
                val = float(right.name)
                if val == 0: return right
                if val == 1: return left

        if self.op == "/":
            if right.op == "CONST":
                val = float(right.name)
                if val == 1: return left
                if val == 0: raise ZeroDivisionError("Cannot simplify division by zero.")

        # Return the new combined Traceable if no simplification was possible
        return Traceable(self._func, self.name, self.op, left, right)
    
    def limit(
        self,
        var: str,
        to: float,
        direction: str = "both",
        max_steps: int = 10,
        canvas: Optional[Canvas] = None
    ) -> float:
        canvas = canvas if canvas is not None else Canvas.recent
        sym = canvas.get_symbol(canvas.find_symbol(var))
        if sym is None:
            raise ValueError(f"Unknown variable {var}")

        old = sym.value

        def _safe_eval(expr: "Traceable", xval: Number):
            sym.value = xval
            return expr()

        try:
            expr = self.simplify()

            # -------------------------
            # 1) exact subtree rules
            # -------------------------
            if expr.op == "CONST":
                return float(expr.name)

            if expr.op == "VAR":
                return to if expr.name == var else expr()

            if expr.op == "+":
                return expr.left.limit(var, to, direction, max_steps, canvas) + \
                    expr.right.limit(var, to, direction, max_steps, canvas)

            if expr.op == "-":
                return expr.left.limit(var, to, direction, max_steps, canvas) - \
                    expr.right.limit(var, to, direction, max_steps, canvas)

            if expr.op == "*":
                return expr.left.limit(var, to, direction, max_steps, canvas) * \
                    expr.right.limit(var, to, direction, max_steps, canvas)

            # -------------------------
            # 2) quotient rules
            # -------------------------
            if expr.op == "/":
                num = expr.left
                den = expr.right

                # infinity rational rule
                if math.isinf(to):
                    ld = num.get_degree(var)
                    rd = den.get_degree(var)

                    if ld < rd:
                        return 0.0
                    elif ld == rd:
                        a = num.get_coefficients(var)[-1]
                        b = den.get_coefficients(var)[-1]
                        return a / b

                for _ in range(max_steps):
                    nlim = num.limit(var, to, direction, max_steps, canvas)
                    dlim = den.limit(var, to, direction, max_steps, canvas)

                    zero_zero = abs(nlim) < 1e-12 and abs(dlim) < 1e-12
                    inf_inf = math.isinf(nlim) and math.isinf(dlim)

                    if zero_zero or inf_inf:
                        num = num.diff(var).simplify()
                        den = den.diff(var).simplify()
                        continue

                    return nlim / dlim

            # -------------------------
            # 3) power rules
            # -------------------------
            if expr.op == "**":
                base_lim = expr.left.limit(var, to, direction, max_steps, canvas)
                exp_lim = expr.right.limit(var, to, direction, max_steps, canvas)

                # classic indeterminate powers
                if base_lim == 1 and math.isinf(exp_lim):
                    transformed = Traceable.exp(
                        expr.right * Traceable.log(expr.left)
                    )
                    return transformed.limit(var, to, direction, max_steps, canvas)

                return base_lim ** exp_lim

            # -------------------------
            # 4) special trig limits
            # -------------------------
            if expr.op == "/" and expr.left.op == "SIN":
                if expr.left.left.name == var and expr.right.name == var and to == 0:
                    return 1.0

            # -------------------------
            # 5) direct substitution
            # -------------------------
            try:
                val = _safe_eval(expr, to)
                if not (math.isnan(val) or math.isinf(val)):
                    return val
            except:
                pass

            # -------------------------
            # 6) one-sided numeric fallback
            # -------------------------
            eps = 1e-7

            if direction == "left":
                return _safe_eval(expr, to - eps)

            if direction == "right":
                return _safe_eval(expr, to + eps)

            lv = _safe_eval(expr, to - eps)
            rv = _safe_eval(expr, to + eps)

            if abs(lv - rv) < 1e-5:
                return (lv + rv) / 2

            raise ValueError("Two-sided limit does not exist")

        finally:
            sym.value = old
    
    @classmethod
    def sin(cls, expr: Any) -> Self:
        expr = Traceable.wrap(expr)
        return Traceable(
            lambda: _smart_math_func(math.sin, cmath.sin, expr()), 
            f"sin({expr.name})", 
            op="SIN", 
            left=expr
        )

    @classmethod
    def cos(cls, expr: Any) -> Self:
        expr = Traceable.wrap(expr)
        return cls(
            lambda: _smart_math_func(math.cos, cmath.cos, expr()), 
            f"cos({expr.name})", 
            op="COS", 
            left=expr
        )

    @classmethod
    def tan(cls, expr: Any) -> Self:
        expr = Traceable.wrap(expr)
        return cls(
            lambda: _smart_math_func(math.tan, cmath.tan, expr()), 
            f"tan({expr.name})", 
            op="TAN", 
            left=expr
        )
    
    @classmethod
    def log(cls, expr: Any, base: Optional[float] = None) -> Self:
        expr = Traceable.wrap(expr)
        if base is None:
            return cls(
                lambda: _smart_math_func(math.log, cmath.log, expr()), 
                f"ln({expr.name})", 
                op="LOG", 
                left=expr
            )
        else:
            return cls(
                lambda: _smart_math_func(math.log, cmath.log, expr(), base), 
                f"log_{base}({expr.name})", 
                op="LOG", 
                left=expr
            )
    
    @classmethod
    def exp(cls, expr: Any) -> Self:
        expr = Traceable.wrap(expr)
        return Traceable(
            lambda: _smart_math_func(math.exp, cmath.exp, expr()), 
            f"exp({expr.name})", 
            op="EXP", 
            left=expr
        )
    
    @classmethod
    def sqrt(cls, expr: Any) -> Self:
        expr = Traceable.wrap(expr)
        return cls(
            lambda: cmath.sqrt(expr()),
            f"sqrt({expr.name})",
            op="SQRT",
            left=expr
        )
    
    @classmethod
    def conjugate(cls, expr: Any) -> Self:
        expr = Traceable.wrap(expr)
        return cls(
            lambda: expr().conjugate(),
            f"conj({expr.name})",
            op="CONJ",
            left=expr
        )

    @classmethod
    def abs(cls, expr: Any) -> Self:
        expr = Traceable.wrap(expr)
        return cls(
            lambda: abs(expr()),
            f"|{expr.name}|",
            op="ABS",
            left=expr
        )
    
    @property
    def real(self) -> float:
        return self().real
    
    @property
    def imag(self) -> float:
        return self().imag

    def __add__(self, other: Union[Self, Any]) -> Self:
        other = Traceable.wrap(other)
        return Traceable(
            lambda: self() + other(), 
            f"({self.name} + {other.name})",
            "+", self, other
        )
    
    def __radd__(self, other: Union[Self, Any]) -> Self:
        other = Traceable.wrap(other)
        return Traceable(
            lambda: other() + self(), 
            f"({other.name} + {self.name})",
            "+", other, self
        )

    def __mul__(self, other: Union[Self, Any]) -> Self:
        other = Traceable.wrap(other)
        return Traceable(
            lambda: self() * other(), 
            f"({self.name} * {other.name})",
            "*", self, other
        )
    
    def __rmul__(self, other: Union[Self, Any]) -> Self:
        other = Traceable.wrap(other)
        return Traceable(
            lambda: other() * self(), 
            f"({other.name} * {self.name})",
            "*", other, self
        )
    
    def __sub__(self, other: Union[Self, Any]) -> Self:
        other = Traceable.wrap(other)
        return Traceable(
            lambda: self() - other(), 
            f"({self.name} - {other.name})",
            "-", self, other
        )
    
    def __rsub__(self, other: Union[Self, Any]) -> Self:
        other = Traceable.wrap(other)
        return Traceable(
            lambda: other() - self(), 
            f"({other.name} - {self.name})",
            "-", other, self
        )
    
    def __truediv__(self, other: Union[Self, Any]) -> Self:
        other = Traceable.wrap(other)
        return Traceable(
            lambda: self() / other(), 
            f"({self.name} / {other.name})",
            "/", self, other
        )
    
    def __rtruediv__(self, other: Union[Self, Any]) -> Self:
        other = Traceable.wrap(other)
        return Traceable(
            lambda: other() / self(), 
            f"({other.name} / {self.name})",
            "/", other, self
        )
    
    def __pow__(self, other: Union[Self, Any]) -> Self:
        other = Traceable.wrap(other)
        return Traceable(
            lambda: self() ** other(), 
            f"({self.name} ** {other.name})",
            "**", self, other
        )
    
    def __rpow__(self, other: Union[Self, Any]) -> Self:
        other = Traceable.wrap(other)
        return Traceable(
            lambda: other() ** self(), 
            f"({other.name} ** {self.name})",
            "**", other, self
        )
    
    def __neg__(self) -> Self:
        return Traceable.wrap(-1) * self
    
    def __eq__(self, other: Any) -> Union[bool, "Equation"]:
        if isinstance(other, Traceable):
            return Equation(self, other)
        return self() == other
    
    def __ge__(self, other: Any) -> bool:
        return self() >= (Traceable.wrap(other)())
    
    def __le__(self, other: Any) -> bool:
        return self() <= (Traceable.wrap(other)())
    
    def __gt__(self, other: Any) -> bool:
        return self() > (Traceable.wrap(other)())
    
    def __lt__(self, other: Any) -> bool:
        return self() < (Traceable.wrap(other)())

    def __repr__(self) -> str:
        return self.name

class Symbol(tuple[str, int]):
    """A class that represents a symbol in the canvas. It has a unique identifier (vid) and a name."""

    def __new__(cls, name: str, value: Any = 0, canvas: Optional[Canvas] = None) -> Self:
        """A class that represents a symbol in the canvas. It has a unique identifier (vid) and a name."""
        canvas = canvas if canvas is not None else Canvas.recent
        self = super().__new__(cls, (name, canvas.create_value(value)))
        canvas._symbols[self[1]] = self
        self._canvas = canvas
        return self
    
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """If a symbols value is callable (as in a Function), calling the symbol will call its value. This allows you to use symbols as functions without needing to access their value directly."""
        if callable(self.value):
            return self.value(*args, **kwargs)
    
    @property
    def written(self) -> Optional[str]:
        """A helper method to get the string representation of the symbol. It returns None if the symbol is not traceable or a expression."""
        val = self.value
        if isinstance(val, Traceable):
            return val.name
        if hasattr(val, 'written'):
            return val.written
    
    @property
    def name(self) -> str:
        return self[0]
    
    @property
    def value(self) -> Any:
        return self._canvas[self[1]].value
    
    @value.setter
    def value(self, new_value: Any) -> None:
        self._canvas[self[1]].value = new_value
    
    def __add__(self, other: Self) -> Traceable: 
        return Traceable.wrap(self) + other
    def __radd__(self, other: Self) -> Traceable: 
        return Traceable.wrap(other) + self

    def __sub__(self, other: Self) -> Traceable: 
        return Traceable.wrap(self) - other
    def __rsub__(self, other: Self) -> Traceable: 
        return Traceable.wrap(other) - self

    def __mul__(self, other: Self) -> Traceable: 
        return Traceable.wrap(self) * other
    def __rmul__(self, other: Self) -> Traceable: 
        return Traceable.wrap(other) * self

    def __truediv__(self, other: Self) -> Traceable: 
        return Traceable.wrap(self) / other
    def __rtruediv__(self, other: Self) -> Traceable: 
        return Traceable.wrap(other) / self

    def __pow__(self, other: Self) -> Traceable: 
        return Traceable.wrap(self) ** other
    def __rpow__(self, other: Self) -> Traceable: 
        return Traceable.wrap(other) ** self
    
    def __neg__(self) -> Traceable:
        return -Traceable.wrap(self)
    
    def __eq__(self, val: Any) -> Union[bool, "Equation"]:
        if isinstance(val, Traceable):
            return Equation(Traceable.wrap(self), val)
        return self.value == val
    
    def __ge__(self, other: Any) -> bool:
        return self.value >= (Traceable.wrap(other)())

    def __le__(self, other: Any) -> bool:
        return self.value <= (Traceable.wrap(other)())
    
    def __gt__(self, other: Any) -> bool:
        return self.value > (Traceable.wrap(other)())
    
    def __lt__(self, other: Any) -> bool:
        return self.value < (Traceable.wrap(other)())
    
    def create_reference(self) -> "Reference":
        return Reference(self.name, self._canvas[self[1]])

class Reference:
    """An absolute reference to a symbol in the canvas. It has a value and a name."""

    __slots__ = ("name", "object", "value")

    def __init__(self, name: Optional[str], object: Union[Value, Any]) -> None:
        self.name = name
        self.object = object if isinstance(object, Value) else None
        self.value = object.value if isinstance(object, Value) else object
    
    @property
    def vid(self) -> Optional[VID]:
        return self.object.vid if self.object is not None else None

class Expression(Generic[T1]):
    """A class that represents an expression in the canvas. It is a callable object that takes a canvas as an argument and returns a value.
    
    The expression can be built from a Traceable object or a simple callable. If it is built from a Traceable object, it will have a string 
    representation that can be accessed through the `written` property. If it is built from a simple callable, the `written` property will 
    return None. You can build a traceable object by simply using the operators on your symbols, or by using the Traceable class directly. 
    The expression will not be evaluated directly, but only when you call this object. This allows you to build complex expressions without 
    worrying about the order of evaluation or the state of the canvas at the time of building the expression."""

    __slots__ = ("_canvas", "callable",)

    def __init__(self, func: Union[Callable[[], T1], Traceable], canvas: Optional[Canvas] = None) -> None:
        self._canvas = canvas if canvas is not None else Canvas.recent
        self.callable = func
    
    @property
    def written(self) -> Optional[str]:
        """A helper method to get the string representation of the expression. It returns None if the expression is not traceable."""
        return self.callable.name if isinstance(self.callable, Traceable) else None
    
    def calculate(self) -> T1:
        """A helper method to explicitly calculate the value of the expression. It is equivalent to calling the object itself."""
        return self.callable()
    
    evaluate = calculate
    
    def __call__(self) -> T1:
        return self.callable()

SymbolLike = Union[str, Symbol, Reference, VID]

def get_symbol(canvas: Canvas, symbol_like: SymbolLike) -> Optional[Symbol]:
    """A helper function that takes a symbol-like object and returns the corresponding symbol from the canvas. It can take a string (name), a Symbol object, a Reference object, or a VID (integer)."""
    if isinstance(symbol_like, str):
        return canvas.get_symbol(canvas.find_symbol(symbol_like))
    elif isinstance(symbol_like, Symbol):
        return symbol_like
    elif isinstance(symbol_like, Reference):
        return canvas.get_symbol(symbol_like.vid)
    elif isinstance(symbol_like, int):
        return canvas.get_symbol(symbol_like)
    else:
        return None

class Function(Generic[T, T1], Expression[T1]):
    """A class that represents a function in the canvas. It is a callable object that takes a canvas as an argument and returns a value."""

    __slots__ = ("symbol",)

    def __init__(self, symbol: SymbolLike, func: Union[Callable[[], T1], Traceable], canvas: Optional[Canvas] = None) -> None:
        Expression.__init__(self, func, canvas)
        self.symbol = get_symbol(self._canvas, symbol)
    
    @property
    def name(self) -> Optional[str]:
        return self.symbol.name if self.symbol else None
    
    def calculate(self, value: T) -> T1:
        self.symbol.value = value
        return self.callable()
    
    evaluate = calculate
    
    def __call__(self, value: T) -> T1:
        self.symbol.value = value
        return self.callable()
    
    def derivative(self, value: float, h: float = 1e-5) -> float:
        """Calculates the numerical derivative at a specific point."""
        return (self(value + h) - self(value)) / h

    def integral(self, start: float, end: float, steps: int = 1000) -> float:
        """Calculates the definite integral using the Trapezoidal Rule."""
        dx = (end - start) / steps
        total = 0.5 * (self(start) + self(end))
        for i in range(1, steps):
            total += self(start + i * dx)
        return total * dx
    
    def get_derivative(self) -> Self:
        """Returns a new Function that is the derivative of this one."""
        if not isinstance(self.callable, Traceable):
            raise ValueError("Function must be Traceable for symbolic calculus.")
        deriv = self.callable.diff(self.symbol.name).simplify()
        return Function(self.symbol, deriv, self._canvas)

    def get_integral(self) -> Self:
        """Returns a new Function that is the indefinite integral (Primitive)."""
        if not isinstance(self.callable, Traceable):
            raise ValueError("Function must be Traceable for symbolic calculus.")
        # FIX: Pass the object self.symbol, not self.symbol.name
        integ_traceable = self.callable.integrate(self.symbol).simplify()
        return Function(self.symbol, integ_traceable, self._canvas)

Point = Tuple[float, float]
Points = List[Point]

Number = Union[float, complex]

class Matrix:
    __slots__ = ("rows", "cols", "data")

    def __init__(self, data: List[List[Number]]) -> None:
        self.data = data
        self.rows = len(data)
        self.cols = len(data[0]) if self.rows > 0 else 0

    @classmethod
    def zeros(cls, rows: int, cols: int) -> "Matrix":
        return cls([[0.0 for _ in range(cols)] for _ in range(rows)])

    @classmethod
    def identity(cls, n: int) -> "Matrix":
        m = cls.zeros(n, n)
        for i in range(n): m.data[i][i] = 1.0
        return m

    def __mul__(self, other: Union["Matrix", float]) -> "Matrix":
        if isinstance(other, (int, float)):
            return Matrix([[cell * other for cell in row] for row in self.data])
        
        # Matrix Multiplication
        result = Matrix.zeros(self.rows, other.cols)
        for i in range(self.rows):
            for j in range(other.cols):
                result.data[i][j] = sum(self.data[i][k] * other.data[k][j] for k in range(self.cols))
        return result

    def transpose(self) -> "Matrix":
        return Matrix([[self.data[j][i] for j in range(self.rows)] for i in range(self.cols)])

    def inverse(self) -> "Matrix":
        """Gauss-Jordan elimination to find the inverse."""
        if self.rows != self.cols: raise ValueError("Only square matrices can be inverted.")
        n = self.rows
        aug = [row + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(self.data)]

        for i in range(n):
            pivot = aug[i][i]
            if pivot == 0: raise ValueError("Matrix is singular and cannot be inverted.")
            for j in range(i, 2 * n): aug[i][j] /= pivot
            for k in range(n):
                if k != i:
                    factor = aug[k][i]
                    for j in range(i, 2 * n): aug[k][j] -= factor * aug[i][j]

        return Matrix([row[n:] for row in aug])
    
    def det(self) -> float:
        """Calculates the determinant using Gaussian elimination."""
        if self.rows != self.cols:
            raise ValueError("Determinant only exists for square matrices.")
        
        n = self.rows
        # Copy data to avoid mutating the original matrix
        mat = [row[:] for row in self.data]
        det_val = 1.0

        for i in range(n):
            # Pivot selection
            pivot_row = i
            while pivot_row < n and mat[pivot_row][i] == 0:
                pivot_row += 1
            
            if pivot_row == n:
                return 0.0 # Matrix is singular
            
            if pivot_row != i:
                mat[i], mat[pivot_row] = mat[pivot_row], mat[i]
                det_val *= -1.0 # Swapping rows flips the sign
            
            pivot = mat[i][i]
            det_val *= pivot
            
            for k in range(i + 1, n):
                factor = mat[k][i] / pivot
                for j in range(i + 1, n):
                    mat[k][j] -= factor * mat[i][j]
                    
        return det_val
    
    def solve(self, B: "Matrix") -> "Matrix":
        """Solves AX = B using Gaussian Elimination with Partial Pivoting."""
        if self.rows != self.cols:
            raise ValueError("Matrix must be square to solve AX = B.")
        if self.rows != B.rows:
            raise ValueError("Dimension mismatch between A and B.")

        n = self.rows
        # Create an augmented matrix [A | B]
        A_data = [row[:] for row in self.data]
        B_data = [row[:] for row in B.data]
        
        # Forward Elimination
        for i in range(n):
            # Pivot selection (find the largest element in the column for stability)
            max_row = i
            for k in range(i + 1, n):
                if abs(A_data[k][i]) > abs(A_data[max_row][i]):
                    max_row = k
            
            # Swap rows in A and B
            A_data[i], A_data[max_row] = A_data[max_row], A_data[i]
            B_data[i], B_data[max_row] = B_data[max_row], B_data[i]

            pivot = A_data[i][i]
            if abs(pivot) < 1e-12:
                raise ValueError("Matrix is singular or near-singular.")

            # Eliminate other rows
            for k in range(i + 1, n):
                factor = A_data[k][i] / pivot
                for j in range(i, n):
                    A_data[k][j] -= factor * A_data[i][j]
                for j in range(B.cols):
                    B_data[k][j] -= factor * B_data[i][j]

        # Back Substitution
        X_data = [[0.0 for _ in range(B.cols)] for _ in range(n)]
        for i in range(n - 1, -1, -1):
            for j in range(B.cols):
                sum_val = sum(A_data[i][k] * X_data[k][j] for k in range(i + 1, n))
                X_data[i][j] = (B_data[i][j] - sum_val) / A_data[i][i]

        return Matrix(X_data)

def calculate_r_squared(points: Points, model_func: Callable[[float], float]) -> float:
    """Calculates the R^2 value for a given set of points and a model."""
    y_values = [p[1] for p in points]
    y_mean = sum(y_values) / len(y_values)
    
    # Total Sum of Squares (Variance from the mean)
    ss_tot = sum((y - y_mean) ** 2 for y in y_values)
    
    # Residual Sum of Squares (Variance from our model)
    ss_res = sum((p[1] - model_func(p[0])) ** 2 for p in points)
    
    if ss_tot == 0: return 1.0 # Avoid division by zero for constant data
    return 1 - (ss_res / ss_tot)

class RegressionLin:
    """A class that represents a regression. It is a callable object that takes a list of points as an argument and returns a value."""

    __slots__ = ("points",)

    def __init__(self, points: Points) -> None:
        self.points = points
    
    def __call__(self) -> Tuple[float, float]:
        n = len(self.points)
        if n == 0:
            return (0.0, 0.0)
        sum_x = sum(point[0] for point in self.points)
        sum_y = sum(point[1] for point in self.points)
        sum_xx = sum(point[0] ** 2 for point in self.points)
        sum_xy = sum(point[0] * point[1] for point in self.points)
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x ** 2)
        intercept = (sum_y - slope * sum_x) / n
        return (slope, intercept)
    
    def calculate(self) -> Tuple[float, float]:
        return self()
    
    evaluate = calculate
    
    def r_squared(self) -> float:
        coeffs = self()
        def model(x):
            # Evaluate: a0 + a1*x + a2*x^2 ...
            return sum(coeffs[i] * (x ** i) for i in range(len(coeffs)))
        
        return calculate_r_squared(self.points, model)
    
    def create_function(self, symbol: SymbolLike, canvas: Optional[Canvas] = None) -> Function[float, float]:
        slope, intercept = self()
        canvas = canvas if canvas is not None else Canvas.recent
        sym = get_symbol(canvas, symbol)

        # This looks like math, but it's actually building the Traceable object!
        # sym is converted to Traceable automatically by our __mul__ override
        expr = sym * slope + intercept

        return Function(sym, expr, canvas)
    
class RegressionPoly:
    """Handles Polynomial Regression of a specified degree."""

    __slots__ = ("points", "degree")

    def __init__(self, points: Points, degree: int = 2) -> None:
        self.points = points
        self.degree = degree

    def __call__(self) -> List[float]:
        """Returns the coefficients [a0, a1, a2...] using Least Squares."""
        X_data = [[x**i for i in range(self.degree + 1)] for x, _ in self.points]
        Y_data = [[y] for _, y in self.points]

        X = Matrix(X_data)
        Y = Matrix(Y_data)
        XT = X.transpose()

        # Solve the Normal Equation: (XT * X) * coeffs = (XT * Y)
        A = XT * X
        B = XT * Y
        
        coeffs = A.solve(B)
        return [row[0] for row in coeffs.data]
    
    def calculate(self) -> Tuple[float, float]:
        return self()
    
    evaluate = calculate
    
    def r_squared(self) -> float:
        coeffs = self()
        def model(x):
            # Evaluate: a0 + a1*x + a2*x^2 ...
            return sum(coeffs[i] * (x ** i) for i in range(len(coeffs)))
        
        return calculate_r_squared(self.points, model)

    def create_function(self, symbol: SymbolLike, canvas: Optional[Canvas] = None) -> Function[float, float]:
        coeffs = self()
        canvas = canvas if canvas is not None else Canvas.recent
        sym = get_symbol(canvas, symbol)
        
        # Build the Traceable expression: a0 + a1*x + a2*x^2 ...
        expr = Traceable.wrap(coeffs[0])
        for i in range(1, len(coeffs)):
            expr = expr + (Traceable.wrap(coeffs[i]) * (sym ** i))
            
        return Function(sym, expr, canvas)

class RegressionExp:
    """Handles Exponential Regression y = a * b^x."""

    __slots__ = ("points",)

    def __init__(self, points: Points) -> None:
        # Note: y-values must be > 0 for log transformation
        self.points = [(x, y) for x, y in points if y > 0]

    def __call__(self) -> Tuple[float, float]:
        """Returns (a, b) for the formula y = a * b^x."""
        # 1. Transform points to (x, ln(y))
        log_points = [(x, math.log(y)) for x, y in self.points]
        
        # 2. Use your existing Linear Regression on the transformed data
        lin_reg = RegressionLin(log_points)
        slope, intercept = lin_reg()
        
        # 3. Transform coefficients back
        a = math.exp(intercept)
        b = math.exp(slope)
        return (a, b)
    
    def calculate(self) -> Tuple[float, float]:
        return self()
    
    evaluate = calculate
    
    def r_squared(self) -> float:
        coeffs = self()
        def model(x):
            # Evaluate: a0 + a1*x + a2*x^2 ...
            return sum(coeffs[i] * (x ** i) for i in range(len(coeffs)))
        
        return calculate_r_squared(self.points, model)

    def create_function(self, symbol: SymbolLike, canvas: Optional[Canvas] = None) -> Function[float, float]:
        a, b = self()
        canvas = canvas if canvas is not None else Canvas.recent
        sym = get_symbol(canvas, symbol)
        
        # Formula: a * (b ** x)
        expr = Traceable.wrap(a) * (Traceable.wrap(b) ** sym)
        return Function(sym, expr, canvas)

class RegressionLog:
    """Handles Logarithmic Regression y = a + b * ln(x)."""

    __slots__ = ("points",)

    def __init__(self, points: Points) -> None:
        # x-values must be > 0
        self.points = [(x, y) for x, y in points if x > 0]

    def __call__(self) -> Tuple[float, float]:
        """Returns (a, b) for the formula y = a + b * ln(x)."""
        # 1. Transform points to (ln(x), y)
        log_x_points = [(math.log(x), y) for x, y in self.points]
        
        # 2. Use Linear Regression: y = intercept + slope * ln(x)
        lin_reg = RegressionLin(log_x_points)
        slope, intercept = lin_reg()
        
        # intercept is 'a', slope is 'b'
        return (intercept, slope)
    
    def calculate(self) -> Tuple[float, float]:
        return self()
    
    evaluate = calculate
    
    def r_squared(self) -> float:
        coeffs = self()
        def model(x):
            # Evaluate: a0 + a1*x + a2*x^2 ...
            return sum(coeffs[i] * (x ** i) for i in range(len(coeffs)))
        
        return calculate_r_squared(self.points, model)

    def create_function(self, symbol: SymbolLike, canvas: Optional[Canvas] = None) -> Function[float, float]:
        a, b = self()
        canvas = canvas if canvas is not None else Canvas.recent
        sym = get_symbol(canvas, symbol)

        expr = Traceable.wrap(a) + (Traceable.wrap(b) * Traceable.log(sym))
        
        return Function(sym, expr, canvas)

class RegressionPower:
    """Handles Power Regression y = a * x^b."""

    __slots__ = ("points",)

    def __init__(self, points: Points) -> None:
        # Both x and y must be > 0
        self.points = [(x, y) for x, y in points if x > 0 and y > 0]

    def __call__(self) -> Tuple[float, float]:
        """Returns (a, b) for y = a * x^b."""
        # Transform to (ln(x), ln(y))
        log_log_points = [(math.log(x), math.log(y)) for x, y in self.points]
        
        lin_reg = RegressionLin(log_log_points)
        slope, intercept = lin_reg()
        
        a = math.exp(intercept)
        b = slope
        return (a, b)
    
    def calculate(self) -> Tuple[float, float]:
        return self()
    
    evaluate = calculate
    
    def r_squared(self) -> float:
        coeffs = self()
        def model(x):
            # Evaluate: a0 + a1*x + a2*x^2 ...
            return sum(coeffs[i] * (x ** i) for i in range(len(coeffs)))
        
        return calculate_r_squared(self.points, model)

    def create_function(self, symbol: SymbolLike, canvas: Optional[Canvas] = None) -> Function[float, float]:
        a, b = self()
        canvas = canvas if canvas is not None else Canvas.recent
        sym = get_symbol(canvas, symbol)
        
        # Formula: a * (x ** b)
        expr = Traceable.wrap(a) * (sym ** b)
        return Function(sym, expr, canvas)

class RegressionMultiple:
    """
    Handles Multiple Linear Regression: y = b0 + b1*x1 + b2*x2 + ... + bn*xn
    Points format: [([x1, x2, ...], y), ...]
    """

    __slots__ = ("data_points", "num_vars")

    def __init__(self, data_points: List[Tuple[List[float], float]]) -> None:
        self.data_points = data_points
        self.num_vars = len(data_points[0][0]) if data_points else 0

    def __call__(self) -> List[float]:
        """Returns the coefficients [b0, b1, b2, ... bn]."""
        # 1. Build Design Matrix X (add a column of 1s for the intercept b0)
        X_rows = []
        Y_rows = []
        for inputs, output in self.data_points:
            X_rows.append([1.0] + list(inputs))
            Y_rows.append([output])

        X = Matrix(X_rows)
        Y = Matrix(Y_rows)
        XT = X.transpose()

        # 2. Solve Normal Equation: (XT * X) * B = (XT * Y)
        A = XT * X
        B_vec = XT * Y
        
        coeffs = A.solve(B_vec)
        return [row[0] for row in coeffs.data]
    
    def calculate(self) -> List[float]:
        return self()
    
    evaluate = calculate
    
    def r_squared(self) -> float:
        coeffs = self()
        def model(x):
            # Evaluate: a0 + a1*x + a2*x^2 ...
            return sum(coeffs[i] * (x ** i) for i in range(len(coeffs)))
        
        return calculate_r_squared(self.points, model)

    def create_function(self, symbols: List[Symbol], canvas: Optional[Canvas] = None) -> Function[float, float]:
        if len(symbols) != self.num_vars:
            raise ValueError(f"Expected {self.num_vars} symbols, got {len(symbols)}")
            
        coeffs = self()
        canvas = canvas if canvas is not None else Canvas.recent
        
        # Start with the intercept b0
        expr = Traceable.wrap(coeffs[0])
        
        # Add b1*x1 + b2*x2 + ...
        for i in range(self.num_vars):
            expr = expr + (Traceable.wrap(coeffs[i+1]) * symbols[i])
            
        # Note: Multiple regression returns a scalar, but depends on a list of symbols
        return Function(symbols, expr, canvas)

class Solver:
    """A class to solve for a variable in an expression given a target value."""

    @staticmethod
    def get_auto_range(expr: Traceable, symbol: Symbol, canvas: Optional[Canvas] = None) -> Tuple[float, float]:
        """Calculates a safe search range using Cauchy's Bound."""
        try:
            coeffs = expr.get_coefficients(symbol.name, canvas)
            if len(coeffs) < 2: return (-10, 10)
            
            an = abs(coeffs[-1]) # Leading coefficient
            max_ai = max(abs(c) for c in coeffs[:-1])
            
            # Cauchy's Bound: |x| < 1 + (max|ai| / |an|)
            radius = 1 + (max_ai / an)
            # Pad it slightly for safety
            return (-(radius + 1), radius + 1)
        except:
            # Fallback for non-polynomials (Trig, etc.)
            return (-50, 50)
    
    @staticmethod
    def solve(expr: Union[Expression, Function, Traceable, SymbolLike], 
              target: float, 
              symbol: Symbol, 
              guess: float = 1.0, 
              tol: float = 1e-7, 
              max_iter: int = 100,
              canvas: Optional[Canvas] = None) -> float:
        """Uses Newton's Method to find 'symbol' such that 'expr' == 'target'."""
        canvas = canvas if canvas is not None else Canvas.recent
    
        # 1. Resolve 'expr' to its underlying math
        if isinstance(expr, Symbol):
            # If the symbol holds a Function or Traceable, solve THAT.
            # Otherwise, we are trying to solve 'x = target', which is trivial.
            actual_val = expr.value
            if isinstance(actual_val, (Function, Expression, Traceable)):
                t_expr = Traceable.wrap(actual_val)
            else:
                # It's a raw variable symbol like 'x'
                t_expr = Traceable.wrap(expr)
        elif isinstance(expr, (Function, Expression)):
            t_expr = expr.callable
        else:
            t_expr = Traceable.wrap(expr)
            
        if not isinstance(t_expr, Traceable):
            raise ValueError("Expression must be Traceable to solve symbolically.")

        # g(x) = expr - target (we want g(x) = 0)
        shifted_expr = t_expr - target
        # g'(x)
        derivative = shifted_expr.diff(symbol.name)
        
        current_x = guess
        
        for _ in range(max_iter):
            symbol.value = current_x
            
            f_val = shifted_expr()
            df_val = derivative()

            # Recursively call if the result is still a Traceable (unlikely but safe)
            while hasattr(f_val, '__call__') and isinstance(f_val, Traceable):
                f_val = f_val()
            while hasattr(df_val, '__call__') and isinstance(df_val, Traceable):
                df_val = df_val()
            
            # Cast to float to ensure abs() works
            f_val, df_val = float(f_val), float(df_val)
            
            if abs(df_val) < 1e-12: 
                break
                
            next_x = current_x - (f_val / df_val)
            if abs(next_x - current_x) < tol:
                return next_x
            
            current_x = next_x
            
        return current_x
    
    @staticmethod
    def find_extrema(expr: Union[Traceable, Function, SymbolLike], 
                     symbol: Symbol, 
                     search_range: Optional[Tuple[float, float]] = None,
                     canvas: Optional[Canvas] = None) -> List[float]:
        
        t_expr = Traceable.wrap(expr)

        if search_range is None:
            search_range = Solver.get_auto_range(t_expr, symbol, canvas)

        deriv = t_expr.diff(symbol.name)
        
        # --- NEW: AUTO-COMPLEXITY ---
        deg = t_expr.get_degree(symbol.name)
        # We need at least (degree - 1) intervals to find all extrema, 
        # but multiplying by 5 gives us a safety buffer for narrow curves.
        intervals = max(10, deg * 5) 
        
        extrema = []
        start, end = search_range
        step = (end - start) / intervals
        
        for i in range(intervals):
            x_left = start + i * step
            x_right = x_left + step
            
            # Check for a sign change in the derivative (Bracketing)
            symbol.value = x_left
            val_l = deriv()
            symbol.value = x_right
            val_r = deriv()
            
            # Use float() to ensure we aren't comparing Traceables
            if float(val_l) * float(val_r) <= 0:
                guess = (x_left + x_right) / 2
                root = Solver.solve(deriv, target=0, symbol=symbol, guess=guess)
                
                if start - 1e-5 <= root <= end + 1e-5:
                    if not any(abs(root - e) < 1e-4 for e in extrema):
                        extrema.append(round(root, 6))
        
        return sorted(extrema)

    @staticmethod
    def solve_all(expr: Union[Traceable, Function, SymbolLike], 
                  target: float, 
                  symbol: Symbol, 
                  search_range: Optional[Tuple[float, float]] = None,
                  canvas: Optional[Canvas] = None) -> List[float]:
        """
        Partition the search range using extrema to find all real roots.
        """
        t_expr = Traceable.wrap(expr)

        if search_range is None:
            search_range = Solver.get_auto_range(t_expr, symbol, canvas)
        
        # 1. Find the "wiggles" (extrema)
        extrema = Solver.find_extrema(t_expr, symbol, search_range, canvas)
        
        # 2. Create partitions: [start, ext1, ext2, ..., end]
        partitions = [search_range[0]] + extrema + [search_range[1]]
        
        roots = []
        for i in range(len(partitions) - 1):
            x_left, x_right = partitions[i], partitions[i+1]
            
            # Check if the target is even reachable in this interval
            symbol.value = x_left
            y_left = t_expr() - target
            symbol.value = x_right
            y_right = t_expr() - target
            
            # Bracketing: If the function crosses the target value
            if float(y_left) * float(y_right) <= 0:
                # Use midpoint as the starting guess for Newton's Method
                guess = (x_left + x_right) / 2
                root = Solver.solve(t_expr, target, symbol, guess=guess, canvas=canvas)
                
                # Verify and add unique root
                if not any(abs(root - r) < 1e-4 for r in roots):
                    # Final check: Does it actually solve the equation?
                    symbol.value = root
                    if abs(float(t_expr()) - target) < 1e-5:
                        roots.append(round(root, 6))
        
        return sorted(roots)
    
    @staticmethod
    def solve_complex(expr: Union[Traceable, Function, SymbolLike], 
                      target: float, 
                      symbol: Symbol, 
                      guess: Union[float, complex] = 1+1j,
                      tol: float = 1e-10, 
                      max_iter: int = 100) -> complex:
        t_expr = Traceable.wrap(expr)
        shifted = t_expr - target
        deriv = shifted.diff(symbol.name)

        z = complex(guess)

        for _ in range(max_iter):
            symbol.value = z
            fz = shifted()
            dfz = deriv()

            if abs(dfz) < tol:
                break

            next_z = z - fz / dfz

            if abs(next_z - z) < tol:
                return next_z

            z = next_z

        return z

def fix_symbol_list(symbols: List[SymbolLike], canvas: Optional[Canvas] = None) -> List[Symbol]:
    """A helper function to convert a list of symbol-like objects into a list of Symbol objects."""

    canvas = canvas if canvas is not None else Canvas.recent
    fixed_symbols = []
    for sym in symbols:
        if isinstance(sym, Symbol):
            fixed_symbols.append(sym)
        else:
            fixed_symbols.append(get_symbol(canvas, sym))
    return fixed_symbols

class SystemSolver:
    """Solves systems of linear equations using the Matrix class."""

    @staticmethod
    def solve_linear(equations: List[Traceable], symbols: List[Symbol]) -> Dict[str, float]:
        """
        Solves a linear system. 
        Example: 
           2x + 3y = 8
           4x - y = 2
        """
        n = len(symbols)
        if len(equations) != n:
            raise ValueError("Number of equations must match number of symbols.")

        # Build Matrix A (coefficients) and Matrix B (constants)
        A_data = []
        B_data = []

        for eq in equations:
            row = []
            # To get the coefficient of a symbol in a linear eq:
            # The coefficient of 'x' is the derivative of the expression with respect to 'x'
            for sym in symbols:
                coeff = eq.diff(sym.name).calculate()
                row.append(float(coeff))
            
            A_data.append(row)
            
            # The constant term is -(eq evaluated at all symbols = 0)
            # Save original values
            originals = [s.value for s in symbols]
            for s in symbols: s.value = 0
            constant = -eq.calculate()
            B_data.append([float(constant)])
            
            # Restore values
            for i, s in enumerate(symbols): s.value = originals[i]

        A = Matrix(A_data)
        B = Matrix(B_data)
        solution = A.solve(B)

        return {symbols[i].name: solution.data[i][0] for i in range(n)}
    
    @staticmethod
    def solve_nonlinear(equations: List[Traceable], symbols: List[Symbol], 
                        guesses: List[float], max_iter: int = 50, tol: float = 1e-7) -> Dict[str, float]:
        """Solves F(x) = 0 using the Multi-variable Newton Method."""
        n = len(symbols)
        current_vals = list(guesses)

        for _ in range(max_iter):
            # Set current values in canvas
            for i, s in enumerate(symbols): s.value = current_vals[i]

            # 1. Calculate Function Matrix F
            f_vec = Matrix([[eq.calculate()] for eq in equations])
            
            # 2. Calculate Jacobian Matrix J
            j_data = []
            for eq in equations:
                row = [eq.diff(s.name).calculate() for s in symbols]
                j_data.append(row)
            J = Matrix(j_data)

            # 3. Solve J * delta = -F
            minus_F = f_vec * -1.0
            delta = J.solve(minus_F)

            # 4. Update
            new_vals = [current_vals[i] + delta.data[i][0] for i in range(n)]
            
            # Check convergence
            if sum(abs(d[0]) for d in delta.data) < tol:
                return {symbols[i].name: new_vals[i] for i in range(n)}
            
            current_vals = new_vals

        return {symbols[i].name: current_vals[i] for i in range(n)}

class Equation:
    __slots__ = ("left", "right")

    def __init__(self, left: Any, right: Any) -> None:
        self.left = Traceable.wrap(left)
        self.right = Traceable.wrap(right)

    @staticmethod
    def parse(expr: Union[str, 'Equation'], canvas: Optional[Canvas] = None) -> 'Equation':
        if isinstance(expr, Equation):
            return expr
        if not isinstance(expr, str):
            raise ValueError("Expression must be a string.")
        if not "=" in expr:
            raise ValueError("Expression must contain an '=' sign to be parsed as an equation.")
        return parse(expr, canvas)

    def to_zero(self) -> Traceable:
        return self.left - self.right

    def solve(self, symbol: Symbol, guess: float = 1.0) -> float:
        return Solver.solve(self.to_zero(), 0, symbol, guess)

    def solve_all(self, symbol: Symbol) -> List[float]:
        return Solver.solve_all(self.to_zero(), 0, symbol)
    
    def are_equal(self) -> bool:
        """Checks if the left and right sides of the equation are equal. This is a simple check and may not be reliable for complex expressions due to floating-point precision issues, but it can be useful for quick validations."""
        return float(self.left()) == float(self.right())
    
    def difference(self) -> float:
        """Returns the absolute difference between the left and right sides of the equation. Useful for checking how close we are to equality when solving."""
        return abs(float(self.left()) - float(self.right()))

def _string_to_traceable(expr: str, canvas: Optional[Canvas] = None) -> Traceable:
    """
    Converts a string expression into a Traceable object by evaluating 
    it within a context of known math functions and canvas symbols.
    """

    if canvas is None:
        raise RuntimeError("Due to the complexity of the internal method '_string_to_traceable' and its reliance on the canvas context, you must provide a canvas instance when calling this function. This is to ensure that all symbols and functions are correctly resolved within the canvas environment.")
    
    # 1. Define the supported mathematical functions mapping to Traceable classmethods
    operators = {
        'sin': Traceable.sin,
        'cos': Traceable.cos,
        'tan': Traceable.tan,
        'ln': Traceable.log,
        'log': Traceable.log,
        'exp': Traceable.exp,
        'sqrt': Traceable.sqrt,
        'abs': Traceable.abs,
        'conj': Traceable.conjugate,
    }

    # 2. Map all symbols currently in the canvas to their names
    # This allows the evaluator to see 'x' and treat it as a Traceable(x)
    context = {**operators}
    for symbol in canvas.symbols:
        context[symbol.name] = Traceable.wrap(symbol)

    # 3. Handle potential syntax differences (like ^ for power)
    clean_expr = expr.replace('^', '**')

    try:
        # Use eval with restricted globals/locals for safety and functionality
        result = eval(clean_expr, {"__builtins__": {}}, context)
        return Traceable.wrap(result)
    except NameError as e:
        raise ValueError(f"Unknown symbol or function in expression: {e}")
    except SyntaxError as e:
        raise ValueError(f"Invalid mathematical syntax: {e}")

def parse(expr: Union[str, Traceable, Symbol, Expression, Equation, Any], canvas: Optional[Canvas] = None) -> Union[Traceable, Equation]:
    """A simple parser to convert a string like '2*x + 3 = 8' into an equation or traceable."""

    canvas = canvas if canvas is not None else Canvas.recent

    if isinstance(expr, Traceable):
        return expr
    
    if isinstance(expr, Equation):
        return expr
    
    if not isinstance(expr, str):
        return Traceable.wrap(expr)

    if '=' in expr:
        left_str, *_, right_str = expr.split('=')
        left_expr = _string_to_traceable(left_str.strip(), canvas)
        right_expr = _string_to_traceable(right_str.strip(), canvas)
        return Equation(left_expr, right_expr)
    else:
        return _string_to_traceable(expr.strip(), canvas)
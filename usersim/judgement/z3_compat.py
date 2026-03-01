"""
Z3 compatibility shim.

On platforms where z3-solver is available (x86_64, most CI), imports the real
z3 library.  On ARM64 (Apple Silicon, Raspberry Pi) z3-solver is not packaged
for all Python versions; this shim provides a minimal pure-Python fallback that
handles the Boolean / numeric constraint patterns usersim uses.

The shim is NOT a general-purpose SMT solver.  It supports:
  - Bool / BoolVal
  - Int / RealVal
  - And / Or / Not / Implies
  - ArithRef comparisons (==, !=, <, <=, >, >=)
  - Solver.add / Solver.check / Solver.model
  - sat / unsat constants
"""

import sys

try:
    import z3 as _z3
    # Verify it actually works (z3-solver on ARM may import but fail at runtime)
    _z3.BoolVal(True)
    from z3 import (
        Bool, BoolVal, Int, IntVal, Real, RealVal,
        And, Or, Not, If,
        Solver, sat, unsat,
    )
    import z3 as _z3_mod

    def Implies(a, b):
        """Wrap z3.Implies and attach a human-readable _repr and antecedent."""
        expr = _z3_mod.Implies(a, b)
        expr._repr = f"If {a}, then {b}"
        expr._antecedent = a
        return expr

    def named(label: str, expr):
        """Attach a human-readable name to any Z3 expression."""
        expr._repr = label
        return expr

    Z3_REAL = True

except Exception:
    Z3_REAL = False

    # ── Pure-Python fallback ──────────────────────────────────────────────────

    class _Expr:
        """Minimal expression node — evaluates against a concrete assignment."""
        def __init__(self, fn, repr_str="<expr>"):
            self._fn  = fn
            self._repr = repr_str
        def __call__(self, env):       return self._fn(env)
        def __repr__(self):            return self._repr
        # Comparison operators produce new _Expr nodes
        def __eq__(self, other):       return _binop(self, other, lambda a,b: a==b, "==")
        def __ne__(self, other):       return _binop(self, other, lambda a,b: a!=b, "!=")
        def __lt__(self, other):       return _binop(self, other, lambda a,b: a<b,  "<")
        def __le__(self, other):       return _binop(self, other, lambda a,b: a<=b, "≤")
        def __gt__(self, other):       return _binop(self, other, lambda a,b: a>b,  ">")
        def __ge__(self, other):       return _binop(self, other, lambda a,b: a>=b, "≥")
        # Logical operators
        def __and__(self, other):      return And(self, other)
        def __or__(self, other):       return Or(self, other)
        def __invert__(self):          return Not(self)
        # Arithmetic
        def __add__(self, other):      return _binop(self, other, lambda a,b: a+b, "+")
        def __sub__(self, other):      return _binop(self, other, lambda a,b: a-b, "-")
        def __mul__(self, other):      return _binop(self, other, lambda a,b: a*b, "*")
        def __truediv__(self, other):  return _binop(self, other, lambda a,b: a/b, "/")
        __hash__ = object.__hash__

    def _lit(v):
        return v if isinstance(v, _Expr) else _Expr(lambda env, _v=v: _v, repr(v))

    def _binop(a, b, op, sym):
        a, b = _lit(a), _lit(b)
        return _Expr(lambda env, _a=a, _b=b, _op=op: _op(_a(env), _b(env)), f"({a} {sym} {b})")

    def Bool(name):
        return _Expr(lambda env, _n=name: env.get(_n, False), name)

    def BoolVal(v):
        return _Expr(lambda env, _v=bool(v): _v, str(v))

    def Int(name):
        return _Expr(lambda env, _n=name: env.get(_n, 0), name)

    def IntVal(v):
        return _Expr(lambda env, _v=int(v): _v, str(v))

    def Real(name):
        return _Expr(lambda env, _n=name: env.get(_n, 0.0), name)

    def RealVal(v):
        return _Expr(lambda env, _v=float(v): _v, str(v))

    def And(*args):
        args = [_lit(a) for a in (args[0] if len(args)==1 and hasattr(args[0],'__iter__') and not isinstance(args[0],_Expr) else args)]
        return _Expr(lambda env, _a=args: all(bool(a(env)) for a in _a), f"And({', '.join(repr(a) for a in args)})")

    def Or(*args):
        args = [_lit(a) for a in (args[0] if len(args)==1 and hasattr(args[0],'__iter__') and not isinstance(args[0],_Expr) else args)]
        return _Expr(lambda env, _a=args: any(bool(a(env)) for a in _a), f"Or({', '.join(repr(a) for a in args)})")

    def Not(a):
        a = _lit(a)
        return _Expr(lambda env, _a=a: not bool(_a(env)), f"Not({a})")

    def Implies(a, b):
        a, b = _lit(a), _lit(b)
        expr = _Expr(lambda env, _a=a, _b=b: (not bool(_a(env))) or bool(_b(env)),
                     f"If {a}, then {b}")
        expr._antecedent = a
        return expr

    def named(label: str, expr):
        """Attach a human-readable name to any expression."""
        expr._repr = label
        return expr

    def If(cond, then, else_):
        cond, then, else_ = _lit(cond), _lit(then), _lit(else_)
        return _Expr(lambda env, _c=cond, _t=then, _e=else_: _t(env) if bool(_c(env)) else _e(env))

    class _SolveResult:
        def __init__(self, ok):  self._ok = ok
        def __eq__(self, other): return self._ok == (other is sat)

    sat   = _SolveResult(True)
    unsat = _SolveResult(False)

    class _Model:
        def __init__(self, env): self._env = env
        def __getitem__(self, expr):
            if hasattr(expr, '_fn'): return bool(expr(self._env))
            return self._env.get(str(expr))

    class Solver:
        def __init__(self):   self._constraints = []
        def add(self, *args): self._constraints.extend(args)
        def check(self):
            # Evaluate with empty env (all facts already embedded in expressions)
            env = {}
            self._ok = all(bool(c(env)) if callable(c) else bool(c) for c in self._constraints)
            return sat if self._ok else unsat
        def model(self):
            return _Model({})
        def __repr__(self):
            return f"Solver(constraints={len(self._constraints)}, ok={getattr(self,'_ok',None)})"

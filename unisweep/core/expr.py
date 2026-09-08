"""Safe, tolerant expression compiler.

Replaces the old ``str.replace`` + ``eval`` condition machinery. User text is
parsed with :mod:`ast`, every node is validated against a whitelist, equality
comparisons are rewritten to *tolerant* comparisons (``a == b`` becomes
``abs(a - b) <= tol``), and the result is compiled once and evaluated many
times with an explicit namespace (no builtins, no module globals).

Because the math functions come from numpy, a compiled expression evaluates
transparently on scalars *and* on arrays — the GUI uses that to render the
condition-region preview over the whole sweep grid in one shot.

Fixes over the legacy evaluator:
* variable substitution can no longer mangle other tokens
  ('Slave' inside 'SlaveSlave', 'x' inside 'exp' / 'max');
* chained comparisons (``0 < x < 1``) work natively instead of being
  silently truncated;
* float equality has a real tolerance instead of ``abs(a-b) <= 0``;
* a malformed expression raises :class:`ExprError` at *compile* time with a
  readable message, instead of NameError'ing mid-sweep.
"""

from __future__ import annotations

import ast
import math
import numpy as np

__all__ = ["ExprError", "SafeExpr", "AXIS_ALIASES", "split_lines",
           "apply_transform"]

# Names the user may call as functions.
_FUNCTIONS = {
    "sin": np.sin, "cos": np.cos, "tan": np.tan,
    "asin": np.arcsin, "acos": np.arccos, "atan": np.arctan,
    "sinh": np.sinh, "cosh": np.cosh, "tanh": np.tanh,
    "exp": np.exp, "log": np.log, "log10": np.log10, "log2": np.log2,
    "sqrt": np.sqrt, "abs": np.abs, "sign": np.sign,
    "floor": np.floor, "ceil": np.ceil, "round": np.round,
    "min": np.minimum, "max": np.maximum,
}

# Names the user may reference as constants.
_CONSTANTS = {"pi": math.pi, "e": math.e, "inf": math.inf, "nan": math.nan}

# Canonical axis-variable aliases, index -> accepted spellings.
# axis 1 = master (outermost), axis 2 = slave, axis 3 = slave-slave (innermost).
AXIS_ALIASES = {
    1: ("x", "X", "Master", "master"),
    2: ("y", "Y", "Slave", "slave"),
    3: ("z", "Z", "SlaveSlave", "slaveslave", "Slaveslave"),
}

_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
                   ast.Mod, ast.Pow)
_ALLOWED_UNARY = (ast.UAdd, ast.USub, ast.Not)
_ALLOWED_CMP = (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)


class ExprError(ValueError):
    """Raised when a user expression cannot be compiled safely."""


def split_lines(text: str) -> list[str]:
    """Split multi-line condition text into non-empty stripped lines."""
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def apply_transform(expr_text: str, values):
    """Apply a user axis/colour transform to an array of values.

    Shared by the live plot windows and by the saved-image renderer, so a
    restyled PNG shows the same numbers the window on screen does — the
    whole point of "apply these settings to the saved files".

    A transform that will not compile or evaluate leaves the values
    untouched: a half-typed expression in a settings box must not blank a
    plot, and must certainly not blank a saved file.
    """
    text = (expr_text or "").strip()
    values = np.asarray(values)
    if not text or values.size == 0:
        return values
    try:
        expr = SafeExpr(text, {"v": "v", "x": "v"})
        return np.asarray(expr({"v": values}), dtype=float)
    except Exception:                              # noqa: BLE001
        return values


def _tol_eq(a, b, _tol):
    return np.abs(a - b) <= _tol


def _tol_ne(a, b, _tol):
    return np.abs(a - b) > _tol


class _Rewriter(ast.NodeTransformer):
    """Decompose chained comparisons and make (in)equality tolerant."""

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        parts: list[ast.expr] = []
        left = node.left
        for op, right in zip(node.ops, node.comparators):
            if isinstance(op, (ast.Eq, ast.NotEq)):
                fname = "_tol_eq" if isinstance(op, ast.Eq) else "_tol_ne"
                part: ast.expr = ast.Call(
                    func=ast.Name(id=fname, ctx=ast.Load()),
                    args=[left, right, ast.Name(id="_tol", ctx=ast.Load())],
                    keywords=[],
                )
            else:
                part = ast.Compare(left=left, ops=[op], comparators=[right])
            parts.append(part)
            left = right
        if len(parts) == 1:
            return ast.copy_location(parts[0], node)
        return ast.copy_location(ast.BoolOp(op=ast.And(), values=parts), node)


class _Validator(ast.NodeVisitor):
    def __init__(self, variables: set[str]):
        self.variables = variables
        self.names_used: set[str] = set()

    def visit(self, node):  # noqa: D102 - dispatch with whitelist
        ok = (
            ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.BinOp,
            ast.UnaryOp, ast.Compare, ast.Call, ast.Name, ast.Load,
            ast.Constant, ast.keyword,
        ) + _ALLOWED_BINOPS + _ALLOWED_UNARY + _ALLOWED_CMP
        if not isinstance(node, ok):
            raise ExprError(
                f"'{type(node).__name__}' is not allowed in expressions")
        return super().visit(node)

    def visit_Constant(self, node: ast.Constant):
        if not isinstance(node.value, (int, float, bool)):
            raise ExprError(f"literal {node.value!r} is not allowed")

    def visit_Call(self, node: ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ExprError("only plain function calls are allowed")
        if node.func.id not in _FUNCTIONS and node.func.id not in (
                "_tol_eq", "_tol_ne"):
            raise ExprError(f"unknown function '{node.func.id}'")
        if node.keywords:
            raise ExprError("keyword arguments are not allowed")
        for a in node.args:
            self.visit(a)

    def visit_Name(self, node: ast.Name):
        name = node.id
        if name in ("_tol_eq", "_tol_ne", "_tol"):
            return
        if name in _FUNCTIONS or name in _CONSTANTS:
            self.names_used.add(name)
            return
        if name not in self.variables:
            allowed = ", ".join(sorted(self.variables))
            raise ExprError(
                f"unknown name '{name}' (allowed variables: {allowed})")
        self.names_used.add(name)


class SafeExpr:
    """A compiled, safely-evaluable expression.

    Parameters
    ----------
    source:
        The user text, e.g. ``"x**2 + y**2 <= 1"``.
    variables:
        Mapping of accepted variable name -> canonical name. Values with the
        same canonical name are treated as the same quantity (aliases).
    """

    def __init__(self, source: str, variables: dict[str, str]):
        self.source = source.strip()
        self.variables = dict(variables)
        if not self.source:
            raise ExprError("empty expression")
        try:
            tree = ast.parse(self.source, mode="eval")
        except SyntaxError as exc:
            raise ExprError(f"syntax error: {exc.msg}") from None
        tree = _Rewriter().visit(tree)
        ast.fix_missing_locations(tree)
        validator = _Validator(set(self.variables))
        validator.visit(tree)
        self.names_used = validator.names_used & set(self.variables)
        self.canonical_used = {self.variables[n] for n in self.names_used}
        self._code = compile(tree, "<unisweep-expr>", "eval")

    def __call__(self, values: dict[str, float], tol: float = 0.0):
        """Evaluate with canonical-name ``values`` and equality tolerance."""
        ns = {"__builtins__": {}}
        ns.update(_FUNCTIONS)
        ns.update(_CONSTANTS)
        ns.update({"_tol_eq": _tol_eq, "_tol_ne": _tol_ne, "_tol": tol})
        for alias, canonical in self.variables.items():
            if canonical in values:
                ns[alias] = values[canonical]
        try:
            return eval(self._code, ns)  # noqa: S307 - AST-validated code
        except Exception as exc:  # pragma: no cover - defensive
            raise ExprError(f"error evaluating '{self.source}': {exc}") from exc

    def __repr__(self) -> str:  # pragma: no cover
        return f"SafeExpr({self.source!r})"

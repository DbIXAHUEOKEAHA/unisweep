"""User sweep conditions.

Two legacy features live here, both rebuilt on :class:`SafeExpr`:

1. **Region masking** — inequality lines such as ``x**2 + y**2 <= 1`` restrict
   which grid points are actually measured. The predicate is evaluated *per
   point at measure time* against the live axis values, so it keeps working
   when the trajectory is edited mid-sweep (no precomputed grid, no
   ``isinarea`` tolerance matching, no race with the engine thread —
   the causes of "the condition works only sometimes").

2. **Coupled equality (curve following)** — a single ``==`` line relating two
   axes (e.g. ``y == 2*x + 1``) removes the solved axis's own loop and
   computes it from the driven axis at every step by root finding. This
   reproduces the legacy 'xy' / 'yz' / 'yx' condition_status modes, detected
   structurally from the parsed expression instead of by substring checks.

Equality inside region lines is tolerant: ``a == b`` means
``|a - b| <= tol`` where ``tol`` is half the local step of the axes involved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from scipy import optimize

from .expr import AXIS_ALIASES, ExprError, SafeExpr, split_lines

__all__ = ["ConditionError", "CoupledEquality", "ConditionSet"]


class ConditionError(ValueError):
    pass


def _alias_map(dimensions: int) -> dict[str, str]:
    """alias -> canonical axis name ('ax1', 'ax2', 'ax3')."""
    m: dict[str, str] = {}
    for axis in range(1, dimensions + 1):
        for alias in AXIS_ALIASES[axis]:
            m[alias] = f"ax{axis}"
    return m


@dataclass
class CoupledEquality:
    """axes are 1-based; ``solved`` is computed from the others per step."""
    expr: SafeExpr            # boolean form (tolerant ==) — kept for reports
    residual: SafeExpr        # f(...) == 0 residual form for root finding
    solved: int               # axis index computed by the solver
    driven: tuple[int, ...]   # axes appearing on the other side
    last_solution: Optional[float] = None

    def solve(self, values: dict[str, float], guess: float) -> float:
        """Root-find the solved axis value given the driven axes' values."""
        canonical = f"ax{self.solved}"

        def f(v: float) -> float:
            vals = dict(values)
            vals[canonical] = v
            return float(self.residual(vals))

        x0 = self.last_solution if self.last_solution is not None else guess
        try:
            sol = optimize.newton(f, x0=x0, maxiter=200)
        except (RuntimeError, OverflowError) as exc:
            raise ConditionError(
                f"could not solve '{self.expr.source}' for axis "
                f"{self.solved} near {x0:g}: {exc}") from None
        self.last_solution = float(sol)
        return float(sol)


class ConditionSet:
    """Parsed multi-line condition text for an N-dimensional sweep."""

    def __init__(self, text: str, dimensions: int):
        self.text = text or ""
        self.dimensions = dimensions
        self.region: list[SafeExpr] = []
        self.coupled: Optional[CoupledEquality] = None

        aliases = _alias_map(dimensions)
        for line in split_lines(self.text):
            expr = SafeExpr(line, aliases)
            axes = sorted(int(c[2:]) for c in expr.canonical_used)
            if self._is_pure_equality(line) and len(axes) == 2 \
                    and dimensions >= 2 and self.coupled is None:
                lhs, rhs = self._split_equality(line)
                residual = SafeExpr(f"({lhs}) - ({rhs})", aliases)
                # Legacy convention: the *lower* axis index is solved from the
                # higher one ('xy' -> x from y, 'yz' -> y from z, 'yx' -> x).
                solved, driven = axes[0], tuple(a for a in axes if a != axes[0])
                self.coupled = CoupledEquality(expr, residual, solved, driven)
            else:
                self.region.append(expr)

        if dimensions < 2:
            # 1-D sweeps never masked points in the legacy engine
            self.region = []
            self.coupled = None

    # -----------------------------------------------------------------
    @staticmethod
    def _is_pure_equality(line: str) -> bool:
        stripped = line.replace("==", "\x00")
        if any(op in stripped for op in ("<", ">", "!=")):
            return False
        return "\x00" in stripped or \
            ("=" in stripped and "==" not in line and "!=" not in line)

    @staticmethod
    def _split_equality(line: str) -> tuple[str, str]:
        sep = "==" if "==" in line else "="
        lhs, rhs = line.split(sep, 1)
        return lhs.strip(), rhs.strip()

    # -----------------------------------------------------------------
    @property
    def has_region(self) -> bool:
        return bool(self.region)

    def allows(self, values: dict[str, float],
               tolerances: dict[str, float]) -> bool:
        """True if the point passes every region line.

        ``values`` / ``tolerances`` use canonical names ('ax1', ...).
        The equality tolerance for a line is half the smallest local step of
        the axes it references.
        """
        for expr in self.region:
            axes = expr.canonical_used or set(values)
            tol = min(tolerances.get(c, 0.0) for c in axes) / 2.0 \
                if axes else 0.0
            try:
                if not bool(expr(values, tol=tol)):
                    return False
            except ExprError:
                return False
        return True

    def preview_mask(self, ax1_grid, ax2_grid,
                     tol1: float, tol2: float) -> np.ndarray:
        """Vectorised region mask over a 2-D grid (GUI preview)."""
        X, Y = np.meshgrid(np.asarray(ax1_grid), np.asarray(ax2_grid))
        mask = np.ones_like(X, dtype=bool)
        tol = min(tol1, tol2) / 2.0
        for expr in self.region:
            mask &= np.asarray(
                expr({"ax1": X, "ax2": Y}, tol=tol), dtype=bool)
        return mask

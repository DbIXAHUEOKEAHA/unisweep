"""The assignment: what a session is for, and when it is finished.

The rest of the agent surface answers *what is the rig* and *what did I
just measure*. Nothing answered *what am I here to find out*, so an
assistant's idea of "done" was its own opinion of its own work — and an
opinion is exactly what a confident wrong answer also looks like.

An assignment is a markdown file the supervisor writes in their own
words, with one machine-checkable part: the acceptance criteria. A
criterion is an expression over **facts**, and the facts that can be
taken from the journal are taken from the journal — which runs a finding
cites, what they swept, how far, how many points they took — never from
what the finding says about itself. Only quantities nobody but the
assistant can produce (a fitted value, an uncertainty) come from the
assistant, and a reported fact can never overwrite a measured one. That
asymmetry is the whole point of the module; :func:`merge_facts` is where
it lives and ``tests/test_assignment.py`` pins it.

The file lives at ``<core_dir>/assignments/<name>.md``::

    # Hall density at base temperature

    ## Question
    What is the carrier density at Vbg = -40 V, and how sure are you?

    ## Sample
    Monolayer graphene on 300 nm SiO2, back gate only. Cold.

    ## Constraints
    - Do not exceed the gate limit you measure.

    ## Acceptance
    - field_span >= 1.8           - the Hall slope needs at least +-0.9 T
    - points >= 150
    - density_uncertainty <= 0.05

    ## Deliverables
    - The density, with an uncertainty.

Sections are optional and their order does not matter. Anything under a
heading this module does not recognise is kept verbatim under ``extra``,
so a supervisor can write whatever else they like without it being lost —
the assistant is shown all of it.
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Optional, Sequence

from ..core.expr import ExprError, SafeExpr
from ..core.labprofile import channel_ident

__all__ = ["Assignment", "Criterion", "AssignmentError", "assignments_dir",
           "list_assignments", "load_assignment", "facts_from_runs",
           "facts_from_programs", "merge_facts"]

ASSIGNMENT_DIRNAME = "assignments"

#: How a criterion line separates its expression from its explanation.
#: A minus sign is arithmetic, so it cannot be one of these.
_WHY_SPLIT = re.compile(r"\s+(?:—|–|#|::)\s+")

_KNOWN_SECTIONS = ("question", "sample", "constraints", "acceptance",
                   "deliverables", "notes")
_LIST_SECTIONS = ("constraints", "deliverables")


class AssignmentError(ValueError):
    """A malformed or missing assignment file."""


def assignments_dir(core_dir: str) -> str:
    return os.path.join(core_dir, ASSIGNMENT_DIRNAME)


def list_assignments(core_dir: str) -> list[dict]:
    """Every assignment on disk, with its title — enough to choose one."""
    folder = assignments_dir(core_dir)
    out: list[dict] = []
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return out
    for filename in names:
        if not filename.lower().endswith(".md"):
            continue
        name = filename[:-3]
        try:
            assignment = load_assignment(core_dir, name)
        except AssignmentError:
            out.append({"name": name, "title": "", "error": "unreadable"})
            continue
        out.append({"name": name, "title": assignment.title,
                    "criteria": len(assignment.criteria)})
    return out


# ---------------------------------------------------------------------------
# criteria
# ---------------------------------------------------------------------------
def _names_in(source: str) -> set[str]:
    """Free variable names, excluding anything being called."""
    tree = ast.parse(source, mode="eval")
    called = {n.func.id for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    return {n.id for n in ast.walk(tree)
            if isinstance(n, ast.Name)} - called


@dataclass(frozen=True)
class Criterion:
    """One acceptance test: an expression, and why it is there.

    A criterion that will not compile is kept rather than dropped, with
    its error. A supervisor mistyping one should see a complaint on the
    criterion, not silently lose the requirement it stood for.
    """

    test: str
    why: str = ""
    expr: Optional[SafeExpr] = None
    error: str = ""
    wants: tuple[str, ...] = ()

    @classmethod
    def parse(cls, line: str) -> "Criterion":
        parts = _WHY_SPLIT.split(str(line).strip(), maxsplit=1)
        return cls._build(parts[0].strip(),
                          parts[1].strip() if len(parts) > 1 else "")

    @classmethod
    def _build(cls, test: str, why: str) -> "Criterion":
        try:
            wants = tuple(sorted(_names_in(test)))
            expr = SafeExpr(test, {n: n for n in wants})
        except (SyntaxError, ExprError, ValueError) as exc:
            return cls(test=test, why=why, error=f"{exc}")
        return cls(test=test, why=why, expr=expr, wants=wants)

    def check(self, facts: dict) -> dict:
        """Evaluate against the facts. Never raises; a criterion that
        cannot be evaluated has not been met."""
        out = {"test": self.test, "why": self.why, "met": False, "using": {}}
        if self.expr is None:
            out["reason"] = f"this criterion does not compile: {self.error}"
            return out
        missing = [n for n in self.wants if n not in facts]
        if missing:
            out["reason"] = (
                "nothing establishes " + ", ".join(missing)
                + " — cite a run that measures it, or report it as evidence")
            out["missing"] = missing
            return out
        values = {n: facts[n] for n in self.wants}
        out["using"] = values
        try:
            out["met"] = bool(self.expr(values))
        except Exception as exc:                   # noqa: BLE001
            out["reason"] = f"could not be evaluated: {exc}"
            return out
        if not out["met"]:
            out["reason"] = "not met by the evidence"
        return out


# ---------------------------------------------------------------------------
# the assignment itself
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Assignment:
    name: str
    title: str = ""
    question: str = ""
    sample: str = ""
    constraints: tuple[str, ...] = ()
    criteria: tuple[Criterion, ...] = ()
    deliverables: tuple[str, ...] = ()
    notes: str = ""
    extra: tuple[tuple[str, str], ...] = ()
    path: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "question": self.question,
            "sample": self.sample,
            "constraints": list(self.constraints),
            "deliverables": list(self.deliverables),
            "notes": self.notes,
            "extra": {k: v for k, v in self.extra},
            "path": self.path,
            "acceptance": [
                {"test": c.test, "why": c.why, "needs": list(c.wants),
                 **({"error": c.error} if c.error else {})}
                for c in self.criteria],
            "how_acceptance_works": (
                "Criteria are checked by report_finding against facts taken "
                "from the runs you cite — points, the span of each swept "
                "parameter, which channels were read. Anything they cannot "
                "supply you pass as evidence, and a value you report never "
                "overrides one measured from the journal."),
        }

    def check(self, facts: dict) -> list[dict]:
        return [c.check(facts) for c in self.criteria]


def _split_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    title = ""
    sections: list[tuple[str, str]] = []
    heading, body = "", []
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            if heading or body:
                sections.append((heading, "\n".join(body).strip()))
            heading, body = line[3:].strip(), []
        elif line.startswith("# ") and not heading and not title:
            title = line[2:].strip()
        else:
            body.append(line)
    if heading or body:
        sections.append((heading, "\n".join(body).strip()))
    return title, sections


def _bullets(body: str) -> tuple[str, ...]:
    out = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            out.append(stripped[2:].strip())
        elif stripped:
            out.append(stripped)
    return tuple(o for o in out if o)


def parse_assignment(text: str, name: str = "", path: str = "") -> Assignment:
    title, sections = _split_sections(text)
    fields: dict[str, Any] = {}
    extra: list[tuple[str, str]] = []
    for heading, body in sections:
        key = heading.strip().lower()
        if not heading:
            continue
        if key in _KNOWN_SECTIONS:
            fields[key] = body
        else:
            extra.append((heading.strip(), body))

    criteria = [Criterion.parse(line)
                for line in _bullets(fields.get("acceptance", ""))
                if line.strip()]

    return Assignment(
        name=name,
        title=title or name,
        question=fields.get("question", ""),
        sample=fields.get("sample", ""),
        constraints=_bullets(fields.get("constraints", "")),
        criteria=tuple(criteria),
        deliverables=_bullets(fields.get("deliverables", "")),
        notes=fields.get("notes", ""),
        extra=tuple(extra),
        path=path,
    )


def load_assignment(core_dir: str, name: str) -> Assignment:
    safe = os.path.basename(str(name or "").strip())
    if not safe:
        raise AssignmentError("no assignment named")
    if not safe.lower().endswith(".md"):
        safe += ".md"
    path = os.path.join(assignments_dir(core_dir), safe)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        available = [a["name"] for a in list_assignments(core_dir)]
        raise AssignmentError(
            f"cannot read {path} ({exc.strerror or exc}). "
            + (f"Available: {', '.join(available)}" if available else
               f"There are no assignments in "
               f"{assignments_dir(core_dir)} yet")) from None
    return parse_assignment(text, name=safe[:-3], path=path)


# ---------------------------------------------------------------------------
# facts
# ---------------------------------------------------------------------------
def _ident(text: str) -> str:
    out = re.sub(r"[^0-9a-zA-Z]+", "_", str(text)).strip("_").lower()
    return out or "x"


def _seconds(started: str, finished: str) -> float:
    try:
        a = datetime.fromisoformat(str(started))
        b = datetime.fromisoformat(str(finished))
    except (TypeError, ValueError):
        return 0.0
    return max((b - a).total_seconds(), 0.0)


def _axis_facts(axes: Iterable[dict], spans: dict) -> None:
    for axis in axes or ():
        name = _ident(axis.get("parameter") or "")
        try:
            lo = float(axis.get("start"))
            hi = float(axis.get("stop"))
        except (TypeError, ValueError):
            continue
        lo, hi = min(lo, hi), max(lo, hi)
        previous = spans.get(name)
        spans[name] = ((min(previous[0], lo), max(previous[1], hi))
                       if previous else (lo, hi))


def _finish(facts: dict, spans: dict) -> dict:
    for name, (lo, hi) in spans.items():
        facts[f"{name}_min"] = lo
        facts[f"{name}_max"] = hi
        facts[f"{name}_span"] = hi - lo
    return facts


def facts_from_runs(runs: Sequence[dict]) -> dict:
    """What the journal says about the runs a finding cites.

    These are measured, not claimed: they come from the program each run
    actually executed and the count of points it actually took.
    """
    facts: dict[str, float] = {"runs": float(len(runs)), "points": 0.0,
                               "stopped": 0.0, "duration_s": 0.0}
    spans: dict[str, tuple[float, float]] = {}
    for run in runs:
        facts["points"] += float(run.get("points") or 0)
        if run.get("stopped"):
            facts["stopped"] = 1.0
        facts["duration_s"] += _seconds(run.get("started_at", ""),
                                        run.get("finished_at", ""))
        program = run.get("program") or {}
        _axis_facts(program.get("axes") or (), spans)
        for read in program.get("reads") or ():
            facts[f"read_{channel_ident(str(read))}"] = 1.0
    return _finish(facts, spans)


def facts_from_programs(priced: Sequence[dict]) -> dict:
    """The same facts, predicted from a plan that has not run yet.

    Lets a plan be measured against the acceptance criteria *before*
    anything moves — which is the only cheap moment to discover that it
    was never going to answer the question.
    """
    facts: dict[str, float] = {"runs": float(len(priced)), "points": 0.0,
                               "stopped": 0.0, "duration_s": 0.0}
    spans: dict[str, tuple[float, float]] = {}
    for step in priced:
        program = step.get("program") or {}
        facts["points"] += float(step.get("planned_points") or 0)
        facts["duration_s"] += float(step.get("estimated_seconds") or 0)
        _axis_facts(program.get("axes") or (), spans)
        for read in program.get("reads") or ():
            facts[f"read_{channel_ident(str(read))}"] = 1.0
    return _finish(facts, spans)


def merge_facts(measured: dict, reported: Optional[dict]) -> tuple[dict, list]:
    """Measured facts win, always.

    An assistant may supply what the journal cannot know — a fitted
    value, an uncertainty. It may not supply what the journal *does*
    know, because then a criterion about how far the field was swept
    would be checked against the claim rather than the sweep, and the
    assignment would be back to grading itself.
    """
    facts = dict(measured)
    refused: list[dict] = []
    for key, value in (reported or {}).items():
        try:
            number = float(value)
        except (TypeError, ValueError):
            refused.append({"name": key, "reason": "not a number"})
            continue
        if key in measured:
            refused.append({"name": key, "reason": "measured from the runs "
                                                   "you cited; not overridable",
                            "measured": measured[key], "reported": number})
            continue
        facts[key] = number
    return facts, refused

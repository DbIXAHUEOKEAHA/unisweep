"""The sweep engine.

One generic N-dimensional engine replaces the legacy ``Sweeper1d`` /
``Sweeper2d`` / ``Sweeper3d`` loop pyramids and the ``Sweeper_write`` thread.

Key properties
--------------
* **Live-editable** — all instructions are re-read from the shared
  :class:`LiveProgram` at every step boundary (see ``runner.py``), so the GUI
  can retune ranges, rates, delays, walks and manual step tables while the
  sweep runs, exactly like the old globals allowed.
* **Endpoints always measured** — the runner clamps the final point onto the
  target value (the legacy "last step never happens" bug class is gone).
* **No GUI access** — the engine only talks through an event queue; pause /
  stop / to-zero arrive as :class:`threading.Event` s (pause is a wait loop,
  not recursion, so long pauses can no longer blow the stack).
* **Deterministic conditions** — region masking is evaluated per point with a
  half-step tolerance from the *current* instructions; coupled equalities are
  solved per step with a warm-started Newton iteration. Nothing is computed
  in a race with the thread start.
* **Reacting to what was measured** — the per-point script sees the row that
  was just written (``reads``, ``row``, ``columns``) alongside ``stop()``,
  ``to_zero()`` and the live program, so an abort condition on a measured
  value is a couple of lines of Python rather than a subsystem.

Loop topology (legacy-compatible)
---------------------------------
Axis 1 is the master (outermost), axis N the innermost measured axis. A new
data file starts whenever the next-to-innermost axis takes a point, with the
outer values embedded in the file name — same rotation and naming as before.
A coupled equality removes the solved axis's own loop and computes it from
its partner every step (legacy 'xy' / 'yz' / 'yx' modes).
"""

from __future__ import annotations

import queue
import threading
import time
from collections import deque
from typing import Optional

import numpy as np

from .condition import ConditionError, ConditionSet
from .config import LiveProgram
from .devices import DeviceRegistry, DriverAdapter
from .events import (ApproachStarted, ApproachFinished, AxisStepped,
                     FileOpened, MapRowCommitted, PointMeasured,
                     PointSkipped, Progress, SweepError, SweepFinished,
                     SweepPaused, SweepResumed, SweepStarted, WalkFinished)
from .labprofile import LabProfile
from .limits import validate_program
from .journal import Journal
from .maps import MapWriter
from .provenance import RunProvenance
from .runner import AxisRunner
from .writer import DataWriter

__all__ = ["SweepEngine"]

_FMT = "{:.3e}".format          # legacy axis-value formatting in CSV rows


def check_start_positions(registry, program) -> list[dict]:
    """Pre-flight: which axes stand away from their sweep start?

    For every loop axis whose parameter is readable, compare the current
    value with the first walk's start point against the device's eps
    (falling back to the axis step). Returns one dict per offender —
    the GUI raises the v1-style 'Start warning' dialog from this.
    Unreadable parameters and failed/NaN readbacks are skipped (nothing
    to warn about without a position).
    """
    out = []
    for ax in program.axes:
        try:
            adapter = registry.connect(ax.device)
        except Exception:                          # noqa: BLE001
            continue
        if not adapter.can_read(ax.parameter):
            continue
        try:
            v = float(adapter.get(ax.parameter))
        except Exception:                          # noqa: BLE001
            continue
        if not np.isfinite(v):
            continue
        eps = adapter.eps(ax.parameter,
                          fallback=max(ax.step_size(False), 1e-12))
        if abs(v - float(ax.start)) > eps:
            out.append({"device": ax.device, "parameter": ax.parameter,
                        "current": v, "start": float(ax.start),
                        "eps": float(eps)})
    return out


class _AxisFault(RuntimeError):
    """A device the sweep depends on failed (NaN / dead readback / set
    failure) — the whole sweep stops with a message naming the device."""


class _Stopped(Exception):
    """Internal control-flow signal: unwind all loops cleanly."""


class SweepEngine(threading.Thread):

    def __init__(self, live: LiveProgram, registry: DeviceRegistry,
                 core_dir: str, out_queue: "queue.Queue", profile=None):
        super().__init__(daemon=True, name="unisweep-engine")
        self.live = live
        self.registry = registry
        self.core_dir = core_dir
        self.q = out_queue
        # The lab profile supplies the pre-flight envelope and the names
        # used in messages. It is taken from the registry's policy when
        # not passed explicitly, so the engine, the Devices page and any
        # agent are always bounded by the same file. Absent a profile this
        # is the empty one and nothing below changes behaviour.
        if profile is None:
            policy = getattr(registry, "policy", None)
            profile = getattr(policy, "profile", None)
        self.profile = profile or LabProfile.empty()

        self.pause_ev = threading.Event()
        self.stop_ev = threading.Event()
        self.tozero_ev = threading.Event()

        prog = live.get()
        self.dims = prog.dimensions
        self.runners = [AxisRunner(live, i) for i in range(self.dims)]
        self.axis_values: list[float] = [float(a.start) for a in prog.axes]
        self.reads: tuple[str, ...] = tuple(prog.reads)   # frozen at start
        self.columns: tuple[str, ...] = ()

        self._adapters: list[Optional[DriverAdapter]] = [None] * self.dims
        self._read_adapters: dict[str, DriverAdapter] = {}
        self._writer: Optional[DataWriter] = None
        self._map: Optional[MapWriter] = None
        self._loop_axes: list[int] = list(range(self.dims))
        self._condition = ConditionSet(prog.condition, self.dims)
        self._cond_version = live.version
        self._script_code = None
        self._script_errors: set[str] = set()
        self._read_errors: set[str] = set()
        self._nan_warned: set[str] = set()
        self._last_reads: list = []
        self._last_row: tuple = ()

        self.provenance: Optional[RunProvenance] = None
        self.journal: Optional[Journal] = None
        self._points_done = 0
        self._durations: deque[float] = deque(maxlen=25)
        self._was_paused = False
        self._snake_entry: dict[int, bool] = {}
        self._stall_streak: dict[int, int] = {}
        self._inner_walk_no = 1

    # ---------------- public control (GUI thread) ----------------------
    def set_paused(self, paused: bool) -> None:
        if paused:
            self.pause_ev.set()
        else:
            self.pause_ev.clear()

    def stop(self) -> None:
        self.stop_ev.set()

    def to_zero(self) -> None:
        self.tozero_ev.set()

    # ---------------- helpers ------------------------------------------
    def _emit(self, event) -> None:
        try:
            self.q.put_nowait(event)
        except queue.Full:      # pragma: no cover - unbounded by default
            pass

    def _error(self, where: str, exc: Exception, fatal: bool = False,
               dedupe: Optional[set] = None) -> None:
        msg = f"{type(exc).__name__}: {exc}"
        if dedupe is not None:
            if msg in dedupe or len(dedupe) >= 5:
                return
            dedupe.add(msg)
        self._emit(SweepError(where=where, message=msg, fatal=fatal))

    def _resolve_devices(self) -> None:
        prog = self.live.get()
        for i, ax in enumerate(prog.axes):
            self._adapters[i] = self.registry.connect(ax.device)
            if ax.parameter not in self._adapters[i].set_options:
                raise RuntimeError(
                    f"'{ax.parameter}' is not settable on {ax.device}")
        for read in self.reads:
            addr, _, _opt = read.rpartition(".")
            if addr not in self._read_adapters:
                self._read_adapters[addr] = self.registry.connect(addr)

    def _build_columns(self) -> tuple[str, ...]:
        prog = self.live.get()
        cols = ["time"]
        for ax in prog.axes:
            cols.append(f"{ax.device}.{ax.parameter}_sweep")
        cols.extend(self.reads)
        return tuple(cols)

    def _refresh_condition(self) -> None:
        v = self.live.version
        if v == self._cond_version:
            return
        self._cond_version = v
        text = self.live.get().condition
        if text.strip() != self._condition.text.strip():
            try:
                new = ConditionSet(text, self.dims)
            except (ConditionError, Exception) as exc:   # noqa: BLE001
                self._error("condition", exc)
                return
            # a coupled equality cannot be introduced/removed mid-sweep
            if (new.coupled is None) == (self._condition.coupled is None):
                self._condition = new

    # ---------------- pre-flight ----------------------------------------
    def _preflight(self) -> bool:
        """Refuse a program the lab profile forbids, before any instrument
        is touched. With no profile there is nothing to refuse, so an
        installation without one behaves exactly as before."""
        if self.profile.is_empty:
            return True
        try:
            problems = validate_program(self.live.get(), self.profile,
                                        self.registry)
        except Exception as exc:                  # noqa: BLE001
            self._error("preflight", exc)
            return True
        errors = [p for p in problems if p.level == "error"]
        for problem in problems:
            if problem.level != "error":
                self._emit(SweepError(where=f"preflight/{problem.where}",
                                      message=problem.message))
        if not errors:
            return True
        detail = "; ".join(f"{p.where}: {p.message}" for p in errors)
        self._emit(SweepError(
            where="preflight", fatal=True, crucial=True,
            message=f"the lab profile refuses this sweep — {detail}"))
        return False

    def _tolerances(self) -> dict[str, float]:
        return {f"ax{i + 1}": self.runners[i].local_step()
                for i in range(self.dims)}

    def _planned_total(self) -> int:
        prog = self.live.get()
        total = 1
        solved = self._condition.coupled.solved - 1 \
            if self._condition.coupled else None
        for i, ax in enumerate(prog.axes):
            if i == solved:
                continue
            total *= max(ax.planned_count(), 1) * ax.effective_walks()
        return total

    # ---------------- pause / stop / to-zero gate ----------------------
    def _gate(self) -> None:
        """Block while paused; raise :class:`_Stopped` on stop / to-zero.

        A wait *loop* — the legacy recursive pause crashed with a
        RecursionError after ~100 s.
        """
        if self.tozero_ev.is_set():
            self._ramp_all_to_zero()
            self.stop_ev.set()
        if self.stop_ev.is_set():
            raise _Stopped
        if self.pause_ev.is_set():
            self._emit(SweepPaused())
            for a in self._adapters:
                if a is not None:
                    try:
                        a.pause()
                    except Exception as exc:      # noqa: BLE001
                        self._error("pause", exc)
            self._was_paused = True
            while self.pause_ev.is_set() and not self.stop_ev.is_set() \
                    and not self.tozero_ev.is_set():
                time.sleep(0.1)
            self._emit(SweepResumed())
            self._gate()                          # re-check stop / to-zero

    def _sleep(self, seconds: float) -> None:
        """Interruptible dwell — stop/pause react within 0.1 s."""
        end = time.perf_counter() + max(seconds, 0.0)
        while True:
            if self.stop_ev.is_set() or self.tozero_ev.is_set() \
                    or self.pause_ev.is_set():
                self._gate()
                if self._was_paused:
                    return                        # dwell forfeited on resume
            remaining = end - time.perf_counter()
            if remaining <= 0:
                return
            time.sleep(min(remaining, 0.1))

    def _ramp_all_to_zero(self) -> None:
        """Legacy to-zero: 10 linear steps to 0 on every sweep device."""
        for i in range(self.dims):
            adapter = self._adapters[i]
            if adapter is None:
                continue
            ax = self.live.axis(i)
            try:
                current = float(adapter.get(ax.parameter)) \
                    if adapter.can_read(ax.parameter) else self.axis_values[i]
            except Exception:                     # noqa: BLE001
                current = self.axis_values[i]
            speed = abs(ax.rate) if adapter.sweepable(ax.parameter) \
                else None
            for v in np.linspace(current, 0.0, 10):
                try:
                    adapter.set(ax.parameter, float(v), speed=speed,
                                safety=True)
                except Exception as exc:          # noqa: BLE001
                    self._error("to-zero", exc)
                    break
                time.sleep(0.1)
            self.axis_values[i] = 0.0

    # ---------------- measurement --------------------------------------
    def _measure_row(self) -> tuple:
        t = round(time.perf_counter() - self._zero_time, 2)
        row: list = [t]
        row += [_FMT(self.axis_values[i]) for i in range(self.dims)]
        self._last_reads = []
        for read in self.reads:
            addr, _, opt = read.rpartition(".")
            from_exception = False
            try:
                v = self._read_adapters[addr].get(opt)
                if v is None or str(v) == "":
                    v = np.nan
            except Exception as exc:              # noqa: BLE001
                # a read parameter is not crucial: warn once (naming the
                # device) and record NaN — the sweep continues
                self._error(f"read {read}", exc, dedupe=self._read_errors)
                v = np.nan
                from_exception = True
            try:
                bad = (not from_exception and isinstance(v, float)
                       and not np.isfinite(v))
            except TypeError:
                bad = False
            if bad and read not in self._nan_warned:
                self._nan_warned.add(read)
                self._error(f"read {read}", ValueError(
                    "device returned NaN — recording NaN and continuing"))
            row.append(v)
            self._last_reads.append(v)
        return tuple(row)

    def _record_point(self) -> None:
        row = self._measure_row()
        self._last_row = row
        self._writer.write(row)
        if self._map is not None:
            self._map.add_point(self.axis_values[self._loop_axes[-1]],
                                self._last_reads,
                                axis_values=tuple(self.axis_values))
        self._points_done += 1
        now = time.perf_counter()
        if hasattr(self, "_last_point_t"):
            self._durations.append(now - self._last_point_t)
        self._last_point_t = now
        self._emit(PointMeasured(row=row,
                                 axis_values=tuple(self.axis_values),
                                 file=self._writer.path or "",
                                 walk=self._inner_walk_no))
        total = self._planned_total()
        eta = None
        if self._durations:
            avg = sum(self._durations) / len(self._durations)
            eta = max(total - self._points_done, 0) * avg
        self._emit(Progress(done=self._points_done, total=total,
                            eta_seconds=eta,
                            elapsed_seconds=now - self._zero_time))
        self._run_script()

    def _run_script(self) -> None:
        prog = self.live.get()
        if not prog.script.strip():
            self._script_code = None
            return
        if self._script_code is None or prog.script != self._script_src:
            try:
                self._script_code = compile(prog.script,
                                            "<unisweep-script>", "exec")
                self._script_src = prog.script
            except SyntaxError as exc:
                self._error("script compile", exc, dedupe=self._script_errors)
                return
        ns = {
            "np": np, "time": time,
            "point": {f"ax{i + 1}": self.axis_values[i]
                      for i in range(self.dims)},
            "values": list(self.axis_values),
            # what was just MEASURED, keyed exactly like the CSV columns.
            # This is what lets a script react to a reading rather than
            # only to a setpoint — "stop when the leakage runs away" is
            #     if abs(reads["GPIB4.A_current"]) > 2e-9: stop()
            # and pulling a range in instead of ending the run is
            #     engine.live.update_axis(0, stop=values[0])
            "reads": dict(zip(self.reads, self._last_reads)),
            "row": tuple(self._last_row),
            "columns": self.columns,
            "walk": self._inner_walk_no,
            "devices": {a.address: a for a in self._adapters if a},
            "engine": self,
            "live": self.live,
            "stop": self.stop,
            "pause": lambda: self.set_paused(True),
            "to_zero": self.to_zero,
        }
        try:
            exec(self._script_code, ns)           # noqa: S102 - user feature
        except Exception as exc:                  # noqa: BLE001
            self._error("script", exc, dedupe=self._script_errors)

    # ---------------- axis application ---------------------------------
    def _apply_axis(self, i: int, value: float,
                    speed: Optional[float] = None,
                    safety: bool = False) -> None:
        ax = self.live.axis(i)
        try:
            self._adapters[i].set(ax.parameter, float(value), speed=speed,
                                  safety=safety)
        except Exception as exc:                  # noqa: BLE001
            raise _AxisFault(
                f"{ax.device}.{ax.parameter}: setting the value failed "
                f"({type(exc).__name__}: {exc}) — sweep stopped") from exc
        self.axis_values[i] = float(value)

    def _solve_coupled(self) -> None:
        c = self._condition.coupled
        if c is None:
            return
        i = c.solved - 1
        values = {f"ax{k + 1}": self.axis_values[k] for k in range(self.dims)}
        solved = c.solve(values, guess=self.axis_values[i])
        self._apply_axis(i, solved)

    # ---------------- walks --------------------------------------------
    def _direction(self, axis_i: int, walk_no: int) -> bool:
        """Walk direction. Plain axes alternate per walk starting forward.

        Snake axes alternate their ENTRY direction across outer points so
        the instrument continues from where it stands instead of jumping
        back. The entry flag is pure state read here and updated once per
        completed walk-set in the loop (geometric continuation: the next
        entry is the opposite of the last walk's direction) — the old
        version toggled state on every call, which only happened to be
        right for an odd number of walks and silently degenerated for
        even counts (e.g. a return sweep implying two walks).
        """
        ax = self.live.axis(axis_i)
        alt = walk_no % 2 == 1
        if ax.snake:
            return self._snake_entry.get(axis_i, False) != alt
        return alt

    def _walks_of(self, axis_i: int) -> int:
        return self.live.axis(axis_i).effective_walks()

    def _measure_walk(self, axis_i: int, backward: bool,
                      first_walk: bool = True) -> None:
        ax = self.live.axis(axis_i)
        adapter = self._adapters[axis_i]
        continuous = (adapter.sweepable(ax.parameter)
                      and not ax.force_stepwise
                      and ax.manual_points is None)
        if continuous:
            if self._measure_walk_continuous(axis_i, backward, first_walk):
                return
            # invalid rate / configuration -> warned; run stepwise instead
        self._measure_walk_stepwise(axis_i, backward, first_walk)

    def _measure_walk_stepwise(self, axis_i: int, backward: bool,
                               first_walk: bool = True) -> None:
        adapter = self._adapters[axis_i]
        approached = not first_walk
        for pt in self.runners[axis_i].walk(backward):
            # A continuation walk starts exactly at the turning point the
            # previous walk just set and measured — the map grid counts the
            # turn ONCE, so re-setting and re-measuring it would duplicate
            # a row and shift every later cell. Skip it; a fresh walk (or
            # a live-edited start elsewhere) is still taken in full.
            if not first_walk and pt.index == 0 and \
                    abs(pt.value - self.axis_values[axis_i]) <= 1e-12:
                continue
            self._gate()
            self._refresh_condition()
            candidate = dict(
                {f"ax{k + 1}": self.axis_values[k] for k in range(self.dims)},
                **{f"ax{axis_i + 1}": pt.value})
            if self._condition.has_region and not self._condition.allows(
                    candidate, self._tolerances()):
                self.axis_values[axis_i] = pt.value   # advance w/o touching HW
                if self._map is not None:
                    self._map.add_skipped(pt.value)
                self._emit(PointSkipped(axis_values=tuple(self.axis_values)))
                continue
            if not approached:
                approached = True
                if self.live.get().approach_start:
                    self._approach_axis(axis_i, pt.value)
            ax = self.live.axis(axis_i)
            # a self-ramping instrument stepped point-by-point still gets a
            # speed, so each step ramps at the configured rate instead of
            # slewing at the instrument's maximum — the RETURN rate on
            # backward walks, not the forward one
            if adapter.sweepable(ax.parameter):
                speed = abs(ax.back_rate if backward
                            and ax.back_rate is not None else ax.rate)
            else:
                speed = None
            self._apply_axis(axis_i, pt.value, speed=speed)
            self._solve_coupled()
            self._was_paused = False
            self._sleep(pt.delay)
            self._record_point()

    # ---------------- sweepable (self-ramping) devices ------------------
    #: no-progress time before a warning / before the walk is aborted
    STALL_WARN_S = 3.0
    STALL_ABORT_S = 12.0

    def _continuous_rate(self, ax, backward: bool, adapter,
                         param: str):
        rate = ax.back_rate if backward and ax.back_rate else ax.rate
        try:
            rate = abs(float(rate))
        except (TypeError, ValueError):
            rate = 0.0
        ms = adapter.maxspeed(param)
        if ms is not None and ms > 0:
            rate = min(rate, ms)
        if rate <= 0 or rate != rate or rate == float("inf"):
            self._error("sweepable", ValueError(
                f"axis {ax.device}.{param}: rate {rate!r} is not usable for "
                f"a continuous ramp — running the walk stepwise instead"))
            return None
        return rate

    def _measure_walk_continuous(self, axis_i: int, backward: bool,
                                 first_walk: bool = True) -> bool:
        """Device ramps itself. Two phases, both live-editable:

        1. **approach** — ramp to the walk's *start* point first (no data
           rows), so a sweep always begins where the program says it does
           instead of wherever the instrument happened to sit;
        2. **sweep** — ramp to the walk's end, recording a row per poll.

        Reaching is direction-aware (an overshoot past the target counts as
        arrived), and a stall watchdog first warns and then aborts the walk
        if the readback stops making progress — a dead ramp can no longer
        spin forever writing rows. Returns False if the configuration can't
        ramp (caller falls back to stepwise).
        """
        adapter = self._adapters[axis_i]
        ax0 = self.live.axis(axis_i)
        if self._continuous_rate(ax0, backward, adapter, ax0.parameter) \
                is None:
            return False
        self._eps_warned = getattr(self, "_eps_warned", set())
        self._approach_moved = False
        if self.live.get().approach_start:
            if not self._ramp_phase(axis_i, backward, approach=True):
                self._note_stall(axis_i)     # aborted (already reported)
                return True
        if self._ramp_phase(axis_i, backward, approach=False,
                            record_start=first_walk
                            or self._approach_moved):
            self._stall_streak[axis_i] = 0   # healthy walk resets
        else:
            self._note_stall(axis_i)
        return True

    def _note_stall(self, axis_i: int) -> None:
        """One aborted walk is a glitch the sweep survives; the SECOND in
        a row means the instrument is wedged — stopping every later row
        would just burn the night writing flat data, so stop the sweep
        with a message naming the device."""
        n = self._stall_streak.get(axis_i, 0) + 1
        self._stall_streak[axis_i] = n
        if n >= 2:
            ax = self.live.axis(axis_i)
            raise _AxisFault(
                f"{ax.device}.{ax.parameter}: two consecutive walks "
                f"aborted (instrument not following its setpoint) — "
                f"sweep stopped")

    def _ramp_phase(self, axis_i: int, backward: bool,
                    approach: bool, record_start: bool = True) -> bool:
        adapter = self._adapters[axis_i]
        param = self.live.axis(axis_i).parameter
        last_ver = -1
        target = rate = eps = travel = None
        stalled_s = 0.0
        warned_stall = False
        prev_dist = None
        recorded_initial = False
        bad_s = 0.0                    # time with NaN / failing readback
        warned_bad = False
        dev_name = f"{self.live.axis(axis_i).device}.{param}"
        while True:
            self._gate()
            self._refresh_condition()
            ver = self.live.axis_version(axis_i)
            if ver != last_ver or self._was_paused or target is None:
                ax = self.live.axis(axis_i)
                walk_start = ax.stop if backward else ax.start
                walk_end = ax.start if backward else ax.stop
                target = float(walk_start if approach else walk_end)
                rate = self._continuous_rate(ax, backward, adapter, param)
                if rate is None:
                    return False
                eps = adapter.eps(param,
                                  fallback=max(ax.step_size(backward) * 0.1,
                                               1e-12))
                span = abs(walk_end - walk_start)
                if span > 0 and eps >= span / 2 \
                        and axis_i not in self._eps_warned:
                    self._eps_warned.add(axis_i)
                    self._error("sweepable", ValueError(
                        f"{ax.device}.{param}: device eps ({eps:g}) covers "
                        f"half the sweep span ({span:g}) — the walk may "
                        f"terminate almost immediately"))
                try:
                    v_now = float(adapter.get(param))
                except Exception:                 # noqa: BLE001
                    v_now = float("nan")
                if np.isfinite(v_now):
                    travel = 1.0 if target >= v_now else -1.0
                    if (target - v_now) * travel <= eps:
                        self.axis_values[axis_i] = target
                        return True               # already there
                    if approach:
                        self._approach_moved = True   # start point changed
                else:
                    # blind start: command anyway; the travel direction is
                    # derived from the first finite readback instead — a
                    # NaN here must not fake a direction or leak into rows
                    travel = None
                adapter.set(param, target, speed=rate)
                last_ver, self._was_paused = ver, False
                stalled_s, prev_dist, warned_stall = 0.0, None, False
                if not approach and not recorded_initial \
                        and record_start and np.isfinite(v_now):
                    # the walk's start value is a data point too — but a
                    # continuation walk starts at the turn point already
                    # measured by the previous walk (grid counts it once)
                    recorded_initial = True
                    self.axis_values[axis_i] = v_now
                    self._solve_coupled()
                    self._record_point()
            delay = max(self.live.axis(axis_i).point_delay(backward), 0.02)
            self._sleep(delay)
            if self._was_paused:
                continue                          # re-command after pause
            try:
                v = float(adapter.get(param))
                read_failed = False
            except Exception as exc:              # noqa: BLE001
                self._error(f"readback {dev_name}", exc,
                            dedupe=self._read_errors)
                read_failed = True
                v = float("nan")
            # NaN or a dead readback on the SWEEP AXIS is crucial: the walk
            # cannot know where it is. Warn (naming the device), give the
            # instrument a grace period to recover, then stop the sweep.
            # Note: a plain NaN would otherwise defeat the stall watchdog —
            # every NaN comparison is False, landing in its reset branch.
            if read_failed or not np.isfinite(v):
                bad_s += delay
                if bad_s >= self.STALL_WARN_S and not warned_bad:
                    warned_bad = True
                    self._emit(SweepError(
                        where="axis device", crucial=True, message=(
                            f"{dev_name}: readback is "
                            f"{'failing' if read_failed else 'NaN'} — the "
                            f"sweep axis position is unknown; stopping in "
                            f"{max(self.STALL_ABORT_S - bad_s, 0):.0f} s "
                            f"unless it recovers")))
                if bad_s >= self.STALL_ABORT_S:
                    raise _AxisFault(
                        f"{dev_name}: readback "
                        f"{'kept failing' if read_failed else 'stayed NaN'} "
                        f"for {bad_s:.0f} s — sweep stopped")
                continue                           # no row with a NaN axis
            if bad_s:
                bad_s, warned_bad = 0.0, False     # recovered
            if travel is None:                     # first finite readback
                travel = 1.0 if target >= v else -1.0
            if approach:
                self._emit(AxisStepped(axis=axis_i + 1, value=v))
            if not approach:
                self.axis_values[axis_i] = v
                self._solve_coupled()
                self._record_point()
            if (target - v) * travel <= eps:      # reached or passed
                self.axis_values[axis_i] = target
                return True
            # ---- stall watchdog ---------------------------------------
            # progress = getting closer than the best distance so far by a
            # NOISE MARGIN — a jittery readback (a real magnet's gauss-level
            # noise) must not keep resetting the timer while the field is
            # actually stuck
            dist = abs(target - v)
            margin = max(eps * 0.5, rate * delay * 0.25, 1e-12)
            if prev_dist is None or dist < prev_dist - margin:
                prev_dist = dist if prev_dist is None else min(prev_dist,
                                                               dist)
                stalled_s = 0.0
                warned_stall = False
            else:
                stalled_s += delay
            if stalled_s >= self.STALL_WARN_S and not warned_stall:
                warned_stall = True
                self._emit(SweepError(where="sweepable", crucial=True,
                                      message=(
                    f"{dev_name} readback stopped moving at {v:g} "
                    f"(target {target:g}) — re-sending the command")))
                # RETRY: an intermittently lost/ignored command (network
                # instruments!) must cost seconds, not the whole row
                try:
                    adapter.set(param, target, speed=rate)
                except Exception as exc:          # noqa: BLE001
                    raise _AxisFault(
                        f"{dev_name}: re-sending the setpoint failed "
                        f"({type(exc).__name__}: {exc}) — sweep stopped") \
                        from exc
            if stalled_s >= self.STALL_ABORT_S:
                self._emit(SweepError(where="sweepable", crucial=True,
                                      message=(
                    f"{dev_name} never reached {target:g} (stuck at {v:g} "
                    f"for {stalled_s:.0f} s) — walk aborted")))
                self.axis_values[axis_i] = v
                return False

    def _goto_parallel(self, entries, phase: str = "approach") -> None:
        """Drive several axes toward targets SIMULTANEOUSLY — the sweep
        start ('all instruments to their initial positions') and the
        mid-sweep repositioning returns. Sweepable axes get one command
        each (with retry-at-warn, noise-margin watchdog); stepwise axes
        are stepped round-robin on their own delays. AxisStepped events
        stream live positions; ApproachStarted/Finished bracket the
        phase so the GUI can show a progress window. entries: list of
        (axis_i, target, use_back_params)."""
        import time as _time
        work = []
        for axis_i, target, back in entries:
            ax = self.live.axis(axis_i)
            adapter = self._adapters[axis_i]
            readable = adapter.can_read(ax.parameter)
            cur = None
            if readable:
                try:
                    cur = float(adapter.get(ax.parameter))
                except Exception:               # noqa: BLE001
                    cur = None
                if cur is not None and not np.isfinite(cur):
                    cur = None
            eps = adapter.eps(ax.parameter,
                              fallback=max(ax.step_size(back), 1e-12))
            if cur is None and back:
                # returns can trust the setpoint the engine tracked
                cur = float(self.axis_values[axis_i])
                if not np.isfinite(cur):
                    cur = None
            if cur is not None and abs(cur - target) <= eps:
                self.axis_values[axis_i] = float(target)
                continue                        # already there
            work.append({"i": axis_i, "target": float(target),
                         "back": back, "cur": cur, "eps": eps})
        if not work:
            return
        self._emit(ApproachStarted(
            targets=tuple((w["i"] + 1, self.live.axis(w["i"]).device,
                           self.live.axis(w["i"]).parameter,
                           w["cur"] if w["cur"] is not None
                           else float("nan"), w["target"])
                          for w in work),
            phase=phase))
        try:
            self._goto_parallel_run(work)
        finally:
            self._emit(ApproachFinished(phase=phase))

    def _goto_parallel_run(self, work) -> None:
        import time as _time
        sweeps, steps = [], []
        for w in work:
            ax = self.live.axis(w["i"])
            adapter = self._adapters[w["i"]]
            rate = abs(ax.back_rate if (w["back"] and ax.back_rate)
                       else ax.rate) or None
            if adapter.sweepable(ax.parameter) and not ax.force_stepwise:
                try:
                    adapter.set(ax.parameter, w["target"], speed=rate)
                except Exception as exc:        # noqa: BLE001
                    raise _AxisFault(
                        f"{ax.device}.{ax.parameter}: moving to the "
                        f"initial position failed "
                        f"({type(exc).__name__}: {exc})") from exc
                w.update(rate=rate, best=None, stalled=0.0, warned=False,
                         t_last=_time.perf_counter())
                sweeps.append(w)
            else:
                v0 = w["cur"]
                if v0 is None:
                    continue    # unknown position: the walk's own first
                                # apply will land the start point
                step = max(ax.step_size(w["back"]), 1e-12)
                sign = 1.0 if w["target"] > v0 else -1.0
                spd = rate if adapter.sweepable(ax.parameter) else None
                w.update(v=v0, step=step, sign=sign, speed=spd,
                         delay=ax.point_delay(w["back"]),
                         due=_time.perf_counter(), rate=rate)
                steps.append(w)
        while sweeps or steps:
            self._gate()
            now = _time.perf_counter()
            for w in list(steps):
                if now < w["due"]:
                    continue
                ax = self.live.axis(w["i"])
                nxt = w["v"] + w["sign"] * w["step"]
                if w["sign"] * (w["target"] - nxt) <= w["step"] * 1e-9:
                    if w["back"]:
                        # a RETURN must land exactly (nothing follows);
                        # an approach stops one step short — the walk's
                        # first apply sets the start point exactly once
                        self._apply_axis(w["i"], w["target"],
                                         speed=w["speed"])
                        self._emit(AxisStepped(axis=w["i"] + 1,
                                               value=w["target"]))
                    steps.remove(w)
                    continue
                w["v"] = nxt
                self._apply_axis(w["i"], nxt, speed=w["speed"])
                self._emit(AxisStepped(axis=w["i"] + 1, value=nxt))
                w["due"] = now + max(w["delay"], 1e-3)
            for w in list(sweeps):
                ax = self.live.axis(w["i"])
                adapter = self._adapters[w["i"]]
                try:
                    v = float(adapter.get(ax.parameter))
                except Exception:               # noqa: BLE001
                    v = float("nan")
                dt, w["t_last"] = now - w["t_last"], now
                if np.isfinite(v):
                    self.axis_values[w["i"]] = v
                    self._emit(AxisStepped(axis=w["i"] + 1, value=v))
                    if abs(w["target"] - v) <= w["eps"]:
                        self.axis_values[w["i"]] = w["target"]
                        sweeps.remove(w)
                        continue
                    dist = abs(w["target"] - v)
                    margin = max(w["eps"] * 0.5,
                                 (w["rate"] or 0.0) * 0.1 * 0.25, 1e-12)
                    if w["best"] is None or dist < w["best"] - margin:
                        w["best"] = dist if w["best"] is None \
                            else min(w["best"], dist)
                        w["stalled"], w["warned"] = 0.0, False
                    else:
                        w["stalled"] += dt
                    if w["stalled"] >= self.STALL_WARN_S \
                            and not w["warned"]:
                        w["warned"] = True
                        self._error("approach", RuntimeError(
                            f"{ax.device}.{ax.parameter} stuck at {v:g} "
                            f"moving to {w['target']:g} — re-sending"))
                        try:
                            adapter.set(ax.parameter, w["target"],
                                        speed=w["rate"])
                        except Exception:       # noqa: BLE001
                            pass
                    if w["stalled"] >= self.STALL_ABORT_S:
                        self._emit(SweepError(where="approach",
                                              crucial=True, message=(
                            f"{ax.device}.{ax.parameter}: never reached "
                            f"its initial position (stuck at {v:g}) — "
                            f"continuing from there")))
                        sweeps.remove(w)
                        continue
            self._sleep(0.05)

    def _return_level(self, k: int, loop_axes: list[int]) -> None:
        """After a non-outermost axis finishes its pass: walk it (and the
        finished inner axes below it, unless they snake) back to their
        start values TOGETHER — a pure repositioning move, nothing swept,
        nothing recorded — before the axis above makes its step."""
        entries = []
        for j in range(k, len(loop_axes)):
            axis_i = loop_axes[j]
            ax = self.live.axis(axis_i)
            if ax.snake:
                continue
            entries.append((axis_i, float(ax.start), True))
        if entries:
            self._goto_parallel(entries, phase="return")

    def _approach_axis(self, axis_i: int, target: float) -> None:
        """Walk a STEPWISE axis from wherever the instrument currently sits
        to the sweep's entry point, in that axis's own step/delay — the
        legacy 'initial step' behaviour, for any dimension. Without it a
        device parked away from the start boundary received one big jump.

        Walks up to (not including) the target: the caller's normal apply
        performs the final set, so the entry point is set exactly once.
        No rows are recorded — this is positioning, not measurement.
        """
        adapter = self._adapters[axis_i]
        ax = self.live.axis(axis_i)
        if not adapter.can_read(ax.parameter):
            return                          # unknown position -> direct set
        try:
            v = float(adapter.get(ax.parameter))
        except Exception:                   # noqa: BLE001
            return
        if not np.isfinite(v):
            return
        step = ax.step_size(False)
        if step <= 0 or abs(target - v) <= step:
            return                          # one normal set covers it
        sign = 1.0 if target > v else -1.0
        sweepable = adapter.sweepable(ax.parameter)
        speed = abs(ax.rate) if sweepable else None
        while sign * (target - (v + sign * step)) > step * 1e-9:
            self._gate()
            v += sign * step
            try:
                adapter.set(ax.parameter, float(v), speed=speed)
            except Exception as exc:        # noqa: BLE001
                raise _AxisFault(
                    f"{ax.device}.{ax.parameter}: setting the value failed "
                    f"during the approach ({type(exc).__name__}: {exc}) — "
                    f"sweep stopped") from exc
            self.axis_values[axis_i] = float(v)
            self._emit(AxisStepped(axis=axis_i + 1, value=float(v)))
            self._sleep(ax.point_delay(False))
            ax = self.live.axis(axis_i)     # live-editable step/delay
            step = max(ax.step_size(False), step * 0.0) or step

    def _settle_axis(self, axis_i: int, value: float,
                     backward: bool) -> None:
        """Outer sweepable axis stepped: ramp there at the configured rate
        and *wait until the instrument arrives* (with the same stall
        protection) before the inner scan starts — a magnet map must not
        scan while the field is still ramping."""
        adapter = self._adapters[axis_i]
        ax = self.live.axis(axis_i)
        param = ax.parameter
        rate = self._continuous_rate(ax, backward, adapter, param)
        if rate is None:
            self._apply_axis(axis_i, value)
            return
        eps = adapter.eps(param, fallback=max(ax.step_size(backward) * 0.1,
                                              1e-12))
        self._apply_axis(axis_i, value, speed=rate)
        if not adapter.can_read(param):
            try:
                v_from = self.axis_values[axis_i]
            except (TypeError, IndexError):
                v_from = value
            self._sleep(abs(value - v_from) / rate)
            return
        travel = None
        stalled_s, prev_dist, warned = 0.0, None, False
        while True:
            self._gate()
            self._sleep(0.1)
            try:
                v = float(adapter.get(param))
            except Exception:                     # noqa: BLE001
                return
            if not np.isfinite(v):
                stalled_s += 0.1
                if stalled_s >= self.STALL_ABORT_S:
                    self._emit(SweepError(where="sweepable", crucial=True,
                                          message=(
                        f"{param} readback is NaN while settling at "
                        f"{value:g} — continuing without confirmation")))
                    return
                continue
            if travel is None:
                travel = 1.0 if value >= v else -1.0
            if (value - v) * travel <= eps:
                return
            dist = abs(value - v)
            margin = max(eps * 0.5, rate * 0.1 * 0.25, 1e-12)
            if prev_dist is None or dist < prev_dist - margin:
                prev_dist = dist if prev_dist is None else min(prev_dist,
                                                               dist)
                stalled_s, warned = 0.0, False
            else:
                stalled_s += 0.1
            if stalled_s >= self.STALL_WARN_S and not warned:
                warned = True
                self._error("sweepable", RuntimeError(
                    f"{param} stuck at {v:g} while moving to {value:g} — "
                    f"re-sending the command"))
                try:
                    adapter.set(param, float(value), speed=rate)
                except Exception:                 # noqa: BLE001
                    pass
            if stalled_s >= self.STALL_ABORT_S:
                self._error("sweepable", RuntimeError(
                    f"{param} never settled at {value:g} — continuing with "
                    f"the instrument at {v:g}"))
                return

    # ---------------- map spreadsheets ----------------------------------
    def _ensure_map(self, data_path: str) -> None:
        """Create the MapWriter on the first data file (2-D / 3-D only)."""
        if self._map is not None or len(self._loop_axes) < 2:
            return
        prog = self.live.get()
        try:
            self._map = MapWriter(
                self.core_dir, self.live, self._loop_axes, self.reads,
                data_path, interpolated=prog.map_interpolated,
                images=prog.map_images, write_files=prog.save_maps,
                style=prog.map_style, uniform=prog.map_uniform)
        except Exception as exc:              # noqa: BLE001
            self._error("maps", exc)
            self._map = None

    # ---------------- nested loops --------------------------------------
    def _loop_level(self, k: int, loop_axes: list[int]) -> None:
        axis_i = loop_axes[k]
        last = k == len(loop_axes) - 1
        walk_no = 0
        # a non-innermost axis makes exactly ONE measured pass: walking it
        # back does NOT replay the whole nested loop — the way back is a
        # repositioning return (below), never a measurement
        while walk_no < (self._walks_of(axis_i) if last else 1):
            backward = self._direction(axis_i, walk_no)
            if last:
                self._inner_walk_no = walk_no + 1
                self._measure_walk(axis_i, backward,
                                   first_walk=(walk_no == 0))
            else:
                for pt in self.runners[axis_i].walk(backward):
                    self._gate()
                    ax = self.live.axis(axis_i)
                    adapter = self._adapters[axis_i]
                    if adapter.sweepable(ax.parameter) \
                            and not ax.force_stepwise:
                        self._settle_axis(axis_i, pt.value, backward)
                    else:
                        if walk_no == 0 and pt.index == 0 \
                                and self.live.get().approach_start:
                            self._approach_axis(axis_i, pt.value)
                        self._apply_axis(axis_i, pt.value)
                    self._solve_coupled()
                    self._emit(AxisStepped(axis=axis_i + 1, value=pt.value))
                    self._sleep(pt.delay)
                    if k + 1 == len(loop_axes) - 1:
                        outer = [self.axis_values[j] for j in range(self.dims)
                                 if j != loop_axes[-1]]
                        path = self._writer.open_file(outer)
                        self._emit(FileOpened(path=path, columns=self.columns))
                        self._ensure_map(path)
                    self._loop_level(k + 1, loop_axes)
                    if self._map is not None:
                        if k == len(loop_axes) - 2:
                            result = self._map.commit_row(
                                row_value=self.axis_values[loop_axes[k]],
                                master_value=self.axis_values[loop_axes[0]])
                            if result is not None:
                                grid, rows = result
                                self._emit(MapRowCommitted(
                                    grid=grid, read_rows=rows,
                                    row_value=self.axis_values[loop_axes[k]],
                                    master_value=self.axis_values[
                                        loop_axes[0]],
                                    iteration=self._map.iteration))
                        elif k == len(loop_axes) - 3:
                            self._map.new_iteration()
            self._emit(WalkFinished(axis=axis_i + 1, walk=walk_no + 1))
            walk_no += 1
        if self.live.axis(axis_i).snake:
            # continue from where the instrument now stands: the next
            # entry direction is the opposite of the last walk taken
            self._snake_entry[axis_i] = not backward
        if not last and k > 0:
            # slave (and everything below it) returns to its initial
            # value before the axis above steps; the outermost never
            # returns ("don't go back along master")
            self._return_level(k, loop_axes)

    # ---------------- main ----------------------------------------------
    def run(self) -> None:
        stopped = False
        try:
            if not self._preflight():
                stopped = True
                return
            self._resolve_devices()
            self.columns = self._build_columns()
            prog = self.live.get()
            # captured after the devices resolve, so instrument identities
            # and loggable settings can actually be read — once, here,
            # rather than at every file rotation
            self.provenance = RunProvenance(
                self.core_dir, prog, self.profile, self.registry).capture()
            self._writer = DataWriter(self.core_dir, self.columns,
                                      prog.filename,
                                      provenance=self.provenance)
            try:
                self.journal = Journal(self.core_dir)
                self.journal.start_run(self.provenance,
                                       dimensions=self.dims)
            except Exception as exc:              # noqa: BLE001
                self._error("journal", exc)       # never fatal
            # initialise current positions from readback where possible
            for i in range(self.dims):
                ax = prog.axes[i]
                if self._adapters[i].can_read(ax.parameter):
                    try:
                        self.axis_values[i] = float(
                            self._adapters[i].get(ax.parameter))
                    except Exception:             # noqa: BLE001
                        pass
            self._zero_time = time.perf_counter()
            self._emit(SweepStarted(columns=self.columns,
                                    dimensions=self.dims,
                                    planned_points=self._planned_total()))
            solved = self._condition.coupled.solved - 1 \
                if self._condition.coupled else None
            loop_axes = [i for i in range(self.dims) if i != solved]
            self._loop_axes = loop_axes
            if len(loop_axes) == 1:
                path = self._writer.open_file(
                    [self.axis_values[j] for j in range(self.dims)
                     if j != loop_axes[-1]])
                self._emit(FileOpened(path=path, columns=self.columns))
            if self.live.get().approach_start:
                # ALL instruments move to their initial positions at
                # once (parallel), with live progress events
                self._goto_parallel(
                    [(i, float(self.live.axis(i).start), False)
                     for i in loop_axes], phase="approach")
            self._loop_level(0, loop_axes)
        except _Stopped:
            stopped = True
        except _AxisFault as exc:
            self._emit(SweepError(where="axis device", message=str(exc),
                                  fatal=True, crucial=True))
        except Exception as exc:                  # noqa: BLE001
            self._error("engine", exc, fatal=True)
            stopped = True
        finally:
            try:
                if self._writer is not None:
                    self._writer.close()
            except Exception:                     # noqa: BLE001
                pass
            if self._map is not None:
                try:
                    self._map.finish()
                except Exception:                 # noqa: BLE001
                    pass
            if self.live.get().to_zero_on_finish and not self.tozero_ev.is_set():
                try:
                    self._ramp_all_to_zero()
                except Exception:                 # noqa: BLE001
                    pass
            for a in self._adapters:
                if a is not None:
                    a.clear()
            if self.journal is not None and self.provenance is not None:
                # after the writer closed, so the file list is complete
                try:
                    self.journal.finish_run(
                        self.provenance.run_id, stopped=stopped,
                        points=self._points_done,
                        files=list(self.provenance.files),
                        directory=getattr(self._writer, "directory", ""))
                except Exception as exc:          # noqa: BLE001
                    self._error("journal", exc)
            self._emit(SweepFinished(stopped=stopped,
                                     points=self._points_done))

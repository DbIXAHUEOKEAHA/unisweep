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
from .events import (AxisStepped, FileOpened, MapRowCommitted, PointMeasured,
                     PointSkipped, Progress, SweepError, SweepFinished,
                     SweepPaused, SweepResumed, SweepStarted, WalkFinished)
from .maps import MapWriter
from .runner import AxisRunner
from .writer import DataWriter

__all__ = ["SweepEngine"]

_FMT = "{:.3e}".format          # legacy axis-value formatting in CSV rows


class _AxisFault(RuntimeError):
    """A device the sweep depends on failed (NaN / dead readback / set
    failure) — the whole sweep stops with a message naming the device."""


class _Stopped(Exception):
    """Internal control-flow signal: unwind all loops cleanly."""


class SweepEngine(threading.Thread):

    def __init__(self, live: LiveProgram, registry: DeviceRegistry,
                 core_dir: str, out_queue: "queue.Queue"):
        super().__init__(daemon=True, name="unisweep-engine")
        self.live = live
        self.registry = registry
        self.core_dir = core_dir
        self.q = out_queue

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

        self._points_done = 0
        self._durations: deque[float] = deque(maxlen=25)
        self._was_paused = False
        self._snake_backward: dict[int, bool] = {}

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
            total *= max(ax.planned_count(), 1) * max(ax.walks, 1)
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
                    adapter.set(ax.parameter, float(v), speed=speed)
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
                                 file=self._writer.path or ""))
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
            "devices": {a.address: a for a in self._adapters if a},
            "engine": self,
        }
        try:
            exec(self._script_code, ns)           # noqa: S102 - user feature
        except Exception as exc:                  # noqa: BLE001
            self._error("script", exc, dedupe=self._script_errors)

    # ---------------- axis application ---------------------------------
    def _apply_axis(self, i: int, value: float,
                    speed: Optional[float] = None) -> None:
        ax = self.live.axis(i)
        try:
            self._adapters[i].set(ax.parameter, float(value), speed=speed)
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
        ax = self.live.axis(axis_i)
        if ax.snake:
            back = self._snake_backward.get(axis_i, False)
            self._snake_backward[axis_i] = not back
            return back
        return walk_no % 2 == 1

    def _walks_of(self, axis_i: int) -> int:
        return max(int(self.live.axis(axis_i).walks), 1)

    def _measure_walk(self, axis_i: int, backward: bool) -> None:
        ax = self.live.axis(axis_i)
        adapter = self._adapters[axis_i]
        continuous = (adapter.sweepable(ax.parameter)
                      and not ax.force_stepwise
                      and ax.manual_points is None)
        if continuous:
            if self._measure_walk_continuous(axis_i, backward):
                return
            # invalid rate / configuration -> warned; run stepwise instead
        self._measure_walk_stepwise(axis_i, backward)

    def _measure_walk_stepwise(self, axis_i: int, backward: bool) -> None:
        adapter = self._adapters[axis_i]
        for pt in self.runners[axis_i].walk(backward):
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
            ax = self.live.axis(axis_i)
            # a self-ramping instrument stepped point-by-point still gets a
            # speed, so each step ramps at the configured rate instead of
            # slewing at the instrument's maximum
            speed = abs(ax.rate) if adapter.sweepable(ax.parameter) else None
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

    def _measure_walk_continuous(self, axis_i: int, backward: bool) -> bool:
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
        if not self._ramp_phase(axis_i, backward, approach=True):
            return True                      # aborted (already reported)
        self._ramp_phase(axis_i, backward, approach=False)
        return True

    def _ramp_phase(self, axis_i: int, backward: bool,
                    approach: bool) -> bool:
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
                else:
                    # blind start: command anyway; the travel direction is
                    # derived from the first finite readback instead — a
                    # NaN here must not fake a direction or leak into rows
                    travel = None
                adapter.set(param, target, speed=rate)
                last_ver, self._was_paused = ver, False
                stalled_s, prev_dist, warned_stall = 0.0, None, False
                if not approach and not recorded_initial \
                        and np.isfinite(v_now):
                    # the walk's start value is a data point too
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
            if not approach:
                self.axis_values[axis_i] = v
                self._solve_coupled()
                self._record_point()
            if (target - v) * travel <= eps:      # reached or passed
                self.axis_values[axis_i] = target
                return True
            # ---- stall watchdog ---------------------------------------
            dist = abs(target - v)
            if prev_dist is not None and prev_dist - dist <= \
                    max(eps * 0.01, 1e-15):
                stalled_s += delay
            else:
                stalled_s = 0.0
                warned_stall = False
            prev_dist = dist
            if stalled_s >= self.STALL_WARN_S and not warned_stall:
                warned_stall = True
                self._emit(SweepError(where="sweepable", crucial=True,
                                      message=(
                    f"{dev_name} readback stopped moving at {v:g} "
                    f"(target {target:g}) — check the instrument")))
            if stalled_s >= self.STALL_ABORT_S:
                self._emit(SweepError(where="sweepable", crucial=True,
                                      message=(
                    f"{dev_name} never reached {target:g} (stuck at {v:g} "
                    f"for {stalled_s:.0f} s) — walk aborted")))
                self.axis_values[axis_i] = v
                return False

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
            if prev_dist is not None and prev_dist - dist <= \
                    max(eps * 0.01, 1e-15):
                stalled_s += 0.1
            else:
                stalled_s, warned = 0.0, False
            prev_dist = dist
            if stalled_s >= self.STALL_WARN_S and not warned:
                warned = True
                self._error("sweepable", RuntimeError(
                    f"{param} stuck at {v:g} while moving to {value:g}"))
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
        while walk_no < self._walks_of(axis_i):
            backward = self._direction(axis_i, walk_no)
            if last:
                self._measure_walk(axis_i, backward)
            else:
                for pt in self.runners[axis_i].walk(backward):
                    self._gate()
                    ax = self.live.axis(axis_i)
                    adapter = self._adapters[axis_i]
                    if adapter.sweepable(ax.parameter) \
                            and not ax.force_stepwise:
                        self._settle_axis(axis_i, pt.value, backward)
                    else:
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

    # ---------------- main ----------------------------------------------
    def run(self) -> None:
        stopped = False
        try:
            self._resolve_devices()
            self.columns = self._build_columns()
            prog = self.live.get()
            self._writer = DataWriter(self.core_dir, self.columns,
                                      prog.filename)
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
            self._emit(SweepFinished(stopped=stopped,
                                     points=self._points_done))

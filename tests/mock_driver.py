"""A mock instrument implementing the legacy duck-typed driver contract."""

import time


class MockDevice:
    """Records every set; readable; optionally self-ramping ('sweepable')."""

    def __init__(self, adress="MOCK::1", sweepable_flags=None, ramp_rate=50.0,
                 stall_at=None, overshoot=0.0, fault=None):
        self.adress = adress
        self.set_options = ["Volt", "Curr"]
        self.get_options = ["Volt", "Curr", "Noise"]
        self.eps = [1e-9, 1e-9]
        self.sweepable = sweepable_flags or [False, False]
        self.maxspeed = [None, None]
        self._values = {"Volt": 0.0, "Curr": 0.0}
        self.set_log = []            # (param, value, speed, t)
        self.paused = False
        self._ramp = None            # (param, target, rate, t0, v0)
        self._ramp_rate = ramp_rate
        self.stall_at = stall_at     # freeze ramps at this value (fault)
        self.overshoot = overshoot   # settle past the target by this much
        # realistic fault injection:
        #   {"param": "Volt", "kind": "nan"|"raise"|"hang"|"set_raise",
        #    "start": first affected call (1-based),
        #    "end": first healthy call again (None = forever),
        #    "hang_s": seconds to block for kind="hang"}
        self.fault = fault
        self.read_calls: dict[str, int] = {}
        self.set_calls: dict[str, int] = {}

    # ---- getters ----------------------------------------------------
    def _fault_active(self, p, kind, counter):
        f = self.fault
        if not f or f.get("param") != p or f.get("kind") != kind:
            return False
        n = counter.get(p, 0)
        start = f.get("start", 1)
        end = f.get("end")
        return n >= start and (end is None or n < end)

    def _current(self, p):
        self.read_calls[p] = self.read_calls.get(p, 0) + 1
        if self._fault_active(p, "hang", self.read_calls):
            time.sleep(self.fault.get("hang_s", 1.0))
        if self._fault_active(p, "raise", self.read_calls):
            raise IOError(f"{p}: instrument not responding")
        if self._ramp and self._ramp[0] == p and not self.paused:
            _, target, rate, t0, v0 = self._ramp
            dv = rate * (time.perf_counter() - t0)
            sign = 1 if target > v0 else -1
            v = v0 + dv * sign
            if self.stall_at is not None and \
                    (v - self.stall_at) * sign >= 0 and \
                    (target - self.stall_at) * sign > 0:
                self._values[p] = self.stall_at      # fault: ramp freezes
            elif abs(target - v0) <= dv:
                self._values[p] = target + self.overshoot * sign
                self._ramp = None
            else:
                self._values[p] = v
        if self._fault_active(p, "nan", self.read_calls):
            return float("nan")
        return self._values[p]

    def Volt(self):
        return self._current("Volt")

    def Curr(self):
        return self._current("Curr")

    def Noise(self):
        return 0.5

    # ---- setters ----------------------------------------------------
    def set_Volt(self, value=None, speed=None):
        self._set("Volt", value, speed)

    def set_Curr(self, value=None, speed=None):
        self._set("Curr", value, speed)

    def _set(self, p, value, speed):
        self.set_calls[p] = self.set_calls.get(p, 0) + 1
        if self._fault_active(p, "set_raise", self.set_calls):
            raise IOError(f"{p}: set command rejected")
        self.set_log.append((p, float(value), speed, time.perf_counter()))
        idx = self.set_options.index(p)
        if self.sweepable[idx] and speed is not None:
            self._ramp = (p, float(value), abs(speed) or self._ramp_rate,
                          time.perf_counter(), self._values[p])
        else:
            self._values[p] = float(value)

    def pause(self):
        self.paused = True

    def clear(self):
        self.paused = False

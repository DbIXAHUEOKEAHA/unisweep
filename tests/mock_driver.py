"""A mock instrument implementing the legacy duck-typed driver contract."""

import time


class MockDevice:

    #: every instantiation appends its address here (double-init detector)
    init_log: list = []
    #: adapters closed through the registry appear here
    close_log: list = []

    """Records every set; readable; optionally self-ramping ('sweepable')."""

    def __init__(self, adress="MOCK::1", sweepable_flags=None, ramp_rate=50.0,
                 stall_at=None, overshoot=0.0, fault=None, noise=0.0):
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
        self.noise = noise           # gaussian readback jitter (1 sigma)
        self._frozen: dict[str, float] = {}
        self.read_calls: dict[str, int] = {}
        self.set_calls: dict[str, int] = {}
        self.closed = False
        MockDevice.init_log.append(adress)

    def close(self):
        self.closed = True
        MockDevice.close_log.append(self.adress)

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
        if self._fault_active(p, "freeze_read", self.read_calls):
            if p not in self._frozen:
                self._frozen[p] = self._values[p]
            return self._frozen[p]       # readback pinned; device may move
        self._frozen.pop(p, None)
        v = self._values[p]
        if self.noise:
            import random
            v = v + random.gauss(0.0, self.noise)
        return v

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
        if self._fault_active(p, "deaf", self.set_calls):
            return                    # command silently ignored (wedged)
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


class OptiCoolMock:
    """High-fidelity stand-in built from MEASURED OptiCool behaviour:

    * ``Field``: honours speed; ~LATENCY s of dead time between the
      command and motion (measured 1.5–2 s); overshoots the target by
      ~OVERSHOOT and settles back; readback carries gaussian NOISE.
    * ``T_finger``: slow self-ramping (K/min-scale), tiny eps, and the
      driver's read-side sleep.
    * both live on ONE device, like the real cryostat.

    All timing/values are scaled ~100x faster than the night scan; the
    RATIOS (eps/step, latency/warn, noise/eps) match the real system.
    """

    LATENCY = 0.02          # s, command -> motion dead time (night: ~1.8)
    OVERSHOOT = 2.0         # units past target before settling back
    SETTLE_S = 0.03         # s to bleed the overshoot away
    NOISE = 0.3             # 1-sigma readback jitter
    T_READ_SLEEP = 0.0005   # driver's time.sleep in T_finger()

    def __init__(self, adress="OC::1"):
        import random
        self.adress = adress
        self._rnd = random.Random(hash(adress) & 0xffff)
        self.set_options = ["T_finger", "Field"]
        self.get_options = ["T_finger", "Field"]
        self.sweepable = [True, True]
        self.maxspeed = [50.0, 1100.0]
        self.eps = [0.05, 5.0]          # night: T 0.05 K, Field 50/110 Oe
        self._v = {"T_finger": 3.0, "Field": 0.0}
        self._ramp = {}                 # param -> (target, rate, t_go, v0)
        self._pending = {}              # param -> (target, rate, t_start)
        self._settle = {}               # param -> (from_v, t0)
        self.set_log = []
        self.paused = False

    # ---------------- physics ----------------------------------------
    def _advance(self, p):
        import time as _t
        now = _t.perf_counter()
        if p in self._pending:
            target, rate, t0 = self._pending[p]
            if now - t0 >= self.LATENCY:
                del self._pending[p]
                self._ramp[p] = (target, rate, now, self._v[p])
        if p in self._ramp and not self.paused:
            target, rate, t0, v0 = self._ramp[p]
            dv = rate * (now - t0)
            if abs(target - v0) <= dv:
                sign = 1.0 if target > v0 else -1.0
                self._v[p] = target + (self.OVERSHOOT * sign
                                       if p == "Field" else 0.0)
                del self._ramp[p]
                self._settle[p] = (self._v[p], now)
            else:
                self._v[p] = v0 + dv * (1 if target > v0 else -1)
        if p in self._settle:
            from_v, t0 = self._settle[p]
            target = self.set_log[-1][1] if self.set_log else from_v
            frac = min((now - t0) / self.SETTLE_S, 1.0)
            # bleed the overshoot back toward the last target of p
            tgt = next((v for (pp, v, sp, tt) in reversed(self.set_log)
                        if pp == p), from_v)
            self._v[p] = from_v + (tgt - from_v) * frac
            if frac >= 1.0:
                del self._settle[p]

    def _read(self, p):
        import time as _t
        self._advance(p)
        noise = self._rnd.gauss(0.0, self.NOISE) if p == "Field" else 0.0
        if p == "T_finger":
            _t.sleep(self.T_READ_SLEEP)
        return self._v[p] + noise

    def T_finger(self):
        return self._read("T_finger")

    def Field(self):
        return self._read("Field")

    def _set(self, p, value, speed):
        import time as _t
        self._advance(p)
        self.set_log.append((p, float(value), speed, _t.perf_counter()))
        rate = abs(speed) if speed else self.maxspeed[
            self.set_options.index(p)]
        self._pending[p] = (float(value), rate, _t.perf_counter())
        self._settle.pop(p, None)

    def set_T_finger(self, value, speed=None):
        self._set("T_finger", value, speed)

    def set_Field(self, value, speed=None):
        self._set("Field", value, speed)

    def pause(self):
        self.paused = True

    def clear(self):
        self.paused = False

    def close(self):
        pass

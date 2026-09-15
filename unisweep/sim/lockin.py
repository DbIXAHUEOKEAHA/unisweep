"""Shared behaviour of the simulated lock-in amplifiers.

Two channels measure the Hall bar: the longitudinal pair (Vxx) and the
transverse pair (Vxy). They are separate instruments, as they are in a real
rack, and they share one oscillator: the XX unit's ``amplitude`` drives the
sample through a 1 Mohm bias resistor, so the excitation current is
``amplitude / 1e6`` and setting the XY unit's amplitude changes nothing
about the measurement. That asymmetry is real and worth discovering.

The value returned is filtered by the time constant over the time that has
actually elapsed since the channel was last read. Sweep faster than a few
time constants per point and the curve lags, hysteretically, without any
warning — which is the single most common way a transport measurement is
quietly wrong.
"""

from __future__ import annotations

import math

from .rig import rig


class SimLockinBase:
    """Instrument face of one lock-in channel.

    Subclasses set :attr:`CHANNEL` to ``"xx"`` or ``"xy"`` and declare
    their own option lists, so that Unisweep can read the lists off the
    class without connecting.
    """

    CHANNEL = "xx"
    MODEL = "SIM-LIA"

    def __init__(self, adress=None):
        self.adress = adress
        self.address = adress
        self.rig = rig()

    # ---- identity --------------------------------------------------------
    def IDN(self):
        return f'UNISWEEP,{type(self).__name__},{self.MODEL},2.0'

    def channel(self):
        return self.CHANNEL

    # ---- readback --------------------------------------------------------
    def x(self):
        """In-phase voltage, V."""
        return self.rig.lockin_xy_pair(self.CHANNEL)[0]

    def y(self):
        """Quadrature voltage, V. Small for a resistive sample; a large
        value means the phase is wrong or something is reactive."""
        return self.rig.lockin_xy_pair(self.CHANNEL)[1]

    def r(self):
        vx, vy = self.rig.lockin_xy_pair(self.CHANNEL)
        return math.hypot(vx, vy)

    def Θ(self):
        vx, vy = self.rig.lockin_xy_pair(self.CHANNEL)
        return math.degrees(math.atan2(vy, vx))

    def amplitude(self):
        return self.rig.get_lockin(self.CHANNEL, "amplitude")

    def frequency(self):
        return self.rig.get_lockin(self.CHANNEL, "frequency")

    def time_constant(self):
        return self.rig.get_lockin(self.CHANNEL, "time_constant")

    def sensitivity(self):
        return self.rig.get_lockin(self.CHANNEL, "sensitivity")

    def phase(self):
        return self.rig.get_lockin(self.CHANNEL, "phase")

    def excitation_current(self):
        """The current actually flowing through the sample, A."""
        return self.rig.ac_current()

    # ---- commands --------------------------------------------------------
    def set_amplitude(self, value, speed=None):
        self.rig.set_lockin(self.CHANNEL, "amplitude", value)

    def set_frequency(self, value, speed=None):
        self.rig.set_lockin(self.CHANNEL, "frequency", value)

    def set_time_constant(self, value, speed=None):
        self.rig.set_lockin(self.CHANNEL, "time_constant", value)

    def set_sensitivity(self, value, speed=None):
        self.rig.set_lockin(self.CHANNEL, "sensitivity", value)

    def set_phase(self, value, speed=None):
        self.rig.set_lockin(self.CHANNEL, "phase", value)

    def close(self):
        return

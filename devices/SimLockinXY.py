"""Simulated lock-in on the transverse (Vxy, Hall) contact pair.

Reads the Hall voltage. This unit is a slave: it shares the reference of
the XX oscillator, so changing its ``amplitude`` does not change the
current through the sample.

The measured Hall voltage carries a fraction of Vxx, because the Hall
probes are never exactly opposite one another. That admixture is even in
magnetic field while the Hall signal is odd, so

    Rxy_true(B) = [Rxy(+B) - Rxy(-B)] / 2

removes it exactly and nothing else does. A Hall density extracted without
symmetrising is wrong by that fraction times the aspect ratio, which is not
a small number.

Part of the simulated rig — see ``docs/SIMULATED_RIG.md``.
"""

from unisweep.sim.lockin import SimLockinBase


class SimLockinXY(SimLockinBase):

    CHANNEL = "xy"
    MODEL = "SIM-LIA-XY"

    def __init__(self, adress='SIM::LOCKIN::XY'):
        super().__init__(adress=adress)

        self.set_options = ['amplitude', 'frequency', 'time_constant',
                            'sensitivity', 'phase']
        self.sweepable = [False, False, False, False, False]
        self.eps = [1e-05, 0.001, None, None, 0.01]

        self.get_options = ['x', 'y', 'r', 'Θ', 'amplitude', 'frequency',
                            'time_constant', 'sensitivity', 'phase',
                            'excitation_current']

        self.loggable = ['IDN', 'amplitude', 'frequency', 'time_constant',
                         'sensitivity', 'phase', 'channel']

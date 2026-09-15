"""Simulated lock-in on the longitudinal (Vxx) contact pair.

This is the unit whose oscillator drives the sample: the excitation current
is ``amplitude / 1e6`` A, so the default 0.1 V gives 100 nA. Raising the
amplitude improves signal-to-noise and eventually heats the sample.

``x`` is the voltage across the Vxx probes; dividing by the excitation
current gives Rxx. The lab profile does that as a derived channel.

Part of the simulated rig — see ``docs/SIMULATED_RIG.md``.
"""

from unisweep.sim.lockin import SimLockinBase


class SimLockinXX(SimLockinBase):

    CHANNEL = "xx"
    MODEL = "SIM-LIA-XX"

    def __init__(self, adress='SIM::LOCKIN::XX'):
        super().__init__(adress=adress)

        self.set_options = ['amplitude', 'frequency', 'time_constant',
                            'sensitivity', 'phase']
        self.sweepable = [False, False, False, False, False]
        self.eps = [1e-05, 0.001, None, None, 0.01]

        self.get_options = ['x', 'y', 'r', 'Θ', 'amplitude', 'frequency',
                            'time_constant', 'sensitivity', 'phase',
                            'excitation_current']

        self.loggable = ['IDN', 'amplitude', 'frequency', 'time_constant',
                         'sensitivity', 'phase', 'excitation_current',
                         'channel']

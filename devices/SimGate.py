"""Simulated back-gate source-measure unit for the graphene Hall bar rig.

Sources a gate voltage and measures the leakage current through the oxide.
The leakage is not decorative: it grows exponentially with |Vg|, passes a
nanoamp somewhere above 50 V, and beyond the breakdown voltage the oxide is
destroyed — permanently, for the life of the process. That is what the
lab profile's ``min``/``max`` on this parameter, and the per-point script
idiom

    if abs(reads["SIM::GATE.current"]) > 2e-9: stop()

are for.

Part of the simulated rig — see ``docs/SIMULATED_RIG.md``.
"""

from unisweep.sim.rig import rig


class SimGate:

    def __init__(self, adress='SIM::GATE'):
        self.adress = adress
        self.address = adress
        self.rig = rig()

        self.set_options = ['voltage', 'compliance_current']
        self.sweepable = [False, False]
        self.eps = [0.001, None]

        self.get_options = ['voltage', 'current', 'compliance_current']

        self.loggable = ['IDN', 'compliance_current']

    def IDN(self):
        return 'UNISWEEP,SimGate,SIM-SMU,2.0'

    # ---- readback --------------------------------------------------------
    def voltage(self):
        return self.rig.gate_voltage()

    def current(self):
        """Gate leakage, A. Clamped at the compliance setting."""
        return self.rig.gate_current()

    def compliance_current(self):
        return self.rig.gate_compliance()

    # ---- commands --------------------------------------------------------
    def set_voltage(self, value, speed=None):
        self.rig.set_gate_voltage(value)

    def set_compliance_current(self, value):
        self.rig.set_gate_compliance(value)

    def to_zero(self, *args, **kwargs):
        self.rig.set_gate_voltage(0.0)

    def set_to_zero(self, *args, **kwargs):
        self.to_zero()

    def close(self):
        return

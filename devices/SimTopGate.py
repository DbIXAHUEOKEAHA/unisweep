"""Simulated top-gate source-measure unit for a dual-gated device.

Only meaningful when the sample actually has a top gate
(``top_gate_thickness_nm`` non-zero in ``config/sim_rig.json``). On a
single-gated device this driver connects and reads zero leakage, and
setting its voltage changes nothing — which is the honest behaviour, since
that is a device property and not something the instrument can know.

With a top gate present, the two gates together set two independent
quantities: the carrier density, which follows their weighted sum, and the
out-of-plane displacement field, which follows their weighted difference.
Sweeping one while holding the other therefore mixes n and D, and the
usual way round that is to sweep along lines of constant D — which is a
condition on the sweep page, not a feature of this driver.

The same safety rule applies to this dielectric as to the back gate, and
it is stricter: a top gate is usually thin hBN, so ±10 V is already a
large field. See the notes in the lab profile.

Part of the simulated rig — see ``docs/SIMULATED_RIG.md``.
"""

from unisweep.sim.rig import rig


class SimTopGate:

    def __init__(self, adress='SIM::TOPGATE'):
        self.adress = adress
        self.address = adress
        self.rig = rig()

        self.set_options = ['voltage', 'compliance_current']
        self.sweepable = [False, False]
        self.eps = [0.001, None]

        self.get_options = ['voltage', 'current', 'compliance_current',
                            'displacement_field']

        self.loggable = ['IDN', 'compliance_current']

    def IDN(self):
        return 'UNISWEEP,SimTopGate,SIM-SMU,2.0'

    # ---- readback --------------------------------------------------------
    def voltage(self):
        return self.rig.top_gate_voltage()

    def current(self):
        """Leakage through the top dielectric, A."""
        return self.rig.top_gate_current()

    def compliance_current(self):
        return self.rig.top_gate_compliance()

    def displacement_field(self):
        """D/eps0 in V/nm, from both gates. Zero without a top gate.

        A convenience readout, not something a real SMU would give you —
        on the bench you compute it from the two gate voltages and the two
        capacitances.
        """
        return self.rig.displacement_field()

    # ---- commands --------------------------------------------------------
    def set_voltage(self, value, speed=None):
        self.rig.set_top_gate_voltage(value)

    def set_compliance_current(self, value):
        self.rig.set_top_gate_compliance(value)

    def to_zero(self, *args, **kwargs):
        self.rig.set_top_gate_voltage(0.0)

    def set_to_zero(self, *args, **kwargs):
        self.to_zero()

    def close(self):
        return

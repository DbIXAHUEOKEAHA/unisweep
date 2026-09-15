"""Simulated DC source-measure unit across the graphene Hall bar.

Two-probe, source-drain. Use it for I-V curves and for bias-dependent
measurements; use the lock-ins for anything where the contact resistance
would get in the way.

Two things it will teach whoever reads it carefully:

* the voltage here is a **two-probe** voltage and includes both contacts,
  so it is larger than the four-probe Vxx implies. The difference is the
  contact resistance, which is how you measure it;
* the sample heats. Power dissipated in the channel raises the electron
  temperature by ``P * 1e4 K/W``, so at a milliamp the graphene is tens of
  kelvin above whatever the cryostat thermometer says. An I-V taken too
  hard is an I-V of a hotter sample, and it will look non-linear for a
  reason that has nothing to do with the physics being sought.

Part of the simulated rig — see ``docs/SIMULATED_RIG.md``.
"""

from unisweep.sim.rig import rig


class SimSMU:

    def __init__(self, adress='SIM::SMU'):
        self.adress = adress
        self.address = adress
        self.rig = rig()

        self.set_options = ['source_current', 'source_voltage',
                            'compliance_voltage', 'NPLC']
        self.sweepable = [False, False, False, False]
        self.eps = [1e-12, 1e-06, None, None]

        self.get_options = ['current', 'voltage', 'resistance',
                            'source_current', 'compliance_voltage', 'NPLC']

        self.loggable = ['IDN', 'compliance_voltage', 'NPLC']

    def IDN(self):
        return 'UNISWEEP,SimSMU,SIM-DC,2.0'

    # ---- readback --------------------------------------------------------
    def current(self):
        return self.rig.bias_current()

    def voltage(self):
        """Two-probe voltage across the device, contacts included."""
        return self.rig.bias_voltage()

    def resistance(self):
        return self.rig.bias_resistance()

    def source_current(self):
        return self.rig.bias_current()

    def compliance_voltage(self):
        return self.rig.bias_compliance_voltage()

    def NPLC(self):
        return self.rig.nplc()

    # ---- commands --------------------------------------------------------
    def set_source_current(self, value, speed=None):
        self.rig.set_bias_current(value)

    def set_source_voltage(self, value, speed=None):
        self.rig.set_bias_voltage(value)

    def set_compliance_voltage(self, value):
        self.rig.set_bias_compliance_voltage(value)

    def set_NPLC(self, value):
        self.rig.set_nplc(value)

    def to_zero(self, *args, **kwargs):
        self.rig.set_bias_current(0.0)

    def set_to_zero(self, *args, **kwargs):
        self.to_zero()

    def close(self):
        return

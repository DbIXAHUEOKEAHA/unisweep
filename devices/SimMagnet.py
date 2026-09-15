"""Simulated superconducting magnet for the graphene Hall bar rig.

Behaves like the AMI-430 driver: ``set_field`` commands a ramp and returns
immediately, and ``field()`` reports wherever the magnet has actually got
to. A sweep that reads the field back therefore sees it moving, and a
program that assumes the setpoint was reached instantly will be wrong in
the way it would be wrong on a real magnet.

Part of the simulated rig — see ``docs/SIMULATED_RIG.md``. The physics
lives in ``unisweep.sim``; this file is only the instrument face.
"""

from unisweep.sim.rig import rig


class SimMagnet:

    def __init__(self, adress='SIM::MAGNET'):
        self.adress = adress
        self.address = adress
        self.rig = rig()

        self.set_options = ['field', 'ramp_rate']
        self.sweepable = [True, False]
        self.maxspeed = [0.1, None]
        self.eps = [0.0005, None]

        self.get_options = ['field', 'target_field', 'ramp_rate', 'state']

        self.loggable = ['IDN', 'ramp_rate', 'max_field']

    # ---- identity --------------------------------------------------------
    def IDN(self):
        return 'UNISWEEP,SimMagnet,SIM-9T,2.0'

    def max_field(self):
        return self.rig.MAX_FIELD_T

    # ---- readback --------------------------------------------------------
    def field(self):
        return self.rig.field()

    def target_field(self):
        return self.rig.field_target()

    def ramp_rate(self):
        return self.rig.field_rate()

    def state(self):
        """2 = holding at target, 1 = ramping (AMI-430 convention)."""
        return self.rig.magnet_state()

    # ---- commands --------------------------------------------------------
    def set_field(self, value, speed=None):
        self.rig.set_field(value, rate=speed)

    def set_ramp_rate(self, value):
        self.rig.set_field_rate(value)

    def to_zero(self, *args, **kwargs):
        self.rig.set_field(0.0)

    def set_to_zero(self, *args, **kwargs):
        self.to_zero()

    def close(self):
        return

"""Simulated sub-THz source for the graphene Hall bar rig.

A multiplier-chain-style source: settable output power, settable emission
frequency, and a shutter. The power monitor reports what leaves the
source, with about 1% of shot-to-shot scatter.

**There is no instrument on this rig that reports absorbed power.** That is
deliberate and it is not a gap: absorbed optical power is not measurable.
It is inferred by matching the photoresistance against the resistance drop
produced by a known DC Joule power, which is the whole reason that
calibration exists. Anything that handed the number over directly would
delete the measurement.

Which of these three knobs a real source actually exposes varies by source
— some give power, some only an attenuator, some are fixed-frequency with
a shutter and nothing else. Read this driver's own ``set_options`` and
``get_options`` rather than assuming; that list is the contract.

Part of the simulated rig — see ``docs/SIMULATED_RIG.md``.
"""

from unisweep.sim.rig import rig


class SimTHzSource:

    def __init__(self, adress='SIM::THZ'):
        self.adress = adress
        self.address = adress
        self.rig = rig()

        self.set_options = ['power', 'frequency', 'output']
        self.sweepable = [False, False, False]
        self.eps = [1e-09, 1000000.0, None]

        self.get_options = ['power', 'frequency', 'output', 'power_monitor',
                            'max_power']

        self.loggable = ['IDN', 'frequency', 'max_power']

    def IDN(self):
        return 'UNISWEEP,SimTHzSource,SIM-SUBTHZ,2.0'

    # ---- readback --------------------------------------------------------
    def power(self):
        """Commanded output power, W."""
        return self.rig.thz_power()

    def power_monitor(self):
        """What the source's own detector reads, W. Zero when shuttered."""
        return self.rig.thz_power_monitor()

    def frequency(self):
        return self.rig.thz_frequency()

    def output(self):
        """1 = shutter open, 0 = closed."""
        return self.rig.thz_output()

    def max_power(self):
        return self.rig.beam.max_source_power_W

    # ---- commands --------------------------------------------------------
    def set_power(self, value, speed=None):
        self.rig.set_thz_power(value)

    def set_frequency(self, value, speed=None):
        self.rig.set_thz_frequency(value)

    def set_output(self, value, speed=None):
        self.rig.set_thz_output(value)

    def to_zero(self, *args, **kwargs):
        self.rig.set_thz_output(0)
        self.rig.set_thz_power(0.0)

    def set_to_zero(self, *args, **kwargs):
        self.to_zero()

    def close(self):
        return

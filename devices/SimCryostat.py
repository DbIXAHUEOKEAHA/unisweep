"""Simulated variable-temperature cryostat for the graphene Hall bar rig.

The setpoint walks toward its target at the commanded rate, and the sample
lags the setpoint by a thermal time constant of about 18 s. Reading
``temperature`` immediately after setting it therefore returns the old
temperature, which is true of every cryostat ever built.

Part of the simulated rig — see ``docs/SIMULATED_RIG.md``.
"""

from unisweep.sim.rig import rig


class SimCryostat:

    def __init__(self, adress='SIM::CRYOSTAT'):
        self.adress = adress
        self.address = adress
        self.rig = rig()

        self.set_options = ['temperature']
        self.sweepable = [True]
        self.maxspeed = [2.0]
        self.eps = [0.05]

        self.get_options = ['temperature', 'setpoint', 'heater_power']

        self.loggable = ['IDN', 'setpoint']

    def IDN(self):
        return 'UNISWEEP,SimCryostat,SIM-VTI,2.0'

    # ---- readback --------------------------------------------------------
    def temperature(self):
        """Sample thermometer reading, K."""
        return self.rig.temperature()

    def setpoint(self):
        return self.rig.temperature_setpoint()

    def heater_power(self):
        return self.rig.heater_power()

    # ---- commands --------------------------------------------------------
    def set_temperature(self, value, speed=None):
        self.rig.set_temperature(value, rate=speed)

    def close(self):
        return

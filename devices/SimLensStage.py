"""Simulated XYZ stage carrying the final lens before the cryostat window.

Moving this stage steers the beam across the sample, which is what makes a
beam-scan map possible. Positions are in millimetres, as the motor
controllers report them.

The calibration this exists for: scan X and Y, record the photoresponse,
and put the lens at **the point of highest symmetry, not the point of
highest signal**. A stray reflection off the cryostat window adds a second,
weaker spot to the beam, and the sum of the two has its maximum pulled
away from the optical axis — by about 0.2 mm on this rig, which is over
half a spot size and around ten steps of an ordinary raster. Taking the
maximum of the map puts the lens in the wrong place and every optical
measurement afterwards inherits the error.

Focus Z before centring XY. Defocus widens the spot and flattens the map,
so a scan taken out of focus is both weaker and harder to centre — and
nothing will tell you that is what happened.

Part of the simulated rig — see ``docs/SIMULATED_RIG.md``.
"""

from unisweep.sim.rig import rig


class SimLensStage:

    def __init__(self, adress='SIM::LENS'):
        self.adress = adress
        self.address = adress
        self.rig = rig()

        self.set_options = ['x', 'y', 'z']
        self.sweepable = [False, False, False]
        self.eps = [0.001, 0.001, 0.001]

        self.get_options = ['x', 'y', 'z']

        self.loggable = ['IDN']

    def IDN(self):
        return 'UNISWEEP,SimLensStage,SIM-XYZ,2.0'

    # ---- readback --------------------------------------------------------
    def x(self):
        return self.rig.lens("x")

    def y(self):
        return self.rig.lens("y")

    def z(self):
        return self.rig.lens("z")

    # ---- commands --------------------------------------------------------
    def set_x(self, value, speed=None):
        self.rig.set_lens("x", value)

    def set_y(self, value, speed=None):
        self.rig.set_lens("y", value)

    def set_z(self, value, speed=None):
        self.rig.set_lens("z", value)

    def close(self):
        return

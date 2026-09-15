"""A simulated graphene Hall bar and the instruments that measure it.

Unisweep can drive this rig exactly as it drives real hardware: copy the
``Sim*.py`` files from ``devices/`` into ``resources/``, give each one an
address on the Devices page, and sweep. Nothing here opens a VISA session
or needs an instrument on the bench.

Two reasons it exists:

1. **A new installation has something to measure.** Clone Unisweep, start
   it, and you can take a real 2-D map on your first day with no hardware.
2. **An assistant can be trained and examined without risking a sample.**
   The rig knows the truth about itself (:meth:`SimRig.truth`) — the
   carrier density, the mobility, the Dirac point, whether the oxide has
   been destroyed — so a measurement of it can be *scored*, not merely
   admired.

See ``docs/SIMULATED_RIG.md``.
"""

from .graphene import GrapheneSample, PHYS
from .optics import BeamPath
from .rig import SimRig, SimFaults, rig, configure, reset

__all__ = ["GrapheneSample", "PHYS", "BeamPath", "SimRig", "SimFaults",
           "rig", "configure", "reset"]

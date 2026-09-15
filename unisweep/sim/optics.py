"""The THz beam path: a source, a lens on an XYZ stage, and a sample.

What this has to get right is not the optics — it is the *calibration
procedure*. The lens is positioned by scanning X and Y, recording the
photoresponse, and putting the lens at **the point of highest symmetry,
not the point of highest signal.** A map where those coincided would teach
the wrong lesson, so this one is built so that they do not.

Why they differ
---------------

A device only a few microns across cannot structure a sub-millimetre beam
at all — its map would simply be the beam profile, and the maximum would
be the right answer. What makes a real photoresponse map interesting is
the **antenna**: at sub-THz the coupling structure is wavelength-scale, a
few hundred microns, comparable to the spot. The map is then the antenna's
pattern smoothed by the beam, and a dipole or bowtie has two lobes
straddling the channel.

The lobes sit **symmetrically** about the device — geometry, set by
lithography. Their strengths are **not** equal — fabrication: a slightly
better contact on one arm, a little more absorber on the other. So:

* the **maximum** sits on the stronger lobe, off by most of a lobe spacing;
* the **intensity centroid** is dragged the same way, less far, still
  wrong;
* the **midpoint of the two lobe positions** is the device, exactly,
  because amplitude asymmetry cannot move where a lobe *is*.

That last one is what "highest symmetry" means in practice: find the
features, take their geometric centre, and keep their brightness out of
the arithmetic.

Defocus is modelled because it destroys exactly this: away from the waist
the spot grows, the two lobes blur into one, and the structure that made
the centre findable is gone. Focus in Z first, then centre in XY. The rig
will let it be done in the wrong order and will say nothing.

Positions are in millimetres, the units the stage controllers use.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict

__all__ = ["BeamPath"]


def _default_lobes() -> tuple:
    """A dipole antenna: two arms, symmetric in place, unequal in strength.

    0.90 mm tip to tip is about a half-wave dipole at 165 GHz, and a 40%
    imbalance is an ordinary difference between two fabricated arms. The
    spacing is a little over three spot sizes, so the two lobes are
    genuinely separable at focus — which is the whole point, since a map
    with one blob in it has no geometry to centre on.
    """
    return ((-0.45, 0.0, 1.00), (0.45, 0.0, 1.40))


@dataclass
class BeamPath:
    """Where the beam is, and how much of it the antenna funnels in."""

    # --- the truth the calibration is supposed to find --------------------
    axis_x_mm: float = 1.35
    axis_y_mm: float = -0.80
    focus_z_mm: float = 4.10
    """The device position and the beam waist. Deliberately not at the
    origin and not at round numbers, so a scan has to find them."""

    waist_mm: float = 0.28
    """Spot size at focus. Sub-THz beams are big — a few hundred microns —
    which here is a third of the antenna length, so the two lobes are
    resolved at focus and merge as soon as they are not."""
    rayleigh_mm: float = 2.2
    """Depth of focus. Defocus by this much and the spot has grown by
    sqrt(2), the lobes have merged, and the centre is no longer findable."""

    lobes: tuple = field(default_factory=_default_lobes)
    """``(dx_mm, dy_mm, amplitude)`` per antenna lobe, relative to the
    device. Positions symmetric, amplitudes not."""

    peak_coupling: float = 8.0e-3
    """Coupling scale: the fraction of the source's power reaching the
    sheet through one unit-amplitude lobe with the lens on it.

    A *bare* device a few microns across would collect only a few times
    1e-4 by area ratio, and the photoresponse that gives at base
    temperature is a fraction of a percent — real, but only reachable with
    a chopped beam and patient averaging. An antenna-coupled device gets
    close to a percent, which puts the electron temperature at full power
    in the tens of kelvin and makes it comparable with a temperature
    sweep. That is what turns the DC-power calibration into a measurement
    rather than a gesture. It is a per-device number."""

    max_source_power_W: float = 2.0e-3
    """2 mW is a reasonable sub-THz multiplier-chain output."""

    # ------------------------------------------------------------------
    def spot_size(self, z_mm: float) -> float:
        """Spot size at this stage height, mm."""
        u = (z_mm - self.focus_z_mm) / self.rayleigh_mm
        return self.waist_mm * math.sqrt(1.0 + u * u)

    def coupling(self, x_mm: float, y_mm: float, z_mm: float) -> float:
        """Fraction of the source power that lands on the sheet."""
        w = self.spot_size(z_mm)
        if w <= 0.0:
            return 0.0
        concentration = (self.waist_mm / w) ** 2
        dx = x_mm - self.axis_x_mm
        dy = y_mm - self.axis_y_mm
        total = 0.0
        for lx, ly, amplitude in self.lobes:
            rx, ry = dx - lx, dy - ly
            total += amplitude * math.exp(-(rx * rx + ry * ry)
                                          / (2.0 * w * w))
        return self.peak_coupling * concentration * total

    # ------------------------------------------------------------------
    # what the three ways of reading the map would give you
    # ------------------------------------------------------------------
    def _sample_map(self, span_mm: float, points: int, z_mm=None):
        z = self.focus_z_mm if z_mm is None else z_mm
        step = 2.0 * span_mm / (points - 1)
        grid = []
        for i in range(points):
            x = self.axis_x_mm - span_mm + i * step
            for j in range(points):
                y = self.axis_y_mm - span_mm + j * step
                grid.append((x, y, self.coupling(x, y, z)))
        return grid

    def argmax_offset(self, span_mm: float = 1.2, points: int = 161,
                      z_mm=None) -> float:
        """Error, in mm, from taking the brightest point of the map."""
        x, y, _ = max(self._sample_map(span_mm, points, z_mm),
                      key=lambda t: t[2])
        return math.hypot(x - self.axis_x_mm, y - self.axis_y_mm)

    def centroid_offset(self, span_mm: float = 1.2, points: int = 161,
                        z_mm=None) -> float:
        """Error from taking the intensity centroid — better than the
        maximum, still wrong, and wrong in the same direction."""
        grid = self._sample_map(span_mm, points, z_mm)
        total = sum(v for _, _, v in grid)
        if total <= 0.0:
            return float("inf")
        cx = sum(x * v for x, _, v in grid) / total
        cy = sum(y * v for _, y, v in grid) / total
        return math.hypot(cx - self.axis_x_mm, cy - self.axis_y_mm)

    def lobe_midpoint_offset(self) -> float:
        """Error from taking the geometric centre of the lobe positions —
        the rule the lab actually uses. Zero by construction, because
        amplitude asymmetry cannot move where a lobe is."""
        if not self.lobes:
            return 0.0
        cx = sum(lx for lx, _, _ in self.lobes) / len(self.lobes)
        cy = sum(ly for _, ly, _ in self.lobes) / len(self.lobes)
        return math.hypot(cx, cy)

    def lobe_spacing_mm(self) -> float:
        if len(self.lobes) < 2:
            return 0.0
        return max(math.hypot(a[0] - b[0], a[1] - b[1])
                   for a in self.lobes for b in self.lobes)

    def lobes_resolved(self, z_mm=None) -> bool:
        """Are the lobes still separable at this focus?

        Once the spot approaches the lobe spacing the map is one blob and
        there is no geometry left to centre on.
        """
        if len(self.lobes) < 2:
            return False
        z = self.focus_z_mm if z_mm is None else z_mm
        return self.lobe_spacing_mm() > 1.8 * self.spot_size(z)

    def truth(self) -> dict:
        """The answer key for a beam-alignment exercise."""
        out = asdict(self)
        out["argmax_offset_mm"] = self.argmax_offset()
        out["centroid_offset_mm"] = self.centroid_offset()
        out["lobe_midpoint_offset_mm"] = self.lobe_midpoint_offset()
        out["lobe_spacing_mm"] = self.lobe_spacing_mm()
        out["lobes_resolved_at_focus"] = self.lobes_resolved()
        return out

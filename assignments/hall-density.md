# Carrier density at high doping

## Question
What is the carrier density of this device at the most negative gate voltage
you have established is safe, and how sure are you of it?

## Sample
Monolayer graphene Hall bar on 300 nm SiO2, back gate only, antenna-coupled
for sub-THz. It is cold. Neither its Dirac point nor its safe gate limit is
known — establishing them is part of the work.

## Constraints
- Establish the safe gate limit by the lab's leak-hunt procedure before
  putting the gate anywhere near it. The profile's range is what the hardware
  survives, not what this device tolerates.
- Symmetrise the Hall signal. The probes are misaligned and Rxy carries a
  fraction of Rxx.
- Keep the excitation where the electrons are still at the bath temperature,
  and say how you know they are.

## Acceptance
- field_span >= 1.8 — a slope needs at least +-0.9 T to be a slope
- points >= 150 — enough curve to fit rather than to guess
- stopped == 0 — no run that was aborted may be cited as evidence
- density_uncertainty <= 0.05 — 5% or better, and say how you arrived at it

## Deliverables
- The carrier density with an uncertainty, and the gate voltage it is at.
- The safe gate limit you established, and how you decided it.
- A journal note recording both.

## Notes
Report the density as `value` and its fractional uncertainty as evidence
`density_uncertainty`. Everything else in the criteria is read out of the runs
you cite, so cite the ones the claim actually rests on.

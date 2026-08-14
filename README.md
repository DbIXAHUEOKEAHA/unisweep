# Unisweep

**N-dimensional instrument sweeps for the physics lab.** Point it at your
instruments, define a 1-D, 2-D, or 3-D parameter sweep, and watch maps
build line by line — with self-installing drivers, live-editable sweeps,
and a measurement engine built to survive a flaky voltmeter at 3 a.m.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

Unisweep grew up in a condensed-matter lab running cryostats, magnets,
lock-ins, and source-meters through years of real measurements. It is the
tool we use every day — released so other labs don't have to build the
same thing again.

---

## What it does

* **1-D / 2-D / 3-D sweeps** of any instrument parameter against any
  others — gate maps, field maps, temperature stacks — with per-axis
  rates, delays, walk counts (back-and-forth with separate return rates),
  snake mode, and manual step files for non-uniform grids.
* **Live-editable while running**: retune limits, rates, delays, walk
  counts, even hot-swap a manual step table mid-sweep. The engine picks up
  every change at the next step boundary — no restart, no lost data.
* **Region conditions**: restrict a 2-D/3-D sweep to an arbitrary region
  (`x + y <= 2.4`, elliptic cuts, …) evaluated per point, or couple axes
  through an equality solved on the fly. Excluded points become clean NaN
  holes in the maps.
* **Self-ramping instruments** (magnet supplies, temperature controllers)
  are first-class: sweeps approach their start point, ramp at your rate,
  log the readback, retarget live — protected by a stall watchdog that
  warns and then stops the sweep, naming the instrument, if a ramp dies.
  A built-in **sweep-capability test** verifies empirically that a device
  really goes where it's told.
* **Fault-tolerant by design**: a read instrument returning NaN, throwing
  errors, or throttling for seconds delays nothing and kills nothing —
  its column records NaN and the sweep continues. Only a fault on a
  device the sweep *depends on* stops the run, with a warning window
  naming it. All of this is covered by an automated fault-injection test
  suite.

## Data you can use immediately

* **CSV per scan** with time, every axis value, and every read parameter —
  file names carry the outer-loop values, rotating per master point.
* **Map worksheets**, built exactly like the classic mapper: the header is
  the walk-concatenated inner grid, one line appended per outer point,
  interpolated segment-by-segment so forward/backward hysteresis is
  preserved and NaN holes are never smeared. PNG mirrors and 3-D GIF
  stacks render in the background.
* **Or a single XYZ long-format file** per read parameter — one row per
  measured point, raw coordinates, ready for Origin, gnuplot, or
  `pandas.read_csv`. A 3-D sweep stays in one file.
* **Live plots on demand**: spawn any number of independent line and map
  windows before or during a sweep; maps render the same walk-aware
  matrices as the worksheets (never re-binned scatter), with a plane
  selector for 3-D stacks. A latest-readings table always shows the last
  measured row.

## A driver library that installs itself

The core ships separate from the instrument drivers. Assign an instrument
to an address and Unisweep **fetches the driver from this repository and
pip-installs its Python dependencies** — including vendored SDKs
(attocube, libximc, Rohde & Schwarz) extracted automatically. The catalog
refreshes itself from GitHub at every start, so a driver pushed here
appears in everyone's dropdown; with no connection, the cached catalog and
installed drivers keep working. Import failures show on the device row
with a one-click **Fix**, and every working import→pip recipe is recorded
permanently in a self-learning dependency map.

**Supported out of the box** (40+ drivers in [`devices/`](devices)):

| Family | Instruments |
| --- | --- |
| Source / measure | Keithley 2400, 2600B series, 2000, 2182; SRS SIM900/SIM928 |
| Lock-ins & preamps | SRS SR830, SR860, current preamplifier; Lake Shore M81 family |
| Temperature & cryo | Lake Shore 336, Oxford MercuryiTC/iPS, attocube attoDRY 800/2100, Quantum Design OptiCool, Thorlabs TC300 |
| Magnets | AMI 430, Oxford MercuryiPS, vector operation |
| Positioners | attocube ANC300/ANC350/AMC, Standa 8MT stages, Thorlabs KDC101/KSC101 |
| Scopes, VNA, DAQ | Teledyne LeCroy WaveRunner, Rohde & Schwarz VNA, NI-DAQmx, Rigol DG800, Tektronix AFG1000, Avantes AvaSpec |

## Quick start

```bash
git clone https://github.com/DbIXAHUEOKEAHA/unisweep.git
cd unisweep
pip install numpy scipy pandas matplotlib
python main.py
```

First launch opens a setup wizard: scan for instruments (VISA + serial),
pick what answers on each address, confirm — drivers and their Python
packages install themselves. Then choose a sweep dimension, set the axes,
tick the parameters to read, and **Start**.

No instruments handy? The virtual `Time` device works everywhere, and the
test suite's mock instruments demonstrate every feature offline.

## Writing a driver

A driver is one Python file with a duck-typed class — no framework, no
registration:

```python
class MyInstrument:
    def __init__(self, adress):
        self.set_options = ["Volt"]          # settable parameters
        self.get_options = ["Volt", "Curr"]  # readable parameters
        self.sweepable   = [True]            # optional: ramps by itself
        self.eps         = [1e-4]            # optional: arrival tolerance
        self.maxspeed    = [0.5]             # optional: rate ceiling

    def Volt(self): ...                      # read
    def set_Volt(self, value, speed=None): ...  # write (speed for ramps)
```

Drop it in `devices/`, open a pull request, and every Unisweep
installation discovers it at the next catalog refresh. That's the whole
contribution pipeline.

## Reliability

The measurement engine is covered by 50+ automated tests: endpoint
correctness, live-edit semantics, condition regions, map row logic
(hysteresis, NaN holes, uniform/non-uniform grids), sweepable-device
behaviour (approach, stall, overshoot, retargeting), and realistic fault
injection — instruments that hang, spit NaN, or die mid-sweep. A GUI
smoke harness clicks every control on a cold-started app and fails on any
unhandled exception.

## License

MIT — use it, modify it, ship it. If Unisweep produced data in your
paper, an acknowledgement is appreciated.

---

*Built at the National University of Singapore by Mikhail Kravtsov.
Issues and pull requests welcome — especially new drivers.*

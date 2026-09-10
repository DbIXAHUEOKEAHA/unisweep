# Reads that are a whole trace

A VNA returns a sweep of its own at every point. So does a scope, a
spectrum analyser, a lock-in in buffered mode. Unisweep now recognises
that on its own and gives such a read maps of its own.

The whole feature is one rule:

> **The trace becomes the innermost axis, and every sweep axis shifts out
> by one.**

Everything below follows from it.

| you ran | the trace-valued read becomes | files |
|---|---|---|
| a **1-D** sweep | a map — x is the trace's axis, y is the swept parameter | the worksheet a 2-D sweep of numbers writes |
| a **2-D** sweep | a *set* of maps, one per master point, with the toggle to step through them | the layout a 3-D sweep of numbers writes |
| a **3-D** sweep | one dimension past anything that can be drawn: the screen falls back to the first element of each trace | a fourth level — folder per master, folder per slave, an index per level |

Ordinary reads in the same sweep are untouched.

## Nothing has to be declared

Detection is by shape. A driver whose getter returns a list or a numpy
array is understood with no profile, no flag, no code change; so is the
comma-joined string most drivers produce today, because that is what they
produce today.

Deliberately strict, because the cost of a false positive is a column
that silently becomes a map: text is only a trace when **every** token
parses as a number and there are at least two of them. `"open"`,
`"1 error"` and `"3.5"` are readings, not traces. A driver returning
`[x]` is reporting one number in a box.

```python
def Trace(self):                     # the fast path: no string at all
    return self.visa.query_binary_values("CALC:DATA? SDAT",
                                         datatype="d", is_big_endian=False)
```

That is also the answer to *is there a faster way than joining floats into
a string*: the join was never the expensive part — the instrument's ASCII
formatting is. Ask for a binary block (`FORM:DATA REAL,64` and
`query_binary_values`) and hand Unisweep the array. You save the
instrument-side formatting, both parses, and every digit `repr` would have
dropped.

## The trace's own x axis

In precedence order:

1. **the lab profile**, when it states one;
2. **the driver**, through a companion getter — `Trace` is paired with
   `Trace_axis` — read **once per run**, not once per point, the same
   shape of agreement as `loggable`;
3. **the index** 0…N-1, which is honest about knowing nothing.

```jsonc
"parameters": {
  "Trace": {
    "vector": true,               // "auto" (default), true, false
    "vector_axis": "Trace_axis",  // a getter name, or a list of values
    "axis_name": "frequency",
    "axis_unit": "Hz"
  }
}
```
`vector: false` is the way to tell Unisweep that a reading which *looks*
like a trace is not one.

## What lands on disk

**The per-point CSV is unchanged.** One cell per read, the trace as
comma-separated numbers, exactly as before — every script already pointed
at those files keeps working. The full-precision copy lives in the map
tables beside it.

The maps go where every map goes, under `<YYMMDD>/2d_maps/`:

```
1-D   tables/<base>_<i>/<i>_<read>_map.csv
2-D   tables/<base>_<i>/<axis1>_<value>/<i>_<read>_map_<n>.csv
3-D   tables/<base>_<i>/<axis1>_<v1>/<axis2>_<v2>/<i>_<read>_map_<n>_<m>.csv
```

with `images/` mirroring `tables/` file for file, as always. The header
row is the trace's axis; the first column of each row is the sweep point
that produced it. Rows are in measurement order — there is nothing to
interpolate onto a grid, because the instrument returned the whole line
at once, already aligned.

With `map_style` set to `xyz`, the long format gains the trace axis as one
more coordinate column: `<sweep axes>,<trace axis>,<read>`, one line per
point of every trace. That is what the format means, and it is why it is
not the default for a read that returns a thousand numbers at a time.

## When the trace changes length

The first trace of a run fixes that read's length and axis for the whole
run — a map whose rows changed width halfway through would not be a map.
Later traces are padded with NaN or truncated to fit, and the change is
reported **once**. Someone retuning the span at 3 a.m. costs a warning,
not the night's data, and the NaN is visible in a way a silently reshaped
grid would not be.

## Cost

A 1601-point trace at 10 000 sweep points is 128 MB of float64. The
files are streamed, and the live map holds the rows it is shown; a long
run with several traced reads is worth thinking about before it is worth
starting.

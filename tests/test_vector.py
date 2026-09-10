"""Recognising a reading that is a whole trace.

The risk here is not failing to notice a trace — it is deciding that
something is a trace when it is not, because that silently reshapes a
column somebody has been recording for months.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from unisweep.core.vector import (MAX_LENGTH, VectorSpec, as_vector,
                                  axis_getter_name, fit_to_length,
                                  resolve_axis, vector_text)


# ---------------------------------------------------------------------------
# what is a trace
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("value", [
    1.0, 0, -3, True, np.float64(2.5), np.int32(7), None,
])
def test_a_number_is_not_a_trace(value):
    assert as_vector(value) is None


@pytest.mark.parametrize("value", [
    "", "  ", "open", "1 error", "nan", "3.5", "off,",
    "1,2,oops", "not,a,number",
])
def test_text_that_is_not_a_row_of_numbers_is_not_a_trace(value):
    """A reading that is a word with a comma in it is a reading with a
    problem, not a trace. Guessing otherwise reshapes real data."""
    assert as_vector(value) is None


def test_the_legacy_comma_string_is_understood():
    """What the drivers produce today, unchanged."""
    trace = as_vector("1.0,2.5,-3e-4")
    assert trace is not None
    assert np.allclose(trace, [1.0, 2.5, -3e-4])


@pytest.mark.parametrize("text,expected", [
    ("1;2;3", [1, 2, 3]),
    ("1\t2\t3", [1, 2, 3]),
    ("1 2 3", [1, 2, 3]),
    ("[1, 2, 3]", [1, 2, 3]),
    ("1,2,nan", [1, 2, np.nan]),
])
def test_the_shapes_instruments_actually_send(text, expected):
    trace = as_vector(text)
    assert trace is not None
    assert np.allclose(trace, expected, equal_nan=True)


def test_a_list_or_array_needs_no_string_at_all():
    """The point of the exercise: a driver can hand over the numbers."""
    for value in ([1.0, 2.0, 3.0], (1.0, 2.0, 3.0),
                  np.array([1.0, 2.0, 3.0])):
        trace = as_vector(value)
        assert trace is not None and trace.dtype == float
        assert np.allclose(trace, [1, 2, 3])


def test_a_two_dimensional_reading_is_flattened_not_refused():
    trace = as_vector(np.array([[1.0, 2.0], [3.0, 4.0]]))
    assert np.allclose(trace, [1, 2, 3, 4])


def test_one_number_in_a_box_is_still_one_number():
    """A driver returning [x] is reporting a scalar, and a column that
    turned into a map because of it would be a nasty surprise."""
    assert as_vector([2.0]) is None
    assert as_vector(np.array([2.0])) is None


def test_the_profile_can_settle_an_ambiguous_reading():
    assert as_vector([2.0], force="always") is not None
    assert as_vector("1,2,3", force="never") is None
    assert as_vector(2.0, force="always") is not None
    assert len(as_vector("3.5", force="always")) == 1


def test_an_absurd_length_is_capped_rather_than_allocated():
    assert len(as_vector(np.zeros(MAX_LENGTH + 10))) == MAX_LENGTH


# ---------------------------------------------------------------------------
# the on-disk form
# ---------------------------------------------------------------------------
def test_the_cell_text_round_trips():
    original = np.array([1.0, -2.5e-7, np.nan, 3.0])
    text = vector_text(original)
    assert text == "1,-2.5e-07,nan,3"
    assert np.allclose(as_vector(text), original, equal_nan=True)


def test_the_cell_text_keeps_more_digits_than_the_screen_does():
    assert vector_text([1.234567891234]) == "1.234567891"


# ---------------------------------------------------------------------------
# length changes
# ---------------------------------------------------------------------------
def test_a_shorter_trace_is_padded_and_a_longer_one_is_cut():
    assert np.allclose(fit_to_length([1, 2], 4), [1, 2, np.nan, np.nan],
                       equal_nan=True)
    assert np.allclose(fit_to_length([1, 2, 3, 4], 2), [1, 2])
    assert np.allclose(fit_to_length([1, 2], 2), [1, 2])


# ---------------------------------------------------------------------------
# where the x axis comes from
# ---------------------------------------------------------------------------
class Driver:
    def __init__(self, axis=None, name="Trace_axis"):
        self.get_options = ["Trace"]
        if axis is not None:
            setattr(self, name, lambda: axis)


class Adapter:
    def __init__(self, raw):
        self.raw = raw


def test_without_help_the_axis_is_the_index():
    spec = resolve_axis("VNA.Trace", 4)
    assert spec.source == "index"
    assert np.allclose(spec.axis, [0, 1, 2, 3])
    assert spec.axis_name == "index"


def test_the_driver_can_report_its_own_axis():
    """``Trace`` is paired with ``Trace_axis`` — the same shape of
    agreement as ``loggable``: have the attribute and you are asked."""
    assert axis_getter_name("Trace") == "Trace_axis"
    adapter = Adapter(Driver(axis=[1e9, 2e9, 3e9]))
    spec = resolve_axis("VNA.Trace", 3, adapter=adapter)
    assert spec.source == "driver"
    assert np.allclose(spec.axis, [1e9, 2e9, 3e9])


def test_the_profile_wins_over_the_driver():
    class Spec:
        vector_axis = [10.0, 20.0, 30.0]
        axis_name = "frequency"
        axis_unit = "Hz"
    adapter = Adapter(Driver(axis=[1e9, 2e9, 3e9]))
    spec = resolve_axis("VNA.Trace", 3, adapter=adapter, spec=Spec())
    assert spec.source == "profile"
    assert np.allclose(spec.axis, [10, 20, 30])
    assert spec.axis_label == "frequency (Hz)"


def test_the_profile_can_name_the_getter_instead_of_the_values():
    class Spec:
        vector_axis = "frequencies"
        axis_name = "f"
        axis_unit = "GHz"
    adapter = Adapter(Driver(axis=[1, 2, 3], name="frequencies"))
    spec = resolve_axis("VNA.Trace", 3, adapter=adapter, spec=Spec())
    assert spec.source == "driver"
    assert np.allclose(spec.axis, [1, 2, 3])
    assert spec.axis_name == "f"


def test_an_axis_that_does_not_match_its_own_trace_is_fitted():
    adapter = Adapter(Driver(axis=[1.0, 2.0]))
    spec = resolve_axis("VNA.Trace", 4, adapter=adapter)
    assert len(spec.axis) == 4
    assert np.isnan(spec.axis[-1])


def test_an_axis_getter_that_raises_costs_the_axis_not_the_run():
    class Hostile:
        get_options = ["Trace"]

        def Trace_axis(self):
            raise IOError("instrument on fire")

    spec = resolve_axis("VNA.Trace", 3, adapter=Adapter(Hostile()))
    assert spec.source == "index"
    assert np.allclose(spec.axis, [0, 1, 2])


# ---------------------------------------------------------------------------
# the shapes a real instrument sends
# ---------------------------------------------------------------------------
def test_the_rohde_schwarz_trace_parses_as_it_arrives():
    """``CALC1:DATA? FDAT`` with the whitespace stripped, which is exactly
    what devices/Vna.py returns today. No driver change required."""
    answer = "1.0000E-01,2.0000E-01,-3.5000E-02,4.1E-01"
    assert np.allclose(as_vector(answer), [0.1, 0.2, -0.035, 0.41])


def test_a_numpy_abbreviated_list_is_refused_rather_than_half_read():
    """``np.array2string`` abbreviates anything longer than 1000 points:

        1.000000e+09,1.000625e+09,...,2.000000e+09

    A frequency list with a hole in it. Reading the visible half would be
    worse than not reading it — a trace drawn against three-quarters of
    an axis looks fine and is wrong — so this stays a non-trace and the
    map falls back to the honest 0…N-1 index.
    """
    abbreviated = ",".join(["1.0e+09", "1.000625e+09", "...", "2.0e+09"])
    assert as_vector(abbreviated) is None


def test_a_long_axis_built_by_hand_survives_the_round_trip():
    axis = np.linspace(1e9, 2e9, 1601)
    text = ",".join(f"{v:.10g}" for v in axis)
    assert np.allclose(as_vector(text), axis)


def test_the_shipped_vna_driver_still_offers_what_unisweep_asks_for():
    """A source check, because importing the driver needs the vendor
    package. Two things must hold: the frequency list is not built with
    the abbreviating call, and the trace reads have the companion axis
    getters that put real frequencies under a map.
    """
    import ast as _ast
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(here, "devices", "Vna.py")
    if not os.path.exists(path):
        pytest.skip("the driver library is not in this checkout")
    tree = _ast.parse(open(path, encoding="utf-8").read())
    vna = next((n for n in _ast.walk(tree)
                if isinstance(n, _ast.ClassDef) and n.name == "Vna"), None)
    assert vna is not None, "the Vna class moved"
    methods = {n.name: n for n in vna.body
               if isinstance(n, _ast.FunctionDef)}
    for name in ("trace_real_axis", "trace_im_axis", "frequency_axis"):
        assert name in methods, f"{name} is how the map gets its x axis"
    for name in ("freqs", "frequency_axis"):
        calls = [n for n in _ast.walk(methods[name])
                 if isinstance(n, _ast.Call)
                 and getattr(n.func, "attr", "") == "array2string"]
        assert not calls, (f"{name} builds the frequency list with "
                           f"array2string, which abbreviates past 1000 "
                           f"points")

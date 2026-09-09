"""Figures rendered on the server, from the snapshot the rig pushed.

The measurement computer does not draw anything for Telegram: it sends a
decimated copy of what it is holding and this module draws it.  That keeps
matplotlib off the instrument PC's critical path, and it means a picture
can be produced for a chat at any moment without asking the rig for
anything.

Two figures cover what the request asked for:

* :func:`render_trace` — a read parameter along the **fast (innermost)
  axis**, which is the one plot that answers "is the measurement still
  sane?" at a glance;
* :func:`render_map` — a read parameter over the 2-D grid, the same
  ``viridis`` picture the application's own map window shows, so the phone
  and the screen in the lab never disagree.

Everything uses the object API (``Figure`` + ``FigureCanvasAgg``) rather
than ``pyplot``: no global figure state, so these can safely be called
from a worker thread.
"""

from __future__ import annotations

import io
import logging
import math
from typing import Optional, Sequence

import matplotlib
matplotlib.use("Agg")                                  # noqa: E402

import numpy as np                                     # noqa: E402
from matplotlib.backends.backend_agg import FigureCanvasAgg   # noqa: E402
from matplotlib.figure import Figure                   # noqa: E402
from matplotlib.ticker import ScalarFormatter          # noqa: E402

logger = logging.getLogger(__name__)

#: Categorical hues in fixed order — a series keeps its colour whatever
#: else is on the plot, and the order is never cycled.  Validated for
#: colour-vision deficiency on a light surface (adjacent pairs).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
          "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
MAX_SERIES = len(SERIES)

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#dedcd6"

#: perceptually uniform, monotone in lightness and colour-blind safe; it is
#: also what the desktop map window defaults to.  Used when the rig has not
#: said which scale its own map window is drawing with.
DEFAULT_CMAP = "viridis"


def known_cmap(name: str) -> str:
    """The rig's colour scale if matplotlib has one by that name.

    The desktop offers scales this module has never heard of, and will
    grow more; asking matplotlib is both shorter and always current than
    keeping a second list in step.  Anything unrecognised — an old
    snapshot, a typo in a saved template — quietly becomes the default
    rather than raising inside a render.
    """
    name = (name or "").strip()
    if not name:
        return DEFAULT_CMAP
    try:
        matplotlib.colormaps[name]                     # noqa: B018
        return name
    except (KeyError, ValueError, AttributeError):
        return DEFAULT_CMAP

#: Sized for a phone, not a paper.  Telegram shows a photo about 800 px
#: wide, so rendering larger costs bytes and buys nothing; the type sizes
#: below are chosen against *this* pixel count, not scaled down from a
#: print figure.
DPI = 100

#: Palette depth used when re-encoding (see :func:`_png`).  Line art is a
#: handful of flat colours and survives 48; a colormapped surface needs
#: more steps before banding shows on a smooth gradient.
COLORS_LINE = 48
COLORS_MAP = 192


# ---------------------------------------------------------------- style --
def _new_figure(width=8.0, height=4.6):
    fig = Figure(figsize=(width, height), dpi=DPI, facecolor=SURFACE)
    ax = fig.add_subplot(111)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
        ax.spines[side].set_linewidth(1.0)
    ax.tick_params(colors=INK_2, labelsize=11, length=3, width=1.0)
    ax.grid(True, color=GRID, linewidth=0.7, alpha=0.9)
    ax.set_axisbelow(True)
    return fig, ax


def _sci(ax):
    """Compact axis numbers — lab values span many decades."""
    for axis in (ax.xaxis, ax.yaxis):
        fmt = ScalarFormatter(useMathText=True)
        fmt.set_powerlimits((-3, 4))
        axis.set_major_formatter(fmt)
    ax.xaxis.get_offset_text().set_color(INK_2)
    ax.yaxis.get_offset_text().set_color(INK_2)


def _titles(ax, title: str, subtitle: str = "") -> None:
    """Heading left, data file right.

    Both go in matplotlib's title row rather than inside the axes: the
    scientific-notation offset (``×10⁻⁶``) also lives just above the
    top-left corner, and a subtitle drawn there lands on top of it.
    """
    ax.set_title(title, color=INK, fontsize=14, loc="left", pad=12)
    if subtitle:
        ax.set_title(subtitle, color=INK_2, fontsize=11, loc="right", pad=12)


def _png(fig, colors: int = COLORS_LINE) -> bytes:
    """Encode the figure as a small PNG.

    A plot is flat colour over a flat background — a handful of distinct
    values, not a photograph — so reducing the palette costs nothing
    visible and roughly quarters the file.  It stays PNG rather than
    becoming JPEG on purpose: JPEG puts ringing around thin lines and
    small text, which is most of what these pictures are.

    The octree method rather than median cut, which matters more than it
    sounds: median cut spends the whole palette on whatever dominates the
    frame, so on a map filled with a colour ramp the black title text
    lands on the nearest *green*, and the heading comes out speckled.
    Octree keeps the extremes and, here, also encodes smaller.

    Pillow ships with matplotlib, but if it is somehow missing the plain
    PNG goes out unchanged rather than nothing going out at all.
    """
    buf = io.BytesIO()
    FigureCanvasAgg(fig)
    fig.savefig(buf, format="png", facecolor=SURFACE,
                bbox_inches="tight", pad_inches=0.22)
    raw = buf.getvalue()
    try:
        from PIL import Image
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        small = image.quantize(colors=colors, method=Image.FASTOCTREE)
        out = io.BytesIO()
        small.save(out, format="PNG", optimize=True)
        packed = out.getvalue()
        return packed if len(packed) < len(raw) else raw
    except Exception as exc:                           # noqa: BLE001
        logger.debug("palette encoding skipped: %s", exc)
        return raw


def _clean(values) -> np.ndarray:
    out = np.asarray(values, dtype=float) if len(values) else np.array([])
    return out


def _finite(*arrays) -> bool:
    return all(a.size and np.isfinite(a).any() for a in arrays)


# --------------------------------------------------------------- traces --
def render_trace(trace: dict, reads: Sequence[str], title: str,
                 subtitle: str = "") -> Optional[bytes]:
    """One or more read parameters against the fast axis.

    A single series carries no legend — the title names it.  Two or more
    get a legend, because identity must never rest on colour alone.
    """
    if not trace:
        return None
    x = _clean(trace.get("x") or [])
    series = trace.get("series") or {}
    wanted = [r for r in reads if r in series][:MAX_SERIES]
    if not wanted or not x.size:
        return None

    fig, ax = _new_figure()
    drawn = 0
    for i, name in enumerate(wanted):
        y = _clean(series.get(name) or [])
        n = min(len(x), len(y))
        if n < 2:
            continue
        xs, ys = x[:n], y[:n]
        ok = np.isfinite(xs) & np.isfinite(ys)
        if ok.sum() < 2:
            continue
        # markers only while the walk is short enough to read them
        marker = "o" if ok.sum() <= 60 else None
        ax.plot(xs[ok], ys[ok], color=SERIES[i % MAX_SERIES], linewidth=1.8,
                marker=marker, markersize=3.4, label=name,
                solid_capstyle="round")
        drawn += 1
    if not drawn:
        return None

    ax.set_xlabel(trace.get("x_label") or "fast axis", color=INK_2,
                  fontsize=11)
    if drawn == 1:
        ax.set_ylabel(wanted[0], color=INK_2, fontsize=11)
    else:
        ax.set_ylabel("value", color=INK_2, fontsize=11)
        leg = ax.legend(loc="best", frameon=False, fontsize=11,
                        labelcolor=INK_2)
        for text in leg.get_texts():
            text.set_color(INK_2)
    _sci(ax)
    head = title or (f"{wanted[0]}  vs  "
                     f"{trace.get('x_label') or 'fast axis'}")
    _titles(ax, head, subtitle)
    return _png(fig)


# ----------------------------------------------------------------- maps --
def render_map(map_obj: dict, read: str, title: str, subtitle: str = "",
               cmap: str = DEFAULT_CMAP,
               vmin: float = None, vmax: float = None) -> Optional[bytes]:
    """A read parameter over the 2-D grid.

    ``grid`` is the inner-axis coordinate, ``rows`` the outer-axis value of
    each committed line, ``z`` the matrix — exactly the structure the
    application's own map windows consume, so nothing is re-binned here.
    """
    if not map_obj:
        return None
    grid = _clean(map_obj.get("grid") or [])
    rows = _clean(map_obj.get("rows") or [])
    z = map_obj.get("z") or []
    if not len(z) or not grid.size:
        return None
    z = np.array([[float("nan") if v is None else v for v in line]
                  for line in z], dtype=float)
    if z.ndim != 2 or z.size == 0:
        return None
    if rows.size != z.shape[0]:
        rows = np.arange(z.shape[0], dtype=float)
    if grid.size != z.shape[1]:
        grid = np.arange(z.shape[1], dtype=float)
    if not np.isfinite(z).any():
        return None

    fig, ax = _new_figure(width=8.0, height=5.0)
    ax.grid(False)
    cmap = known_cmap(cmap)
    # The first committed row of a 2-D sweep is a map one line tall, and
    # it is worth showing — but a mesh needs two rows to have a height,
    # so that line is drawn as a band around its own value.
    if z.shape[0] == 1:
        half = max(abs(float(rows[0])) * 1e-3, 0.5)
        rows = np.array([rows[0] - half, rows[0] + half])
        z = np.vstack([z, z])
    masked = np.ma.masked_invalid(z)
    mesh = ax.pcolormesh(grid, rows, masked, cmap=cmap, shading="nearest",
                         vmin=vmin, vmax=vmax)
    bar = fig.colorbar(mesh, ax=ax, pad=0.02)
    bar.set_label(read, color=INK_2, fontsize=11)
    bar.ax.tick_params(colors=INK_2, labelsize=10)
    bar.outline.set_edgecolor(GRID)

    ax.set_xlabel(map_obj.get("x_label") or "fast axis", color=INK_2,
                  fontsize=11)
    ax.set_ylabel(map_obj.get("y_label") or "slow axis", color=INK_2,
                  fontsize=11)
    _sci(ax)
    _titles(ax, title or read, subtitle)
    return _png(fig, COLORS_MAP)


# ------------------------------------------------------- what to render --
def auto_figure(snapshot: dict, read: str, title: str, subtitle: str = "",
                cmap: str = DEFAULT_CMAP) -> Optional[bytes]:
    """The picture that best represents this sweep right now.

    A 2-D or 3-D sweep with at least one committed map row is a map; a 1-D
    sweep (or a map that has no rows yet) is the fast-axis trace.
    """
    if not snapshot:
        return None
    maps = snapshot.get("maps") or {}
    if read in maps and (maps[read].get("z") or []):
        return render_map(maps[read], read, title, subtitle, cmap)
    return render_trace(snapshot.get("trace") or {}, [read], title, subtitle)


def readable_reads(snapshot: dict) -> list:
    if not snapshot:
        return []
    reads = list(snapshot.get("reads") or [])
    if reads:
        return reads
    trace = snapshot.get("trace") or {}
    return list((trace.get("series") or {}).keys())


def safe_render(fn, *args, **kwargs) -> Optional[bytes]:
    """Never let a plotting problem take a handler (or the ingest) down."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:                           # noqa: BLE001
        logger.warning("rendering failed: %s: %s", type(exc).__name__, exc)
        return None

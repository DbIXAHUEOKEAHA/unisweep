"""Filename helpers carried over from the legacy ``mapper.filename_utils``.

Kept verbatim in behaviour so file names produced by the new engine match the
old ones exactly (``cut`` rounding included).
"""

from __future__ import annotations

import numpy as np

__all__ = ["cut", "unify_filename", "fix_unicode"]


def cut(val: float, repeated: bool = False, flag: bool = False) -> str:
    """0.000427 -> '4.2', 3.953569 -> '4.0', -3.953569 -> '-4.0'."""
    neg_flag = flag if repeated else False
    if val < 0:
        val = abs(val)
        neg_flag = True
    elif val == 0 and not repeated:
        return "0.0"
    _int = divmod(val, 1)[0]
    _float = divmod(val, 1)[1] * 10
    if _int == 0.0:
        return cut(_float, repeated=True, flag=neg_flag)
    _float = round(_float)
    _int = round(_int)
    if _float == 10:
        _int += 1
        _float = 0
    return f"-{_int}.{_float}" if neg_flag else f"{_int}.{_float}"


_i1, _i2 = np.meshgrid(np.arange(0, 10), np.arange(0, 10))
_POSSIBILITIES = [f"{a}.{b}" for a, b in zip(_i1.flatten(), _i2.flatten())]


def unify_filename(filename: str, possibilities=_POSSIBILITIES) -> str:
    """Remove up to two embedded '_<d>.<d>' value tags from a filename."""
    for _ in range(2):
        match = next((num for num in possibilities if num in filename), None)
        if match is None:
            break
        head = filename[: filename.index(match)]
        tail = filename[filename.index(match) + len(match):]
        if "_" in head:
            head = head[: len(head) - head[::-1].index("_") - 1]
        filename = head + tail
    return filename


def fix_unicode(filename: str) -> str:
    if ":" in filename and ":\\" not in filename:
        filename = filename.replace(":", ":\\")
    return filename

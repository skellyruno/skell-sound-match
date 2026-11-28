"""Causal coefficient-rate mapping for native sound-match research.

Map each source tap's time to adjacent output samples. This preserves the
coefficient sum (DC gain) and zero-time taps, without adding negative time
support. It is not a bandlimited response-equivalent conversion or proof of
plugin realtime/latency parity. Verify actual native renders at each rate.
"""
from numbers import Integral
import numpy as np


def map_causal_kernel(kernel, source_rate: int, target_rate: int):
    """Map tap times along axis zero, preserving all channel dimensions."""
    if any(not isinstance(v, Integral) or isinstance(v, bool) or not 8000 <= v <= 192000
           for v in (source_rate, target_rate)):
        raise ValueError('sample rates must be integers from 8000 to 192000')
    h = np.asarray(kernel, dtype=np.float32)
    if not h.ndim or not len(h) or not np.isfinite(h).all():
        raise ValueError('kernel must contain finite causal taps')
    if source_rate == target_rate:
        return h.copy()
    idx = np.arange(len(h), dtype=np.float64) * target_rate / source_rate
    left = np.floor(idx).astype(np.int64)
    frac = (idx-left).astype(np.float32)
    out = np.zeros((left[-1]+2,) + h.shape[1:], dtype=np.float32)
    w = frac.reshape((-1,) + (1,)*(h.ndim-1))
    np.add.at(out, left, h*(1-w))
    np.add.at(out, left+1, h*w)
    if not np.isfinite(out).all():
        raise ValueError('mapped kernel is nonfinite')
    return out

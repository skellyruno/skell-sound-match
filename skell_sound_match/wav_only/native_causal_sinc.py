"""Bounded, causal tap-time mapping for offline native DSP research.

Preserves zero-time taps and per-channel DC coefficient sums. This is not
proof of bandlimited equivalence, host latency or real-time safety.
"""
from numbers import Integral
import numpy as np


def map_causal_sinc(kernel, source_rate, target_rate, radius=8):
    if any(not isinstance(v, Integral) or isinstance(v, bool) or not 8000 <= v <= 192000
           for v in (source_rate, target_rate)):
        raise ValueError('invalid sample rate')
    if not isinstance(radius, Integral) or isinstance(radius, bool) or not 2 <= radius <= 32:
        raise ValueError('radius must be an integer in [2, 32]')
    h = np.asarray(kernel, dtype=np.float32)
    if h.ndim == 0 or len(h) == 0 or not np.isfinite(h).all():
        raise ValueError('kernel must have finite taps')
    if source_rate == target_rate:
        return h.copy()
    pos = np.arange(len(h), dtype=np.float64) * target_rate / source_rate
    left = np.floor(pos).astype(np.int64)
    frac = pos - left
    offsets = np.arange(-radius + 1, radius + 1)
    indices = left[:, None] + offsets
    delta = frac[:, None] - offsets[None, :]
    weights = np.sinc(delta) * (.5 + .5 * np.cos(np.pi * np.clip(delta / radius, -1, 1)))
    weights[(indices < 0) | (np.abs(delta) >= radius)] = 0
    weights /= np.maximum(weights.sum(1, keepdims=True), 1e-9)
    out = np.zeros((int(left[-1] + radius + 1),) + h.shape[1:], dtype=np.float32)
    shape = (-1,) + (1,) * (h.ndim - 1)
    for k in range(len(offsets)):
        good = indices[:, k] >= 0
        np.add.at(out, indices[good, k], h[good] * weights[good, k].astype('f').reshape(shape))
    if not np.isfinite(out).all():
        raise ValueError('nonfinite mapped kernel')
    return out

"""Bounded normalized correlation for offline, training-only delay estimates.

The candidate must contain a symmetric radius of context around the reference
frame. Positive lag means the candidate is delayed at replay. No target data
or per-recording time index is required by the eventual fixed replay model.
"""
from numbers import Integral
import numpy as np


def estimate_lag(candidate, reference, radius):
    """Return (fractional lag in samples, signed peak correlation).

    Use three-point parabolic refinement when the correlation peak is interior.
    Silent frames return (0, 0); unreliable estimates should be downweighted.
    This does not establish that a time-varying delay is the correct DSP model.
    """
    if not isinstance(radius, Integral) or isinstance(radius, bool) or not 1 <= radius <= 128:
        raise ValueError('radius must be an integer in [1, 128]')
    x = np.asarray(candidate, dtype=np.float32)
    t = np.asarray(reference, dtype=np.float32)
    if (x.ndim != 1 or t.ndim != 1 or len(t) < 8
            or len(x) != len(t) + 2 * radius
            or not np.isfinite(x).all() or not np.isfinite(t).all()):
        raise ValueError('invalid paired mono frame or context')
    p = np.linalg.norm(t)
    if p <= 1e-8 or np.linalg.norm(x) <= 1e-8:
        return 0.0, 0.0
    lags = np.arange(-radius, radius + 1)
    scores = []
    for lag in lags:
        v = x[radius-lag:radius-lag+len(t)]
        scores.append(float(v @ t / max(np.linalg.norm(v) * p, 1e-10)))
    k = int(np.argmax(scores))
    lag = float(lags[k])
    if 0 < k < len(lags) - 1:
        a, b, c = scores[k-1:k+2]
        den = a - 2*b + c
        if den < -1e-6:
            lag += float(np.clip(.5*(a-c)/den, -.5, .5))
    return lag, scores[k]

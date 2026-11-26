"""Offline fixed-recipe causal residual replay; no reference or re-fitting required."""
import numpy as np
from scipy.signal import lfilter


def replay_residual(source, *, taps, coefficients, dynamic, scale):
    x = np.asarray(source, dtype=np.float32)
    if x.ndim != 2 or x.shape[1] != 2 or not 1 <= len(x) <= 12000000 or not np.isfinite(x).all():
        raise ValueError('expected bounded finite stereo audio')
    if type(dynamic) is not bool or not 1 <= len(taps) <= 16 or any(type(k) is not int or not 0 <= k <= 128 for k in taps) or list(taps) != sorted(set(taps)):
        raise ValueError('invalid causal taps')
    w = np.asarray(coefficients, dtype=np.float64)
    if w.shape != (2, len(taps) + int(dynamic)) or not np.isfinite(w).all() or np.max(abs(w)) > .25:
        raise ValueError('invalid bounded coefficients')
    if not np.isfinite(scale) or not 1e-5 <= scale <= 32:
        raise ValueError('invalid frozen scale')
    mid_side = np.column_stack((x.mean(1), (x[:, 0] - x[:, 1]) * .5))
    if dynamic:
        env = lfilter([.001], [1, -.999], np.max(abs(x), axis=1))
        mod = np.clip(np.log2(np.maximum(env, scale * .1) / scale), -2, 2).astype('f')
    out = []
    for c in range(2):
        v = mid_side[:, c]
        q = np.column_stack([np.pad(v, (k, 0))[:len(x)] for k in taps])
        if dynamic:
            q = np.column_stack((q, v * mod))
        out.append(v + q @ w[c])
    y = np.column_stack((out[0] + out[1], out[0] - out[1])).astype('f')
    if not np.isfinite(y).all():
        raise ValueError('nonfinite result')
    return y

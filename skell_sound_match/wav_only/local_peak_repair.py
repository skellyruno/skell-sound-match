"""Offline, localized estimated true-peak repair. No reference audio at replay.
Uses 4x polyphase interpolation; not a certified true-peak meter or realtime limiter.
"""
import numpy as np
from scipy import signal, ndimage


def estimated_peak(samples):
    x = np.asarray(samples, dtype=np.float32)
    if x.ndim != 2 or not len(x) or x.shape[1] != 2 or not np.isfinite(x).all():
        raise ValueError('expected nonempty finite stereo samples')
    return float(np.max(np.abs(signal.resample_poly(x, 4, 1, axis=0))))


def repair_peak(samples, ceiling_db=-1.2, passes=3):
    """Link stereo and attenuate only a small neighborhood of unsafe peaks.

    An unchanged safe input is returned as a copy. Final global fallback is
    measured rather than assumed; estimated peak is not guaranteed at other
    interpolation rates. Output uses the same length and sample alignment.
    """
    x = np.asarray(samples, dtype=np.float32)
    if not np.isfinite(ceiling_db) or not -12 <= ceiling_db <= 0:
        raise ValueError('invalid ceiling')
    if type(passes) is not int or not 1 <= passes <= 8:
        raise ValueError('invalid pass count')
    p = estimated_peak(x)
    cap = 10.0**(ceiling_db/20)
    y = x.copy()
    if p <= cap:
        return y
    for _ in range(passes):
        u = signal.resample_poly(y, 4, 1, axis=0)
        peak = np.max(np.abs(u.reshape(len(y), 4, 2)), axis=(1, 2))
        if float(peak.max()) <= cap:
            return y
        g = np.minimum(1., cap / np.maximum(peak, 1e-12))
        g = ndimage.minimum_filter1d(g, size=17, mode='nearest')
        g = ndimage.uniform_filter1d(g, size=9, mode='nearest')
        y *= g[:, None]
    p = estimated_peak(y)
    if p > cap:
        y *= np.float32(cap / p * .99999)
    return y

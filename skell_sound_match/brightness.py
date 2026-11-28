"""Bounded offline causal brightness shelf (independent research)."""
import numpy as np
from scipy import signal


def brightness_shelf(x, rate, hz, db):
    x = np.asarray(x, dtype=np.float32)
    if x.ndim != 2 or x.shape[1] not in (1, 2) or not len(x) or not np.isfinite(x).all():
        raise ValueError('expected finite mono or stereo audio')
    if type(rate) is not int or not 32000 <= rate <= 192000 or not np.isfinite(hz) or not 100 <= hz <= min(12000, rate / 4) or not np.isfinite(db) or not -12 <= db <= 12:
        raise ValueError('invalid shelf parameters')
    if db == 0:
        return x.copy()
    a = np.exp(-2 * np.pi * hz / rate)
    low = signal.lfilter([1-a], [1,-a], x, axis=0)
    return (low + (x-low)*10**(db/20)).astype(np.float32)

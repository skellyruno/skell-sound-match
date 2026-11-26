"""Offline latency compensation with a known delay, never a fitted correlation lag."""
import numpy as np


def render_compensated(source, render, latency):
    x = np.asarray(source, dtype=np.float32)
    if x.ndim != 2 or x.shape[1] != 2 or not 1 <= len(x) <= 12000000 or not np.isfinite(x).all():
        raise ValueError('expected bounded finite stereo audio')
    if type(latency) is not int or not 0 <= latency <= 192000:
        raise ValueError('invalid declared latency')
    padded = np.pad(x, ((0, latency), (0, 0))).astype(np.float32)
    y = np.asarray(render(padded), dtype=np.float32)
    if y.shape != padded.shape or not np.isfinite(y).all():
        raise ValueError('renderer returned invalid geometry or samples')
    return np.ascontiguousarray(y[latency:latency + len(x)]).copy()

"""Offline stereo-linked peak compression; zero algorithmic lookahead.

This is an experimental finishing stage, not a true-peak limiter. Measure the
emitted waveform at oversampled rate and apply a final safety trim separately.
"""
import numpy as np


def render(audio, ceiling_db=-6., ratio=4.):
    x = np.asarray(audio, dtype=float)
    if x.ndim != 2 or x.shape[1] != 2 or not np.isfinite(x).all():
        raise ValueError('Expected finite stereo audio')
    if not np.isfinite([ceiling_db, ratio]).all() or not -30 <= ceiling_db <= 0 or not 1 <= ratio <= 20:
        raise ValueError('Invalid peak control parameters')
    peak = np.max(np.abs(x), axis=1)
    threshold = 10 ** (ceiling_db / 20)
    gain = np.ones(len(x))
    loud = peak > threshold
    gain[loud] = (peak[loud] / threshold) ** (1 / ratio - 1)
    return x * gain[:, None]

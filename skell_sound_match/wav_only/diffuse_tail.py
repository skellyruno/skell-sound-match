"""Deterministic causal diffuse-tail hypothesis for private offline trials.

No measured impulse responses or original plugin settings are embedded here.
Side emphasis routes a decorrelated wet field into mid/side; the dry channels
remain untouched. This is not a native or real-time convolution engine.
"""
import numpy as np
from scipy import signal


def render(audio, sr, decay_s=.7, wet_gain=.1, *, side_emphasis=False, seed=20261123):
    x = np.asarray(audio, dtype=float)
    if x.ndim != 2 or x.shape[1] != 2 or not len(x) or not np.isfinite(x).all():
        raise ValueError('Expected nonempty finite stereo audio')
    if not 32000 <= sr <= 192000 or not np.isfinite([decay_s, wet_gain]).all():
        raise ValueError('Invalid sample rate or tail parameters')
    if not .1 <= decay_s <= 10 or not 0 <= wet_gain <= 1:
        raise ValueError('Tail parameters out of bounds')
    if wet_gain == 0:
        return x.copy()
    t = np.arange(round(sr * decay_s * 1.5)) / sr
    impulse = np.random.default_rng(seed).normal(size=(len(t), 2))
    impulse *= np.exp(-6.908 * t[:, None] / decay_s)
    impulse = signal.sosfilt(signal.butter(2, 5000, fs=sr, output='sos'), impulse, axis=0)
    impulse[:round(.02 * sr)] = 0
    impulse /= np.sqrt(np.sum(impulse ** 2, axis=0))
    wet = np.stack([signal.fftconvolve(x[:, c], impulse[:, c])[:len(x)]
                    for c in range(2)], axis=1)
    if side_emphasis:
        mid = np.mean(wet, axis=1)
        side = (wet[:, 0] - wet[:, 1]) / 2
        wet = np.column_stack((.25 * mid + side, .25 * mid - side))
    return x + wet_gain * wet

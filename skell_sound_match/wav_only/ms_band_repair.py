"""Offline phase-preserving mid/side band repair.
Fits training audio only; centered FIR replay adds an offline lookahead
requirement. This is not proof of plugin latency or real-time safety.
"""
import numpy as np
from scipy import signal
from scipy.optimize import least_squares

EDGES = np.array([70, 150, 300, 600, 1200, 2400, 4800, 9600, 18000])
CENTERS = np.sqrt(EDGES[:-1] * EDGES[1:])


def _stereo(x):
    x = np.asarray(x, dtype=np.float32)
    if x.ndim != 2 or x.shape[1] != 2 or len(x) == 0 or not np.isfinite(x).all():
        raise ValueError('expected finite stereo samples')
    return x


def _ms(x):
    return np.column_stack([x.mean(1), (x[:, 0] - x[:, 1]) * .5]).astype('f')


def fit_ms_gain(candidate, target, *, separate_side=True):
    """Fit eight broad-band gains to paired 44.1 kHz training audio."""
    y, t = _stereo(candidate), _stereo(target)
    if y.shape != t.shape or len(y) < 2048:
        raise ValueError('paired training audio must align and contain 2048 samples')
    f, p = signal.welch(_ms(y), 44100, nperseg=2048, axis=0)
    _, q = signal.welch(_ms(t), 44100, nperseg=2048, axis=0)
    c = np.log(CENTERS)
    B = np.stack([np.interp(np.log(np.maximum(f, 20)), c, np.eye(len(c))[k])
                  for k in range(len(c))], axis=1)
    masks = [(f >= l) & (f < h) for l, h in zip(EDGES[:-1], EDGES[1:])]
    floor = max(q.sum() * 1e-7, 1e-16)
    target_bands = np.array([q[v].sum(0) for v in masks])

    def unpack(g):
        return g.reshape(8, 2) if separate_side else np.column_stack([g[:8], g[:8] + g[8]])

    def loss(g):
        g = unpack(g)
        r = p * 10**((B @ g) / 10)
        bands = np.array([r[v].sum(0) for v in masks])
        tone = 10*np.log10((bands.sum(1)+floor)/(target_bands.sum(1)+floor))
        side = (10*np.log10((bands[:, 1]+floor)/(bands[:, 0]+floor))
                - 10*np.log10((target_bands[:, 1]+floor)/(target_bands[:, 0]+floor)))
        return np.r_[tone, side*.2, g.flatten()*.065, np.diff(g, axis=0).flatten()*.065]

    fit = least_squares(loss, np.zeros(16 if separate_side else 9),
                        bounds=(-8, 8), max_nfev=35)
    return unpack(fit.x).astype('f')


def replay_ms_gain(candidate, gains, amount=1.):
    """Centered, symmetric FIR with fixed learned gains; no target input."""
    y = _stereo(candidate)
    g = np.asarray(gains, dtype=np.float32)
    if g.shape != (8, 2) or not np.isfinite(g).all() or np.max(abs(g)) > 16.001:
        raise ValueError('invalid gain coefficients')
    if not np.isfinite(amount) or not 0 <= amount <= 1:
        raise ValueError('amount must be in [0, 1]')
    f = np.linspace(0, 22050, 1025)
    v = _ms(y)
    out = np.empty_like(v)
    for c in range(2):
        gain = 10**(np.interp(np.log(np.maximum(f, 20)), np.log(CENTERS), g[:, c])*amount/20)
        h = signal.firwin2(2049, f, gain, fs=44100).astype('f')
        out[:, c] = signal.fftconvolve(v[:, c], h, mode='same')
    return np.column_stack([out[:, 0]+out[:, 1], out[:, 0]-out[:, 1]]).astype('f')

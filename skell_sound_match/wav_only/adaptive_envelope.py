"""Offline, train-prefix-only wet-envelope identification and bounded correction.

No reference samples or time-varying reference envelope are replayed. The learned
weights describe source-driven causal power history. This is not native DSP.
"""
from dataclasses import dataclass
import numpy as np
from scipy import ndimage, optimize


@dataclass(frozen=True)
class EnvelopeModel:
    sample_rate: int
    hop: int
    lags: tuple[int, ...]
    weights: np.ndarray
    source_scale: float
    target_scale: float


def _power(x, hop):
    x = np.asarray(x, dtype=float)
    if x.ndim != 1 or not len(x) or not np.isfinite(x).all():
        raise ValueError('Expected finite mono signal')
    pad = (-len(x)) % hop
    return np.mean(np.pad(x*x, (0, pad)).reshape(-1, hop), axis=1)


def _history(p, lags):
    return np.column_stack([np.pad(p, (lag, 0))[:len(p)] for lag in lags])


def fit_envelope(source, target, sample_rate, train_stop, *, ridge=.02):
    """Identify nonnegative power taps with a frozen train-prefix boundary."""
    if sample_rate < 8000 or not 0 < train_stop <= min(len(source), len(target)) or ridge < 0:
        raise ValueError('Invalid training interval or regularization')
    hop = max(1, round(sample_rate*.01))
    n = train_stop//hop*hop
    if n < 20*hop:
        raise ValueError('Training interval too short')
    p = _power(source[:n], hop)
    q = _power(target[:n], hop)
    lags = (0, 1, 2, 4, 7, 10, 15, 22, 32, 45, 64, 85, 110, 150)
    xs = max(float(np.percentile(p, 95)), 1e-12)
    ys = max(float(np.percentile(q, 95)), 1e-12)
    A = _history(p/xs, lags)
    # Weight quiet and active frames without making digital silence dominant.
    w = 1/np.sqrt(np.maximum(q/ys, .025))
    B = A*w[:, None]
    c = q/ys*w
    weights, _ = optimize.nnls(np.vstack((B, np.sqrt(ridge*len(p))*np.eye(len(lags)))),
                               np.r_[c, np.zeros(len(lags))])
    weights.setflags(write=False)
    return EnvelopeModel(sample_rate, hop, lags, weights, xs, ys)


def apply_envelope(source, candidate, model, *, strength=.65, max_db=9):
    """Apply bounded smooth offline gain derived only from input and candidate."""
    if len(source) != len(candidate) or not 0 <= strength <= 1 or not 0 <= max_db <= 18:
        raise ValueError('Invalid correction arguments')
    p = _power(source, model.hop)
    c = _power(candidate, model.hop)
    predicted = _history(p/model.source_scale, model.lags)@model.weights*model.target_scale
    floor = max(model.target_scale*1e-5, 1e-12)
    db = 10*np.log10((predicted+floor)/(c+floor))
    db = ndimage.gaussian_filter1d(np.clip(db, -max_db, max_db), 1.25)*strength
    # Frame-center interpolation is offline and intentionally not claimed RT causal.
    gain = np.interp(np.arange(len(candidate)), (np.arange(len(db))+.5)*model.hop, 10**(db/20))
    return np.asarray(candidate)*gain

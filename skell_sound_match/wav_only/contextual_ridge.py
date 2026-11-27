"""Offline complex ridge regression for input-conditioned spectral features.
No target samples are required by replay. This module does not establish
causality of caller-supplied features, realtime safety or measured latency.
"""
import numpy as np


def fit_complex_ridge(features, target, mask, regularization=.025):
    """Fit [frame, bin, feature] to [frame, bin, output], masked frames only."""
    x = np.asarray(features, dtype=np.complex64)
    y = np.asarray(target, dtype=np.complex64)
    m = np.asarray(mask)
    if (x.ndim != 3 or y.ndim != 3 or x.shape[:2] != y.shape[:2]
            or not all(x.shape) or not y.shape[-1] or m.dtype != np.bool_
            or m.shape != (len(x),) or not m.any()
            or not np.isfinite(regularization) or regularization <= 0):
        raise ValueError('invalid training shape, mask or regularization')
    a = np.ascontiguousarray(x[m].transpose(1, 0, 2))
    b = np.ascontiguousarray(y[m].transpose(1, 0, 2))
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('nonfinite training samples')
    ah = a.conj().transpose(0, 2, 1)
    g = ah @ a
    q = ah @ b
    diag = np.diagonal(g, axis1=1, axis2=2).real
    pen = np.maximum(diag, np.maximum(diag.mean(1)*.015, 1e-9)[:, None])
    j = np.arange(g.shape[-1])
    g[:, j, j] += regularization*pen+1e-7
    h = np.linalg.solve(g, q).astype(np.complex64)
    if not np.isfinite(h).all():
        raise ValueError('nonfinite fitted weights')
    return h


def replay_complex_ridge(features, weights):
    """Fixed coefficients, input features only; no targets or fit mask."""
    x = np.asarray(features, dtype=np.complex64)
    h = np.asarray(weights, dtype=np.complex64)
    if (x.ndim != 3 or h.ndim != 3 or x.shape[1:] != h.shape[:2]
            or not np.isfinite(x).all() or not np.isfinite(h).all()):
        raise ValueError('invalid replay tensors')
    return np.einsum('fbi,bio->fbo', x, h, optimize=True)

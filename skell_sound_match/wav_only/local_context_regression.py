"""Bounded-memory local ridge regression for offline input-conditioned research.
Training descriptors and labels must come from the training region only.
The function accepts query descriptors, not reference audio or time indices.
"""
from numbers import Integral
import numpy as np
from scipy.spatial import cKDTree


def local_ridge(training, labels, queries, *, neighbors=40, components=8,
                ridge=.06, batch_size=128):
    """Predict real-valued labels with distance-weighted local linear models.

    PCA is computed solely from training descriptors. Neighbor search takes
    place in normalized descriptor space; the local regression uses a lower
    dimensional projection. Caller must bound output gains/phase where needed.
    This is an offline fitter, not a realtime DSP callback implementation.
    """
    x = np.asarray(training, dtype=np.float32)
    y = np.asarray(labels, dtype=np.float32)
    q = np.asarray(queries, dtype=np.float32)
    if (x.ndim != 2 or y.ndim != 2 or q.ndim != 2 or len(x) < 2
            or not x.shape[1] or not y.shape[1] or len(x) != len(y)
            or x.shape[1] != q.shape[1]
            or not all(np.isfinite(a).all() for a in (x, y, q))):
        raise ValueError('invalid descriptor or label matrix')
    for n in (neighbors, components, batch_size):
        if not isinstance(n, Integral) or isinstance(n, bool) or n <= 0:
            raise ValueError('invalid integer configuration')
    if neighbors < 2 or not np.isfinite(ridge) or ridge <= 0:
        raise ValueError('neighbors and ridge must be positive')
    if not len(q):
        return np.empty((0, y.shape[1]), dtype=np.float32)
    tree = cKDTree(x)
    _, _, axes = np.linalg.svd(x - x.mean(0), full_matrices=False)
    v = axes[:min(components, len(axes))].T
    xp = x @ v
    qp = q @ v
    out = []
    for start in range(0, len(q), batch_size):
        stop = min(start + batch_size, len(q))
        dist, idx = tree.query(q[start:stop], k=min(neighbors, len(x)), workers=1)
        r = np.maximum(dist[:, -1:], .01)
        delta = (xp[idx] - qp[start:stop, None, :]) / r[:, :, None]
        a = np.concatenate([np.ones((*delta.shape[:2], 1), dtype=np.float32), delta], axis=2)
        w = np.exp(-2 * (dist / r)**2)
        aw = a * w[:, :, None]
        at = a.transpose(0, 2, 1)
        g = at @ aw
        rhs = aw.transpose(0, 2, 1) @ y[idx]
        j = np.arange(g.shape[-1])
        g[:, j, j] += ridge * w.sum(1)[:, None] * np.r_[.005, np.ones(g.shape[-1]-1)][None, :] + 1e-7
        out.append(np.linalg.solve(g, rhs)[:, 0])
    result = np.concatenate(out).astype(np.float32)
    if not np.isfinite(result).all():
        raise ValueError('nonfinite local prediction')
    return result

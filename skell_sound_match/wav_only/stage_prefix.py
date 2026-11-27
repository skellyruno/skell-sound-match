"""Guard same-take intermediate supervision against future-region leakage."""
from numbers import Integral
import numpy as np


def supervised_prefix(dry, stage_dry, stage_target, fit_stop, evaluation_start):
    """Verify exact dry prefix and return an owned, bounded stage target.

    This guards data passed to a new fit, not the provenance of frozen models.
    Cutoffs are exclusive sample indices on the same aligned sample grid.
    """
    x, u, t = (np.asarray(a) for a in (dry, stage_dry, stage_target))
    if any(a.ndim != 2 or a.shape[1] != 2 for a in (x, u, t)) or u.shape != t.shape:
        raise ValueError('expected paired stereo stage data')
    if any(not isinstance(k, Integral) or isinstance(k, bool) for k in (fit_stop, evaluation_start)):
        raise ValueError('invalid sample cutoff')
    if not 0 < fit_stop <= evaluation_start <= len(x) or fit_stop > len(u):
        raise ValueError('stage fit crosses allowed boundary')
    if not all(np.isfinite(a[:fit_stop]).all() for a in (x, u, t)):
        raise ValueError('nonfinite stage prefix')
    if not np.array_equal(x[:fit_stop], u[:fit_stop]):
        raise ValueError('source prefix mismatch')
    return t[:fit_stop].copy()

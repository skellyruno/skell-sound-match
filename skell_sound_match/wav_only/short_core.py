"""Short-memory learned vocal kernel projection for offline dry-core fitting.
A dry-core profile deliberately excludes invented echoes and room features.
Use separate explicitly selected wet-effect stages when present in the reference.
"""
import numpy as np

def dry_core_kernel(impulse, *, taps, lead=0, wrapped=True):
    """Extract short forward impulse support; optional <=32 sample offline lead.

    wrapped=True: IFFT impulse starts at time zero, negative lags wrap at end.
    wrapped=False: impulse is already arranged from time zero; lead must be zero.
    """
    h=np.asarray(impulse,dtype=np.float32)
    if h.ndim!=3 or h.shape[2]!=2 or not 1<=h.shape[1]<=16 or not 64<=len(h)<=32768 or not np.isfinite(h).all():
        raise ValueError('invalid impulse geometry')
    if type(taps) is not int or not 64<=taps<=2048 or type(lead) is not int or not 0<=lead<=32 or taps+lead>len(h) or (not wrapped and lead):
        raise ValueError('invalid short-memory support')
    k=np.concatenate((h[-lead:],h[:taps]),axis=0) if lead else h[:taps].copy()
    k[-64:]*=np.linspace(1,0,64,dtype=np.float32)[:,None,None]
    if lead:k[:min(16,lead)]*=np.linspace(0,1,min(16,lead),dtype=np.float32)[:,None,None]
    return k


def require_dry_core(*, spatial_features=(), spatial_weights=()):
    """Fail closed instead of silently including a wet branch in a dry-core fit."""
    if len(spatial_features) or len(spatial_weights):
        raise ValueError('dry core must not include automatic wet effects')

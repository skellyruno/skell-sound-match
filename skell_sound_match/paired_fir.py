"""Independent offline causal FIR identification from paired training audio.

Not an original plugin emulation. Fits a bounded regularized stereo kernel
from a near-mono source, not a stored reference clip. Render uses only input.
"""
import numpy as np
from scipy import signal, linalg


def _mono(x):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] not in (1,2) or not len(x) or not np.isfinite(x).all():
        raise ValueError('expected finite mono or stereo audio')
    if x.shape[1] == 2:
        if np.mean((x[:,0]-x[:,1])**2) > .01*max(np.mean((x[:,0]+x[:,1])**2),1e-30):
            raise ValueError('source is not sufficiently mono')
    return x.mean(axis=1)


def compress_source(x, rate, amount=0., threshold_db=-24.):
    if type(rate) is not int or not 32000 <= rate <= 192000 or not np.isfinite(amount) or not 0<=amount<=.9 or not np.isfinite(threshold_db) or not -60<=threshold_db<=0:
        raise ValueError('invalid envelope controls')
    x = _mono(x)
    if amount == 0:
        return x
    envs=[]
    for ms in (3.,85.):
        a=-np.expm1(-1000/(ms*rate))
        envs.append(signal.lfilter([a],[1,a-1],x*x))
    db=10*np.log10(np.maximum(np.maximum(*envs),1e-15))
    return x*10**(-amount*np.maximum(db-threshold_db,0)/20)


def fit_kernel(x, y, taps, ridge):
    """Causal Toeplitz ridge fit; zero-pad outside training partition."""
    x=np.asarray(x,dtype=np.float64);y=np.asarray(y,dtype=np.float64)
    if x.ndim!=1 or y.shape!=(len(x),2) or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('invalid paired training')
    if type(taps) is not int or not 1<=taps<=4096 or len(x)<max(2048,8*taps) or not np.isfinite(ridge) or not .0001<=ridge<=1:
        raise ValueError('invalid kernel controls')
    n=len(x); c=signal.correlate(x,x,method='fft')[n-1:n-1+taps]
    if c[0]<1e-12:raise ValueError('silent source')
    rhs=np.column_stack([signal.correlate(y[:,i],x,method='fft')[n-1:n-1+taps] for i in range(2)])
    c[0]*=1+ridge
    h=linalg.solve_toeplitz(c,rhs,check_finite=True)
    if not np.isfinite(h).all() or np.max(np.sum(abs(h),axis=0))>32:
        raise ValueError('unbounded kernel')
    return h


def render_kernel(x, kernel):
    x=np.asarray(x,dtype=np.float64);h=np.asarray(kernel,dtype=np.float64)
    if x.ndim!=1 or not len(x) or h.ndim!=2 or h.shape[1]!=2 or not 1<=len(h)<=4096 or not np.isfinite(x).all() or not np.isfinite(h).all() or np.max(np.sum(abs(h),axis=0))>32:
        raise ValueError('invalid causal FIR render')
    return signal.fftconvolve(x[:,None],h,axes=0)[:len(x)]

"""Small causal offline gate trial with a train-only bypass baseline."""
from __future__ import annotations
import numpy as np
from scipy import signal


def render(audio,sr,threshold_db=-55.,release_s=.03):
    x=np.asarray(audio,dtype=float)
    if x.ndim!=2 or not np.isfinite(x).all() or not -75<=threshold_db<=-30 or not .005<=release_s<=.2:
        raise ValueError('Invalid gate input or parameters')
    detector=np.exp(-1/(sr*.002))
    power=signal.lfilter([1-detector],[1,-detector],np.mean(x*x,axis=1))
    level=10*np.log10(np.maximum(power,1e-16))
    desired=np.clip((level-threshold_db+4)/4,0,1)
    pole=np.exp(-1/(sr*release_s))
    # A causal hold opens immediately; quiet changes release smoothly.
    smooth,_=signal.lfilter([1-pole],[1,-pole],desired,zi=[pole])
    gain=np.maximum(desired,smooth)
    return x*gain[:,None]


def fit(audio,target,sr,train_end):
    x=np.asarray(audio);y=np.asarray(target)
    if x.shape!=y.shape or not 0<train_end<=len(x):raise ValueError('Gate pair/training mismatch')
    quiet=np.mean(x[:train_end]**2,axis=1)<10**(-45/10)
    # Equal emphasis on quiet and active regions; neither can be hidden by level.
    def score(z):
        err=np.mean((z[:train_end]-y[:train_end])**2,axis=1)
        return float(np.mean(err[quiet]) if np.any(quiet) else 0)+float(np.mean(err[~quiet]) if np.any(~quiet) else 0)
    best=(score(x),None,x)
    for threshold in (-65.,-60.,-55.,-50.,-45.):
        for release in (.01,.03,.07):
            z=render(x,sr,threshold,release);value=score(z)
            if value<best[0]:best=(value,{'threshold_db':threshold,'release_s':release},z)
    return best[1],best[2],{'train_score':best[0],'bypass_train_score':score(x),'selection':'train_only_with_bypass_baseline'}

"""Independent phrase-aware return calibration; not vendor source or realtime DSP."""
import numpy as np
from scipy import signal
SR=44100

def activity(x, scale, release_ms):
    if not np.isfinite(scale) or scale<=0 or release_ms<=0: raise ValueError('invalid detector')
    e=np.mean(x*x,axis=1)
    a=np.exp(-1/(SR*.012));b=np.exp(-1/(SR*.001*release_ms))
    fast=signal.lfilter([1-a],[1,-a],e);slow=signal.lfilter([1-b],[1,-b],e)
    return np.clip(np.sqrt(np.maximum(fast,slow))/scale,0,1).astype('f')

def make_terms(x,y,direct,scale,release_ms,mode):
    a=activity(x,scale,release_ms)[:,None];w=y-direct
    if mode==0:return [y,y*(1-a),y*a]
    if mode==1:return [y,w,w*a,direct*(1-a)]
    if mode==2:return [y,w,w*(1-a),direct*a]
    raise ValueError('unknown basis')

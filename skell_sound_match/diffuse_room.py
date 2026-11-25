"""Independent offline diffuse-room basis; not an emulation of a supplied engine."""
import numpy as np
from scipy import signal

def room_basis(x, rate, decay, damping, predelay):
    x=np.asarray(x,dtype=np.float64)
    if x.ndim!=2 or x.shape[1]!=2 or not len(x) or not np.isfinite(x).all() or not np.isfinite(rate) or int(rate)!=rate or not 32000<=rate<=192000:
        raise ValueError('invalid stereo audio or sample rate')
    if not all(np.isfinite(v) for v in (decay,damping,predelay)) or not .15<=decay<=3 or not 500<=damping<=12000 or not 0<=predelay<=.12:
        raise ValueError('invalid room controls')
    n=int(np.ceil(rate*decay)); t=np.arange(n)/rate
    ir=np.random.default_rng(1709).standard_normal((n,2)); pole=np.exp(-2*np.pi*damping/rate)
    ir=signal.lfilter([1-pole],[1,-pole],ir,axis=0)*np.exp(-np.log(1000)*t[:,None]/decay)
    ir*=np.minimum(1.,t/.008)[:,None]
    ir/=max(np.sqrt(np.sum(ir*ir)/2),1e-15)
    ir=np.pad(ir,((int(round(predelay*rate)),0),(0,0)))
    return signal.fftconvolve(x.mean(1)[:,None],ir,axes=0)[:len(x)]

def mix_room(x, wet, mix, width):
    x=np.asarray(x,dtype=np.float64);wet=np.asarray(wet,dtype=np.float64)
    if x.ndim!=2 or x.shape[1]!=2 or x.shape!=wet.shape or not np.isfinite(x).all() or not np.isfinite(wet).all() or not np.isfinite(mix) or not np.isfinite(width) or not 0<=mix<=.5 or not 0<=width<=1:
        raise ValueError('invalid mix')
    if mix==0:return x.copy()
    m=wet.mean(1,keepdims=True)
    return x+mix*(m+width*(wet-m))

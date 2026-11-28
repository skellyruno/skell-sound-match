"""Offline causal side-only EQ research. Unity preserves the input exactly."""
import numpy as np
from scipy.signal import lfilter

class SideBalance:
    def __init__(self, x, rate):
        x = np.asarray(x, dtype=np.float64)
        if x.ndim != 2 or x.shape[1] != 2 or not len(x) or not np.isfinite(x).all() or not np.isfinite(rate) or not 32000 <= rate <= 192000:
            raise ValueError('invalid stereo input or sample rate')
        self.x = x
        side = (x[:,0]-x[:,1])*.5
        lows = []
        for hz in (400, 3000):
            p = np.exp(-2*np.pi*hz/rate)
            lows.append(lfilter([1-p],[1,-p],side))
        self.bands = np.stack((lows[0], lows[1]-lows[0], side-lows[1]))

    def render(self, gains):
        gains = np.asarray(gains, dtype=float)
        if gains.shape != (3,) or not np.isfinite(gains).all() or np.any(abs(gains)>12):
            raise ValueError('invalid side EQ gains')
        delta = (10**(gains/20)-1) @ self.bands
        return self.x + np.stack((delta,-delta),axis=1)

def band_width(x, rate):
    """Per-band mid/side distribution; discard bands with insufficient total energy."""
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[1]!=2 or not np.isfinite(x).all() or len(x)<2048 or not np.isfinite(rate) or not 32000<=rate<=192000:
        raise ValueError('invalid width input')
    n=2048
    f=x[:len(x)//n*n].reshape(-1,n,2)
    power=np.mean(f*f,axis=(1,2)); active=power>max(power.max()*1e-4,1e-12)
    f=f[active]
    if len(f)<8: raise ValueError('insufficient active audio')
    f=f[np.linspace(0,len(f)-1,min(128,len(f)),dtype=int)]
    z=np.fft.rfft(f*np.hanning(n)[None,:,None],axis=1)
    m=abs((z[:,:,0]+z[:,:,1])*.5)**2;s=abs((z[:,:,0]-z[:,:,1])*.5)**2
    hz=np.fft.rfftfreq(n,1/rate); total=(m+s).sum(axis=1)
    rows=[]
    for lo,hi in ((80,400),(400,3000),(3000,15000)):
        idx=(hz>=lo)&(hz<hi); a=m[:,idx].sum(axis=1); b=s[:,idx].sum(axis=1)
        valid=(a+b)>np.maximum(total*1e-4,1e-15)
        if valid.sum()<8: rows.append(np.full(3,np.nan));continue
        rows.append(np.percentile(np.clip(10*np.log10(np.maximum(b[valid],1e-15)/np.maximum(a[valid],1e-15)),-60,18),[25,50,75]))
    return np.array(rows)

def width_error(a,b):
    valid=np.isfinite(b)
    if not valid.any() or not np.isfinite(a[valid]).all(): raise ValueError('missing target width bands')
    return float(np.mean(abs(a[valid]-b[valid])))
